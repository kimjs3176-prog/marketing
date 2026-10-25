import json, sys, glob
import os, sys
from tt_config import DATA, OUT, SCRIPTS
os.chdir(DATA)
from pathlib import Path
import win32com.client as w
sys.path.insert(0, str(SCRIPTS))
import fitline
r = json.load(open("fitline.json", encoding="utf-8"))
F = {0: None, 4: "item", 5: "proposal", 12: "permits", 13: "adoption", 14: "dev"}
h = w.Dispatch("HWPFrame.HwpObject"); h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
out = {}
for name, v in r.items():
    if not v["still_short_tail"]:
        continue
    pid = name[:3]
    d = "경기A+센터" if pid.startswith("G") else "서울A+센터"
    m = fitline.measure(h, (OUT / d / name).resolve())
    for i in v["still_short_tail"]:
        lines, tail, total = m[i]
        out.setdefault(pid, {})[F.get(i, str(i))] = {"lines": lines, "tail": tail, "total": total}
h.Quit()
json.dump(out, open("left_measure.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(out))
