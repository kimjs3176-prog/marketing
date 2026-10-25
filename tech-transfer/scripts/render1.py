import sys, win32com.client as w
from pathlib import Path
from PIL import Image
h = w.Dispatch("HWPFrame.HwpObject"); h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
f = Path(sys.argv[1]).resolve(); pg = int(sys.argv[2]) if len(sys.argv) > 2 else 0
h.Open(str(f), "HWPX", "forceopen:true")
out = Path(sys.argv[3] if len(sys.argv) > 3 else "page.png").resolve()
h.CreatePageImage(str(out.with_suffix(".bmp")), pg, 110, 24, "bmp")
h.Clear(1); h.Quit()
Image.open(out.with_suffix(".bmp")).save(out)
print(out)
