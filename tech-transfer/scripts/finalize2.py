"""1쪽 줄간격을 파일별로 최대한 넓히고(160→120%), 짧은 줄넘김은 자간으로 정리, 쪽수 검증."""
import json, glob, os, subprocess, sys
from pathlib import Path

from tt_config import DATA as WORK, SCRIPTS
PY = sys.executable
env = dict(os.environ, PYTHONIOENCODING="utf-8")
packets = {c["id"]: c for f in sorted(glob.glob(str(WORK / "packets/packet_*.json"))) for c in json.load(open(f, encoding="utf-8"))}
expected = {pid: 1 + len(p["patents"]) for pid, p in packets.items()}
caps = {k: v[-1] for k, v in json.load(open(WORK / "finalize_log.json", encoding="utf-8")).items()}


def build(ids, ls):
    out = {}
    by = {}
    for i in ids:
        by.setdefault(caps[i], []).append(i)
    for cap, group in by.items():
        r = subprocess.run([PY, str(SCRIPTS / "build_all.py"), *group], cwd=WORK, env=dict(env, CAP=str(cap), LS1=str(ls)),
                           capture_output=True, text=True, encoding="utf-8")
        for ln in r.stdout.splitlines():
            parts = ln.split(" ", 3)
            if len(parts) >= 4 and parts[1] in ("PASS", "WARN"):
                out[parts[0]] = parts[3]
    return out


todo = sorted(packets)
log = {}
for ls in (160, 150, 140, 130, 120):
    if not todo:
        break
    res = build(todo, ls)
    paths = [res[i] for i in todo if i in res]
    subprocess.run([PY, str(SCRIPTS / "fitline.py"), *paths], cwd=WORK, env=env, capture_output=True, text=True, encoding="utf-8", timeout=7200)
    fit = json.load(open(WORK / "fitline.json", encoding="utf-8"))
    subprocess.run([PY, str(SCRIPTS / "pagecheck.py"), *paths], cwd=WORK, env=env, capture_output=True, text=True, encoding="utf-8", timeout=3600)
    pc = json.load(open(WORK / "pages.json", encoding="utf-8"))
    nxt = []
    for i in todo:
        name = Path(res.get(i, "")).name
        n = pc.get(name)
        log[i] = {"ls": ls, "pages": n, "expected": expected[i], "fit": fit.get(name)}
        if n != expected[i]:
            nxt.append(i)
    print(f"LS {ls}: {len(todo) - len(nxt)} ok, {len(nxt)} retry", flush=True)
    todo = nxt
json.dump(log, open(WORK / "finalize2_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("remaining:", todo)
