"""selection.json의 특허(또는 인자로 준 출원번호)를 KIPRIS Plus API로 조회해 서지정보를 kipris.json에 저장한다.
사용: KIPRIS_API_KEY=... python3 kipris_verify.py [출원번호 ...]"""
import json, os, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getBibliographyDetailInfoSearch"
KEY = os.environ["KIPRIS_API_KEY"]
here = Path(__file__).parent
selection = json.loads((here / "selection.json").read_text(encoding="utf-8"))

def text(el, tag):
    v = el.findtext(f".//{tag}")
    return v.strip() if v else ""

apps = sys.argv[1:] or [a for v in selection.values() for a in v]
out = {}
for app in apps:
    if app in out:
        continue
    url = f"{BASE}?applicationNumber={app}&ServiceKey={urllib.parse.quote(KEY)}"
    root = ET.fromstring(urllib.request.urlopen(url, timeout=40).read())
    b = root.find(".//biblioSummaryInfo")
    if b is None:
        out[app] = {"found": False}
        continue
    out[app] = {
        "found": True,
        "title": text(b, "inventionTitle"),
        "appNo": text(b, "applicationNumber"), "appDate": text(b, "applicationDate"),
        "regNo": text(b, "registerNumber").removesuffix("-0000"), "regDate": text(b, "registerDate"),
        "status": text(b, "registerStatus"), "disposal": text(b, "finalDisposal"),
        "claims": text(b, "claimCount"),
        "applicants": [text(a, "name") for a in root.iter("applicantInfo")],
        "rightHolders": [text(a, "name") for a in root.iter("rightHoderInfo")] or
                        [text(a, "name") for a in root.iter("rightHolderInfo")],
        "inventors": [text(a, "name") for a in root.iter("inventorInfo")],
        "ipc": sorted({text(i, "ipcNumber") for i in root.iter("ipcInfo")}),
        "abstract": re.sub(r"\s+", " ", text(root, "astrtCont")),
        "claim1": re.sub(r"\s+", " ", text(root, "claim")),
    }
    time.sleep(0.3)
(here / "kipris.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "patents")
