"""기술이전 제안서 일괄 생성: content_*.json + packets → markdown → HWPX(one_shot, brief-report)."""
import json, re, subprocess, sys, glob, os
from pathlib import Path

from tt_config import DATA as WORK, OUT as ROOT
SKILL = Path.home() / ".claude/skills/hwpx-skill"
SCR = WORK
bib = json.load(open(SCR / "bib.json", encoding="utf-8"))

packets = {c["id"]: c for f in sorted(glob.glob(str(WORK / "packets/packet_*.json"))) for c in json.load(open(f, encoding="utf-8"))}
contents = {c["id"]: c for f in sorted(glob.glob(str(WORK / "content/content_*.json"))) for c in json.load(open(f, encoding="utf-8"))}
addons = {c["id"]: c for f in sorted(glob.glob(str(WORK / "content/addon_*.json"))) for c in json.load(open(f, encoding="utf-8"))}
only = set(sys.argv[1:])


def fan(a):
    return f"{a[:2]}-{a[2:6]}-{a[6:]}"


def cell(s):
    return str(s).replace("|", "/").replace("~", "∼").replace("\n", " ").replace("!", ",").replace("?", "").strip()


def number(a):
    b = bib[a]
    reg = b["regno"].replace("-0000", "") if b["status"] == "등록" and b["regno"].strip() else ""
    return f"{fan(a)}, {'등록 ' + reg if reg else '공개'}"


TODAY = (2026, 10, 24)
CIRCLED = "①②③④⑤"


def expiry(a):
    """존속기간 만료(특허 20년·실용신안 10년, 분할출원은 원출원일 기준)."""
    b = bib[a]
    base = b["origdate"] if b.get("origdate") and "신규" not in b.get("orig", "") else b["appdate"]
    y, m, d = (int(x) for x in base.split("."))
    return (y + (10 if a.startswith("20") else 20), m, d)


def term_line(pats):
    parts, rem = [], []
    for i, pt in enumerate(pats):
        y, m, d = expiry(pt["an"])
        left = y - TODAY[0] - ((m, d) < TODAY[1:])
        rem.append(left)
        tag = "" if bib[pt["an"]]["status"] == "등록" else "(공개)"
        parts.append(f"{CIRCLED[i]} {y}.{m}{tag}")
    lo, hi = min(rem), max(rem)
    span = f"{lo}년" if lo == hi else f"{lo}∼{hi}년"
    note = ""
    return " ".join(parts) + f" 만료 · 잔여 {span}{note}"


def adoption_short(p, ad):
    """도입 형태를 서술 대신 '통상실시권 N건 · 균주 분양 · 공개 N건' 식으로 간단 표기."""
    pats = p["patents"]
    parts = [f"통상실시권 {len(pats)}건"]
    txt = ad.get("adoption", "") + " ".join(pt.get("abstract", "") for pt in pats)
    if re.search(r"분양|KACC|KCCM|균주|종균|세포주", ad.get("adoption", "")):
        parts.append("균주·종균 분양")
    elif re.search(r"품종|계통", ad.get("adoption", "")):
        parts.append("품종 분양")
    pub = sum(1 for pt in pats if bib[pt["an"]]["status"] != "등록")
    if pub:
        parts.append(f"공개특허 {pub}건")
    if any(pt.get("label") == "유사" for pt in pats):
        parts.append("응용범위 검토")
    return " · ".join(parts)


def brk(t):
    return re.sub(r"\s*·\s*", " · ", t)


def short(t, n=58):
    t = cell(t)
    return t if len(t) <= n + 4 else t[:n].rstrip(' ,·') + '…'


def markdown(p, c):
    center = p["center"]
    lines = ["---", f"기관: {center} 농식품 벤처육성", f"줄간격: {LS1}", "---",
             f"# 「{cell(c['short_title'])}」 기술이전 제안", "", "## 제안 개요"]
    tgt = f" · 기업코드 {p['code']}" if p.get("code") else ""
    code = f" (기업코드 {p['code']})" if re.match(r"^\d{4}-\d{2}-\d{3}$", str(p.get("code") or "")) else ""
    lines.append(f"- **(아이템)** {cell(p['item'])}{code}")
    lines.append(f"- **(제안)** {cell(c['proposal'])}")
    lines += ["", "## 추천 특허 개요", "", "| 추천 특허 (출원번호 · 상태) | 핵심 기술 → 적용 |", "|---|---|"]
    core = {x["an"]: x["core"] for x in c["patents"]}
    for pt in p["patents"]:
        lines.append(f"| {short(pt['title'])} ({number(pt['an'])}) | {cell(core[pt['an']])} |")
    ad = addons[p["id"]]
    lines += ["", "## 도입 체크리스트"]
    lines.append(f"- **(권리기간)** {term_line(p['patents'])}")
    lines.append(f"- **(인허가)** {brk(cell(ad['permits']))}")
    lines.append(f"- **(도입 형태)** {adoption_short(p, ad)}")
    lines.append(f"- **(추가 개발)** {brk(cell(ad['dev']))}")
    lines += ["", "## 기대 효과"]
    for lab, txt in c["effects"]:
        lines.append(f"- **({cell(lab)})** {cell(txt)}")
    lines.append(f"⇒ {cell(c['conclusion'])}")
    lines.append("※ 특허 명세서 기반 AI 분석 내용으로, 실제 사업화는 농진청 연구자와 협의 필요")
    lines.append("※ KIPRIS Plus 검증(2026. 10. 24.) 농진청 단독·10년 내 출원 / 붙임 AI 요약서")
    for i, pt in enumerate(p["patents"]):
        lines += attachment(i, pt)
    return "\n".join(lines) + "\n"


