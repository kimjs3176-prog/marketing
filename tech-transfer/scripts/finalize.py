"""전체 생성 → 한글 쪽수 확인 → 넘치는 건만 본문 분량을 줄여 재생성."""
import json, glob, os, subprocess, sys
from pathlib import Path

from tt_config import DATA as WORK, SCRIPTS
PY = sys.executable
env = dict(os.environ, PYTHONIOENCODING="utf-8")
packets = {c["id"]: c for f in sorted(glob.glob(str(WORK / "packets/packet_*.json"))) for c in json.load(open(f, encoding="utf-8"))}
expected = {pid: 1 + len(p["patents"]) for pid, p in packets.items()}


def build(ids, cap):
    r = subprocess.run([PY, str(SCRIPTS / "build_all.py"), *ids], cwd=WORK, env=dict(env, CAP=str(cap)), capture_output=True, text=True, encoding="utf-8")
    out = {}
    for ln in r.stdout.splitlines():
        parts = ln.split(" ", 3)
        if len(parts) >= 4:
            out[parts[0]] = (parts[1], parts[3])
    return out


def pages(paths):
    subprocess.run([PY, str(SCRIPTS / "pagecheck.py"), *paths], cwd=WORK, env=env, capture_output=True, text=True, encoding="utf-8", timeout=1800)
    return json.load(open(WORK / "pages.json", encoding="utf-8"))


todo = sorted(packets)
log = {}
for cap in (240, 210, 180, 150):
    if not todo:
        break
    res = build(todo, cap)
    bad_build = [i for i in todo if res.get(i, ("ERR",))[0] not in ("PASS", "WARN")]
    paths = [res[i][1] for i in todo if i not in bad_build]
    pc = pages(paths)
    nxt = []
    for i in todo:
        if i in bad_build:
            log[i] = ("BUILD_FAIL", cap)
            nxt.append(i)
            continue
        n = pc.get(Path(res[i][1]).name)
        log[i] = (n, expected[i], cap)
        if n != expected[i]:
            nxt.append(i)
    print(f"cap {cap}: {len(todo) - len(nxt)} ok, {len(nxt)} retry", flush=True)
    todo = nxt
json.dump(log, open(WORK / "finalize_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("remaining:", todo)
