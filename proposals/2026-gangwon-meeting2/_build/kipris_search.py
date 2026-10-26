"""KIPRIS Plus 검색: 농진청 단독 · 최근 10년 출원 · 등록/공개 특허 후보를 키워드별로 수집한다.
사용: KIPRIS_API_KEY=... python3 kipris_search.py queries.json out.json"""
import json, os, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

URL = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch"
OWNER, SINCE = "대한민국(농촌진흥청장)", "20161026"
queries = json.load(open(sys.argv[1], encoding="utf-8"))
out = {}
for code, words in queries.items():
    seen = {}
    for w in words:
        q = urllib.parse.urlencode({"astrtCont": w, "applicant": OWNER, "numOfRows": "50", "pageNo": "1"})
        root = ET.fromstring(urllib.request.urlopen(f"{URL}?{q}&ServiceKey={urllib.parse.quote(os.environ['KIPRIS_API_KEY'])}", timeout=40).read())
        for it in root.iter("item"):
            g = lambda t: (it.findtext(t) or "").strip()
            if g("applicantName") != OWNER or g("applicationDate") < SINCE or g("registerStatus") not in ("등록", "공개"):
                continue
            seen.setdefault(g("applicationNumber"), {"title": g("inventionTitle"), "date": g("applicationDate"),
                "status": g("registerStatus"), "reg": g("registerNumber"), "abstract": g("astrtCont")[:300], "q": w})
        time.sleep(0.2)
    out[code] = seen
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