AIS = WORK / "ais"
SECTIONS = [("기술분야", "기술분야"), ("발명요약", "발명 요약"), ("시장", "시장 동향"), ("농산업", "농산업 활용"), ("상용화", "상용화 전망")]
SHOW = ("발명 요약", "농산업 활용", "상용화 전망")
CAP = int(os.environ.get("CAP", "280"))


def cap(t, n=None):
    n = n or CAP
    sents = re.split(r"(?<=[다음함임됨])\.\s+", t)
    out = ""
    for i, x in enumerate(sents):
        x = x if x.endswith(".") else x + "."
        if out and len(out) + len(x) > n:
            break
        out = (out + " " + x).strip()
    if out.count("**") % 2:
        out = out.replace("**", "")
    return out


def clean_ais(t):
    t = t.replace("`", "").replace("**", "\x00")
    t = re.sub(r"(?<![\w])[*_]([^*_\n]+)[*_](?![\w])", r"\1", t).replace("*", "")
    t = t.replace("\x00", "**")
    if t.count("**") % 2:
        t = t.replace("**", "")
    return re.sub(r"(==|\+\+|__)", "", t)


def ais_sections(text):
    text = clean_ais(text)
    out, cur = {}, None
    for ln in text.splitlines():
        if ln.startswith("## "):
            cur = next((lab for key, lab in SECTIONS if key in ln), None)
            continue
        if cur and ln.strip():
            out[cur] = (out.get(cur, "") + " " + ln.strip()).strip()
    return out


def ymd(s):
    return s.replace(".", ". ") + "." if s and s.count(".") == 2 else (s or "-")


def attachment(i, pt):
    a = pt["an"]
    f = AIS / f"{a}.json"
    if not f.exists():
        raise FileNotFoundError(f"AIS 결과 없음: {a}")
    d = json.load(open(f, encoding="utf-8"))
    pat, reg, gov = d.get("patent", {}), d.get("register") or {}, d.get("govt") or {}
    com = (d.get("commercialization") or {})
    det = com.get("details") or {}
    b = bib[a]
    regno = b["regno"].replace("-0000", "") if b["status"] == "등록" and b["regno"].strip() else "미등록(공개)"
    y, m, dd = expiry(a)
    exp = reg.get("expiryDate") or f"{y}.{m:02d}.{dd:02d}"
    inv = pat.get("inventors") or []
    inv_s = (f"{inv[0]} 외 {len(inv) - 1}명" if len(inv) > 1 else (inv[0] if inv else "-"))
    lic_o, lic_e = reg.get("ordinaryLicenses") or [], reg.get("exclusiveLicenses") or []
    lic = "등록 전 확인 불가" if b["status"] != "등록" else (f"통상 {len(lic_o)}건 · 전용 {len(lic_e)}건" if (lic_o or lic_e) else "실시권 설정 이력 없음")
    charge = gov.get("chargeType") or "-"
    ipc = cell(((pat.get("classifications") or [""])[0] or "").split("|")[0]) or "-"
    ey, em, ed = (int(x) for x in exp.split(".")) if exp.count(".") == 2 else expiry(a)
    left = ey - TODAY[0] - ((em, ed) < TODAY[1:])
    regd = f" ({ymd(b['regdate'])} 등록)" if b.get("regdate") else ""
    SP = "​"
    L = ["---", f"## [붙임 {i + 1}] 특허 요약서 {CIRCLED[i]}", f"- **{cell(pt['title'])}**", SP,
         "| 구분 | 내용 |", "|---|---|",
         f"| 출원번호 | {fan(a)} ({ymd(b['appdate'])} 출원) |",
         f"| 등록번호 | {regno}{regd} |",
         f"| 존속기간 | {cell(exp)} 만료 (잔여 약 {left}년) |",
         f"| 발명자 · IPC | {cell(inv_s)} · {ipc} |"]
    if com.get("score") is not None:
        L += ["## AI 사업화 평가", "| 종합 | 기술성 | 시장성 | 사업성 | 기술성숙도 |", "|---|---|---|---|---|",
              f"| {com['score']}점 | {det.get('technologyScore', '-')}점 | {det.get('marketScore', '-')}점 | {det.get('businessScore', '-')}점 | TRL {det.get('trl', '-')} |", SP]
    secs = ais_sections(d.get("summary", ""))
    for lab in SHOW:
        if secs.get(lab):
            L.append(f"- **({lab})** {cell(cap(secs[lab]))}")
    return L


