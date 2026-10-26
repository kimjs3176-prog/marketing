"""기업별 기술이전 제안서(.hwpx) 생성 — 첨부 양식(template.hwpx)의 문단·표 구조를 그대로 복제해 내용만 바꾼다.
입력: companies.json, selection.json, proposals.json, kipris.json, ais.json
사용: python3 make_hwpx.py"""
import json, re, zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import layout

HERE = Path(__file__).parent
OUT = HERE.parent / "제안서"
TODAY = date(2026, 10, 26)
CENTER = "강원센터 농식품 벤처육성"
NUM = "①②③④⑤"

load = lambda n: json.loads((HERE / n).read_text(encoding="utf-8"))
companies, selection, props, kipris, ais = (load(n) for n in
    ("companies.json", "selection.json", "proposals.json", "kipris.json", "ais.json"))

tpl = zipfile.ZipFile(HERE / "template.hwpx")
SEC = tpl.read("Contents/section0.xml").decode("utf-8")
HEAD, BODY_START = SEC[:SEC.index("<hp:p ")], SEC.index("<hp:p ")
TAIL = SEC[SEC.rindex("</hs:sec>"):]
layout.init(tpl.read("Contents/header.xml").decode("utf-8"))
WIDTH = 49324                 # 본문 폭(용지 59528 - 좌우 여백 5102×2)
BODY_MAX, ATT_MAX = 71200, 72779  # 첨부 양식 본문·붙임 페이지의 추정 높이 — 이 이하면 1페이지에 들어감


def top_paragraphs(xml):
    """hs:sec 바로 아래의 hp:p 조각 목록(표 안의 문단은 부모 조각에 포함)."""
    frags, depth, start = [], 0, 0
    for m in re.finditer(r"<(/?)hp:p\b[^>]*?(/?)>", xml):
        if not m.group(1):
            if depth == 0:
                start = m.start()
            if not m.group(2):
                depth += 1
            elif depth == 0:
                frags.append(xml[start:m.end()])
        else:
            depth -= 1
            if depth == 0:
                frags.append(xml[start:m.end()])
    return frags


T = top_paragraphs(SEC[BODY_START:SEC.rindex("</hs:sec>")])
assert len(T) == 61, len(T)


def set_texts(frag, values):
    """조각 안의 <hp:t>텍스트</hp:t>를 순서대로 values로 교체(None이면 유지)."""
    it = iter(values)
    def rep(m):
        v = next(it, None)
        return m.group(0) if v is None else f"<hp:t>{escape(v)}</hp:t>"
    return re.sub(r"<hp:t>[^<]*</hp:t>", rep, frag)


def runs(open_tag, parts):
    return open_tag + "".join(f'<hp:run charPrIDRef="{c}"><hp:t>{escape(t)}</hp:t></hp:run>' for c, t in parts if t) + "</hp:p>"


def p_open(frag):
    return frag[:frag.index(">") + 1]


def body_bullet(label, text):  # 본문 '  ❍ (라벨) 내용' (양식 4번 문단)
    return runs(p_open(T[4]), [("42", "  ❍ "), ("43", f"({label})"), ("42", f" {text}")])


def bold_split(text, normal, bold):
    out = []
    for i, seg in enumerate(re.split(r"\*\*", text)):
        out.append((bold if i % 2 else normal, seg))
    return out


def ann_bullet(label, text):  # 붙임 '  ❍ (라벨) 내용' — **굵게** 구간 유지 (양식 32번 문단)
    return runs(p_open(T[32]), [("21", "  ❍ "), ("22", f"({label})")] + bold_split(" " + text, "21", "22"))


def ymd(s):
    y, m, d = map(int, re.findall(r"\d+", s)[:3])
    return date(y, m, d)


def expiry(k):
    a = ymd(k["appDate"])
    e = a.replace(year=a.year + 20)
    return e, round((e - TODAY).days / 365.25)


