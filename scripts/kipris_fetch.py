#!/usr/bin/env python3
"""KIPRIS Plus에서 특허 서지정보·청구항·대표 도면을 가져와 JSON으로 출력합니다.

특허 시리즈 페이지(docs/patents*.html)의 PATENTS 데이터를 채울 때 씁니다.
API 키는 환경변수 KIPRIS_API_KEY 에서 읽습니다(저장소에 키를 넣지 마세요).

사용 예:
  python3 scripts/kipris_fetch.py 10-2021-0157282 10-2020-0179019 \
      --drawings docs/assets > /tmp/patents.json

인자는 출원번호(10-YYYY-NNNNNNN) 또는 등록번호(10-NNNNNNN) 모두 됩니다.
--drawings 를 주면 대표 도면을 <폴더>/patent-<표시번호>.jpg 로 저장합니다.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE = "http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice"


def call(op, **params):
    key = os.environ.get("KIPRIS_API_KEY")
    if not key:
        sys.exit("KIPRIS_API_KEY 환경변수가 없습니다. 클라우드 환경 설정에 등록한 뒤 새 세션에서 실행하세요.")
    params["ServiceKey"] = key  # urlencode가 +, /, = 를 인코딩
    with urllib.request.urlopen(f"{BASE}/{op}?{urllib.parse.urlencode(params)}", timeout=30) as r:
        root = ET.fromstring(r.read())
    if root.findtext(".//successYN") != "Y":
        sys.exit(f"KIPRIS 오류({op}): {root.findtext('.//resultMsg')}")
    return root


def digits(no):
    d = re.sub(r"\D", "", no)
    if len(d) == 9:            # 등록번호 10-NNNNNNN
        return {"registerNumber": d + "0000"}
    if len(d) == 13:           # 출원번호 10-YYYY-NNNNNNN
        return {"applicationNumber": d}
    sys.exit(f"번호 형식을 알 수 없습니다: {no}")


def fmt_no(n, kind):
    n = (n or "").strip()
    if kind == "app" and len(n) == 13:
        return f"{n[:2]}-{n[2:6]}-{n[6:]}"
    if kind == "reg" and len(n) >= 9:
        return f"{n[:2]}-{n[2:9]}"
    return n


def fmt_date(d):
    d = (d or "").strip()
    return f"{d[:4]}.{d[4:6]}.{d[6:]}" if len(d) == 8 else ""


def fetch(no, drawings_dir=None):
    item = call("getAdvancedSearch", **digits(no)).find(".//item")
    if item is None:
        sys.exit(f"검색 결과 없음: {no}")
    g = lambda t: (item.findtext(t) or "").strip()
    app = g("applicationNumber")
    detail = call("getBibliographyDetailInfoSearch", applicationNumber=app)

    claims = [c.text.strip() for c in detail.iter("claim")
              if c.text and not re.match(r"^\s*\d+\.\s*삭제", c.text)]
    inventors = [i.findtext("name").strip() for i in detail.iter("inventorInfo") if i.findtext("name")]

    reg = fmt_no(g("registerNumber"), "reg")
    rec = {
        "id": reg or fmt_no(app, "app"),
        "status": g("registerStatus"),
        "title": g("inventionTitle"),
        "titleEng": re.sub(r"\s+", " ", detail.findtext(".//inventionTitleEng") or "").strip(),
        "applicant": " · ".join(a.strip() for a in g("applicantName").split("|")),
        "jointlyOwned": len([a for a in g("applicantName").split("|") if a.strip()]) > 1,
        "appNo": fmt_no(app, "app"),
        "appDate": fmt_date(g("applicationDate")),
        "openDate": fmt_date(g("openDate")),
        "regDate": fmt_date(g("registerDate")),
        "inventors": inventors,
        "ipc": " · ".join(x.strip() for x in g("ipcNumber").split("|")),
        "abstract": g("astrtCont"),
        "claims": claims,
        "drawingUrl": g("bigDrawing"),
    }
    if drawings_dir and rec["drawingUrl"]:
        path = os.path.join(drawings_dir, f"patent-{rec['id']}.jpg")
        urllib.request.urlretrieve(rec["drawingUrl"], path)
        rec["drawing"] = path
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("numbers", nargs="+", help="출원번호 또는 등록번호")
    ap.add_argument("--drawings", metavar="DIR", help="대표 도면 저장 폴더 (예: docs/assets)")
    args = ap.parse_args()
    json.dump([fetch(n, args.drawings) for n in args.numbers], sys.stdout, ensure_ascii=False, indent=2)
    print()
