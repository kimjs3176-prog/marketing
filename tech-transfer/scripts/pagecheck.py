"""한컴 한 인스턴스로 HWPX를 열어 쪽 수 확인 + PDF 내보내기."""
import sys, json
from pathlib import Path
import win32com.client as w
from tt_config import DATA

files = [Path(x).resolve() for x in sys.argv[1:]]
h = w.Dispatch("HWPFrame.HwpObject")
try:
    h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
except Exception:
    pass
h.XHwpWindows.Item(0).Visible = True
res = {}
for f in files:
    ok = h.Open(str(f), "HWPX", "forceopen:true")
    pages = h.PageCount if ok else None
    pdf = f.with_suffix(".pdf")
    if ok:
        h.SaveAs(str(pdf), "PDF", "")
    res[f.name] = pages
    print(f.name, pages, flush=True)
    h.Clear(1)
h.Quit()
json.dump(res, open(DATA / "pages.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
