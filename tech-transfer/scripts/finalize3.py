"""기존 파일별 줄간격·분량으로 82건 재생성 → 자간 정리(−12%, 남으면 −15%) → 쪽수 검증."""
import json, glob, os, subprocess, sys
from pathlib import Path

from tt_config import DATA as WORK, SCRIPTS
PY = sys.executable
env = dict(os.environ, PYTHONIOENCODING="utf-8")
packets = {c["id"]: c for f in sorted(glob.glob(str(WORK / "packets/packet_*.json"))) for c in json.load(open(f, encoding="utf-8"))}
expected = {pid: 1 + len(p["patents"]) for pid, p in packets.items()}
caps = {k: v[-1] for k, v in json.load(open(WORK / "finalize_log.json", encoding="utf-8")).items()}
lss = {k: v["ls"] for k, v in json.load(open(WORK / "finalize3_prev.json", encoding="utf-8")).items()}
LADDER = [160, 150, 140, 130, 120, 115]


def run(cmd, extra=None, timeout=7200):
    return subprocess.run(cmd, cwd=WORK, env=dict(env, **(extra or {})), capture_output=True, text=True, encoding="utf-8", timeout=timeout)


def build(ids):
    out, by = {}, {}
    for i in ids:
        by.setdefault((caps[i], lss[i]), []).append(i)
    for (cap, ls), group in by.items():
        r = run([PY, str(SCRIPTS / "build_all.py"), *group], {"CAP": str(cap), "LS1": str(ls)})
        for ln in r.stdout.splitlines():
            p = ln.split(" ", 3)
            if len(p) >= 4 and p[1] in ("PASS", "WARN"):
                out[p[0]] = p[3]
    return out


todo = sorted(packets)
final = {}
for attempt in range(4):
    res = build(todo)
    paths = [res[i] for i in todo if i in res]
    run([PY, str(SCRIPTS / "fitline.py"), *paths])
    fit1 = json.load(open(WORK / "fitline.json", encoding="utf-8"))
    left = [p for p in paths if fit1.get(Path(p).name, {}).get("still_short_tail")]
    fit2 = {}
    if left:
        run([PY, str(SCRIPTS / "fitline.py"), *left], {"MAX_SHRINK": "15", "START": "12"})
        fit2 = json.load(open(WORK / "fitline.json", encoding="utf-8"))
    run([PY, str(SCRIPTS / "pagecheck.py"), *paths], timeout=3600)
    pc = json.load(open(WORK / "pages.json", encoding="utf-8"))
    nxt = []
    for i in todo:
        name = Path(res.get(i, "")).name
        f = fit2.get(name) or fit1.get(name) or {}
        final[i] = {"ls": lss[i], "cap": caps[i], "pages": pc.get(name), "expected": expected[i], "left": f.get("still_short_tail", [])}
        if pc.get(name) != expected[i]:
            nxt.append(i)
            k = LADDER.index(lss[i]) if lss[i] in LADDER else 0
            lss[i] = LADDER[min(k + 1, len(LADDER) - 1)]
    print(f"attempt {attempt}: {len(todo) - len(nxt)} ok, {len(nxt)} retry", flush=True)
    todo = nxt
    if not todo:
        break
json.dump(final, open(WORK / "finalize3_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("remaining:", todo)