FOOTER_TEXT = "※ 붙임 출처: AIS(atipsum.lovable.app) AI 분석 결과로, 실제 개발 단계와 다를 수 있음"
ATT_LS = int(os.environ.get("ATT_LS", "155"))
LS1 = int(os.environ.get("LS1", "140"))


def postprocess(path):
    """붙임(2쪽~)만 ❍ 문단 줄간격 확대 + 2쪽부터 꼬리말(출처) 삽입."""
    import zipfile, io
    src = Path(path).read_bytes()
    zin = zipfile.ZipFile(io.BytesIO(src))
    files = {n: zin.read(n) for n in zin.namelist()}
    infos = {n: zin.getinfo(n) for n in zin.namelist()}
    hname = next(n for n in files if n.endswith("header.xml"))
    sname = next(n for n in files if re.search(r"section0\.xml$", n))
    h = files[hname].decode("utf-8")
    s = files[sname].decode("utf-8")
    m = re.search(r'<hh:paraPr id="35".*?</hh:paraPr>', h, re.S)
    cnt = int(re.search(r'<hh:paraProperties itemCnt="(\d+)"', h).group(1))
    new_id = cnt
    clone = re.sub(r'id="35"', f'id="{new_id}"', m.group(0), count=1)
    clone = re.sub(r'(<hh:lineSpacing type="PERCENT" value=")\d+', rf'\g<1>{ATT_LS}', clone)
    end = h.index("</hh:paraProperties>")
    h = h[:end] + clone + h[end:]
    h = h.replace(f'<hh:paraProperties itemCnt="{cnt}"', f'<hh:paraProperties itemCnt="{cnt + 1}"', 1)
    i = s.find('pageBreak="1"')
    if i > 0:
        pstart = s.rfind("<hp:p ", 0, i)
        att = s[pstart:].replace('paraPrIDRef="35"', f'paraPrIDRef="{new_id}"')
        center = re.search(r'<hh:paraPr id="(\d+)"[^>]*>\s*<hh:align horizontal="CENTER"', h)
        ppr = center.group(1) if center else "0"
        foot = ('<hp:footer id="0" applyPageType="BOTH"><hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" '
                'vertAlign="BOTTOM" linkListIDRef="0" linkListNextIDRef="0" textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
                f'<hp:p id="0" paraPrIDRef="{ppr}" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
                f'<hp:run charPrIDRef="0"><hp:t>{FOOTER_TEXT}</hp:t></hp:run></hp:p></hp:subList></hp:footer>')
        # 2쪽 첫 문단(쪽 나눔 문단)의 첫 run 앞에 꼬리말 컨트롤을 둔다 → 그 쪽부터 적용
        j = att.find(">", 0) + 1
        att = att[:j] + f'<hp:run charPrIDRef="0"><hp:ctrl>{foot}</hp:ctrl></hp:run>' + att[j:]
        s = s[:pstart] + att
    s = s.replace('<hp:margin header="0" footer="0" gutter="0" left="5102" right="5102" top="5669" bottom="6519"/>',
                  '<hp:margin header="0" footer="2267" gutter="0" left="5102" right="5102" top="5669" bottom="4252"/>')
    files[hname], files[sname] = h.encode("utf-8"), s.encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in zin.namelist():
            z.writestr(infos[n], files[n], compress_type=infos[n].compress_type)
    Path(path).write_bytes(buf.getvalue())


def safe(s):
    return re.sub(r'[\\:*?"<>|&]', "·", s.replace("/", "-")).strip()


results = []
for pid, p in packets.items():
    if only and pid not in only:
        continue
    c = contents.get(pid)
    if not c:
        results.append((pid, "NO_CONTENT"))
        continue
    outdir = ROOT / ("경기A+센터" if pid.startswith("G") else "서울A+센터")
    srcdir = WORK / "src"
    outdir.mkdir(exist_ok=True)
    srcdir.mkdir(exist_ok=True)
    name = f"{pid}_{safe(c['short_title'])}"
    md = srcdir / f"{name}.md"
    md.write_text(markdown(p, c), encoding="utf-8")
    spec = srcdir / f"{name}.json"
    out = (outdir / f"{name}_기술이전제안서.hwpx").resolve()
    json.dump({"version": 1, "kind": "brief-report", "output": str(out), "source": md.name,
               "quality": {"hancom": "off", "reject_placeholders": True, "writing": "advisory"}, "metadata_date": "2026-10-24"},
              open(spec, "w", encoding="utf-8"), ensure_ascii=False)
    r = subprocess.run([sys.executable, str(SKILL / "scripts/one_shot.py"), str(spec), "--report", str(srcdir / f"{name}_q.json")],
                       capture_output=True, text=True, encoding="utf-8", cwd=SKILL)
    try:
        rep = json.loads(r.stdout)
        if rep.get("published"):
            postprocess(out)
        results.append((pid, rep.get("status"), rep.get("published"), str(out)))
    except Exception:
        results.append((pid, "ERR", r.stdout[-300:], r.stderr[-300:]))
json.dump(results, open(WORK / "build_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for x in results:
    print(*x)