def section(md, name):
    m = re.search(rf"##\s*{name}[^\n]*\n(.*?)(?=\n##\s|\Z)", md, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def sentences(text, n):
    # 기울임(*)·코드(`) 표기 제거, **굵게**만 유지
    text = "**".join(part.replace("*", "") for part in text.replace("`", "").split("**"))
    return " ".join(re.split(r"(?<=다\.)\s+", text)[:n])


def pno(k):
    return k["appNo"] if k["status"] != "등록" else f"{k['appNo']}, 등록 {k['regNo']}"


def page_h(frags):
    return sum(layout.top_height(f, WIDTH)[0] for f in frags)


def build(c):
    code = c["code"]
    P, apps = props[code], selection[code]
    K = [kipris[a] for a in apps]
    A = [ais.get(a) or {} for a in apps]
    out = []
    out.append(T[0].replace("서울A+센터 농식품 벤처육성", CENTER))
    out.append(set_texts(T[1], [f"「{P['short']}」 기술이전 제안"]))
    out += [T[2], T[3],
            body_bullet("아이템", f"{c['item']} (기업코드 {code})"),
            body_bullet("제안", P["pitch"]), T[6], T[7]]
    rows = ["추천 특허 (출원번호 · 상태)", "핵심 기술 → 적용"]
    for k, core in zip(K, P["core"]):
        rows += [f"{k['title']} ({k['appNo']}, {'등록 ' + k['regNo'] if k['status'] == '등록' else '공개'})", core]
    out.append(set_texts(T[8], rows))
    exp = [expiry(k) for k in K]
    terms = " ".join(f"{NUM[i]} {e.year}.{e.month}{'(공개)' if k['status'] != '등록' else ''}"
                     for i, ((e, _), k) in enumerate(zip(exp, K)))
    yrs = sorted(r for _, r in exp)
    n_open = sum(k["status"] != "등록" for k in K)
    form = f"통상실시권 {len(K)}건" + (f"(공개 {n_open}건 포함)" if n_open else "") + " · 응용범위 검토"
    out += [T[9], T[10],
            body_bullet("권리기간", f"{terms} 만료 · 잔여 {yrs[0]}∼{yrs[-1]}년" if yrs[0] != yrs[-1] else f"{terms} 만료 · 잔여 약 {yrs[0]}년"),
            body_bullet("인허가", P["permit"]),
            body_bullet("도입 형태", form),
            body_bullet("추가 개발", P["dev"]),
            T[15], T[16],
            body_bullet("제품", P["product"]),
            body_bullet("시장", P["market"]),
            set_texts(T[19], [f"  ⇒ {P['goal']}"]),
            T[20],
            set_texts(T[21], [f"    ※ KIPRIS Plus 검증({TODAY.year}. {TODAY.month}. {TODAY.day}.) 농진청 단독·10년 내 출원 / 붙임 AI 요약서"]),
            ]
    if page_h(out) > BODY_MAX:  # 특허명이 길어 넘치면 본문 빈 줄(4개)만 작은 글자(8pt)로 줄여 1페이지에 맞춘다
        for j in (2, 6, 9, 15):
            out[j] = out[j].replace('charPrIDRef="21"', 'charPrIDRef="9"')
    warn = []
    title_cell = re.search(r"<hp:p\b[^>]*>(?:(?!</hp:p>).)*「.*?</hp:p>", out[1], re.S).group(0)
    if layout.para_height(title_cell, 49324 - 1020)[1] > 1:
        warn.append("제목이 2줄")
    for f, t in zip(out[4:], T[4:22]):  # 각 항목은 양식의 같은 문단보다 줄 수가 많으면 안 됨
        if "<hp:tbl" not in f and layout.top_height(f, WIDTH)[1] > layout.top_height(t, WIDTH)[1]:
            warn.append("줄 초과: " + "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", f)).strip()[:24])
    if page_h(out) > BODY_MAX:
        warn.append(f"본문 높이 {page_h(out):.0f} > {BODY_MAX}")
    out.append(T[22])
    for i, (k, a, (e, left)) in enumerate(zip(K, A, exp)):
        page = [T[22], T[23]] if i == 0 else [T[35], T[36]]
        d = a.get("details") or {}
        md = a.get("summary", "")
        inv = k["inventors"]
        a_d = ymd(k["appDate"])
        reg = f"{k['regNo']} ({ymd(k['regDate']).strftime('%Y. %m. %d.')} 등록)" if k["status"] == "등록" else "미등록(공개)"
        head = [set_texts(T[24], [f"□ [붙임 {i + 1}] 특허 요약서 {NUM[i]}"]),
                set_texts(T[25], [None, k["title"]]), T[26],
                set_texts(T[27], [None, None, None, f"{k['appNo']} ({a_d.strftime('%Y. %m. %d.')} 출원)",
                                  None, reg, None, f"{e.strftime('%Y.%m.%d')} 만료 (잔여 약 {left}년)",
                                  None, f"{inv[0]} 외 {len(inv) - 1}명 · {k['ipc'][0]}" if len(inv) > 1 else f"{inv[0]} · {k['ipc'][0]}"]),
                T[28], T[29],
                set_texts(T[30], [None] * 5 + [f"{a.get('score', '-')}점", f"{d.get('technologyScore', '-')}점",
                                               f"{d.get('marketScore', '-')}점", f"{d.get('businessScore', '-')}점",
                                               f"TRL {d.get('trl', '-')}"]),
                T[31]]
        # AIS 요약 3항목: 양식 분량(2·3·3문장)에서 시작해 1페이지에 들어갈 때까지 긴 항목부터 한 문장씩 줄인다
        secs = [section(md, "발명요약"), section(md, "농산업활용"), section(md, "상용화전망")]
        labels, counts = ["발명 요약", "농산업 활용", "상용화 전망"], [2, 3, 3]
        while True:
            bullets = [ann_bullet(l, sentences(t, n)) for l, t, n in zip(labels, secs, counts)]
            if page_h(page[1:] + head + bullets) <= ATT_MAX or max(counts) == 1:
                break
            j = max((j for j in range(3) if counts[j] > 1), key=lambda j: layout.top_height(bullets[j], WIDTH)[1])
            counts[j] -= 1
        if page_h(page[1:] + head + bullets) > ATT_MAX:
            warn.append(f"붙임 {i + 1} 높이 초과")
        out += (page[1:] if i == 0 else page) + head + bullets
    # 문단·표 id 재부여(머리말/꼬리말 id="0"은 유지)
    n = iter(range(1000000001, 1000099999))
    body = re.sub(r'(<hp:(?:p|tbl) id=")(\d+)(")', lambda m: m.group(0) if m.group(2) == "0" else f"{m.group(1)}{next(n)}{m.group(3)}", "".join(out))
    return HEAD + body + TAIL, f"「{P['short']}」 기술이전 제안", body, warn


