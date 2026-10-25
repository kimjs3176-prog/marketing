import json, glob, os, subprocess, sys
import os, sys
from tt_config import DATA, OUT, SCRIPTS
os.chdir(DATA)
from pathlib import Path
PY = sys.executable; env = dict(os.environ, PYTHONIOENCODING="utf-8")
packets = {c["id"]: c for f in glob.glob("packets/packet_*.json") for c in json.load(open(f, encoding="utf-8"))}
caps = {k: v[-1] for k, v in json.load(open("finalize_log.json", encoding="utf-8")).items()}
log = json.load(open("finalize3_log.json", encoding="utf-8"))
for pid in sys.argv[1:]:
    exp = 1 + len(packets[pid]["patents"])
    for ls in (160, 150, 140, 130, 120, 115):
        r = subprocess.run([PY, str(SCRIPTS / "build_all.py"), pid], env=dict(env, CAP=str(caps[pid]), LS1=str(ls)), capture_output=True, text=True, encoding="utf-8")
        parts = r.stdout.strip().split(" ", 3)
        if parts[1] not in ("PASS", "WARN"):
            print(pid, ls, "BUILD", parts[:3]); break
        path = parts[3]
        subprocess.run([PY, str(SCRIPTS / "fitline.py"), path], env=env, capture_output=True)
        f1 = json.load(open("fitline.json", encoding="utf-8")).get(Path(path).name, {})
        if f1.get("still_short_tail"):
            subprocess.run([PY, str(SCRIPTS / "fitline.py"), path], env=dict(env, MAX_SHRINK="15", START="12"), capture_output=True)
            f1 = json.load(open("fitline.json", encoding="utf-8")).get(Path(path).name, {})
        subprocess.run([PY, str(SCRIPTS / "pagecheck.py"), path], env=env, capture_output=True)
        n = json.load(open("pages.json", encoding="utf-8")).get(Path(path).name)
        print(pid, "LS", ls, "pages", n, "/", exp, "left", f1.get("still_short_tail"), flush=True)
        if n == exp:
            log[pid] = {"ls": ls, "cap": caps[pid], "pages": n, "expected": exp, "left": f1.get("still_short_tail", [])}
            break
json.dump(log, open("finalize3_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