def preview_text(body):
    paras = [ "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", p)) for p in re.findall(r"<hp:p\b.*?</hp:p>", body)]
    return "\r\n".join(p for p in paras)[:1024]


OUT.mkdir(exist_ok=True)
for old in OUT.glob("*.hwpx"):  # 파일명이 바뀌어도 이전 산출물이 남지 않도록 비운다
    old.unlink()
for i, c in enumerate(companies, 1):
    sec, title, body, warn = build(c)
    dst = OUT / f"{i:02d}_{c['code']}_{props[c['code']]['short'].replace(' ', '')}_기술이전제안.hwpx"
    with zipfile.ZipFile(dst, "w") as z:
        for info in tpl.infolist():
            data = tpl.read(info.filename)
            if info.filename == "Contents/section0.xml":
                data = sec.encode("utf-8")
            elif info.filename == "Contents/content.hpf":
                data = re.sub(r"<opf:title>.*?</opf:title>", f"<opf:title>{escape(title)}</opf:title>", data.decode("utf-8")).encode("utf-8")
            elif info.filename == "Preview/PrvText.txt":
                data = preview_text(body).encode("utf-8")
            z.writestr(info.filename, data, zipfile.ZIP_STORED if info.filename == "mimetype" else zipfile.ZIP_DEFLATED)
    print(dst.name, *(["⚠ " + "; ".join(warn)] if warn else []))
