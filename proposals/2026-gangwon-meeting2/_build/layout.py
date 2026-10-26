"""hwpx 본문 높이 추정기 — 글자 폭·줄간격·표 셀 크기로 문단별 줄 수와 페이지 높이를 근사한다.
한글 프로그램 없이 '1페이지 넘침'을 점검하기 위한 용도이며, 첨부 양식(template.hwpx)으로 보정한다."""
import re, unicodedata
from functools import lru_cache

HEADER = None


def init(header_xml):
    global HEADER
    HEADER = header_xml


@lru_cache(None)
def char_pr(cid):
    m = re.search(rf'<hh:charPr id="{cid}" height="(\d+)"[^>]*>(.*?)</hh:charPr>', HEADER, re.S)
    ratio = int(re.search(r'<hh:ratio hangul="(\d+)"', m.group(2)).group(1))
    spacing = int(re.search(r'<hh:spacing hangul="(-?\d+)"', m.group(2)).group(1))
    return int(m.group(1)), ratio, spacing


@lru_cache(None)
def para_pr(pid):
    m = re.search(rf'<hh:paraPr id="{pid}"[^>]*>(.*?)</hh:paraPr>', HEADER, re.S).group(1)
    intent = int(re.search(r'<hc:intent value="(-?\d+)"', m).group(1))
    left = int(re.search(r'<hc:left value="(-?\d+)"', m).group(1))
    ls = int(re.search(r'<hh:lineSpacing type="\w+" value="(\d+)"', m).group(1))
    return intent, left, ls


def char_w(ch, cid):
    h, ratio, spacing = char_pr(cid)
    full = h * ratio / 100
    if ch == " ":
        w = full * 0.5
    elif unicodedata.east_asian_width(ch) in ("W", "F", "A") or ch in "·∼→⇒❍□①②③④⑤「」※":
        w = full
    else:
        w = full * 0.55
    return w + full * spacing / 100


def lines(runs, pid, width):
    """runs: [(charPrID, text)] → 줄 수(단어 단위 줄바꿈 근사)."""
    intent, left, _ = para_pr(pid)
    first_w = width - left - max(intent, 0)
    next_w = width - left + min(intent, 0)  # 내어쓰기(intent<0)는 둘째 줄부터 들여씀
    n, cur, avail = 1, 0.0, first_w
    word = 0.0
    for cid, text in runs:
        for ch in text:
            w = char_w(ch, cid)
            word += w
            if cur + word > avail:
                n += 1
                cur, avail = 0.0, next_w
                if word > avail:  # 단어 자체가 한 줄보다 긺
                    cur = word % avail
                    n += int(word // avail)
                    word = 0.0
                    continue
            if ch == " ":
                cur += word
                word = 0.0
    return n


def line_h(runs, pid):
    _, _, ls = para_pr(pid)
    h = max(char_pr(c)[0] for c, _ in runs) if runs else 1000
    return h * ls / 100


def p_runs(p):
    return [(c, "".join(re.findall(r"<hp:t>([^<]*)</hp:t>", body)))
            for c, body in re.findall(r'<hp:run charPrIDRef="(\d+)">(.*?)</hp:run>', p, re.S)] or [("21", "")]


def para_height(p, width):
    pid = re.search(r'paraPrIDRef="(\d+)"', p).group(1)
    runs = p_runs(p)
    texts = [(c, t) for c, t in runs if t] or runs[:1]
    return lines(texts, pid, width) * line_h(texts, pid), lines(texts, pid, width)


def table_height(frag):
    total = 0
    for tr in re.findall(r"<hp:tr>(.*?)</hp:tr>", frag, re.S):
        row = 0
        for tc in re.findall(r"<hp:tc\b.*?</hp:tc>", tr, re.S):
            w, h = map(int, re.search(r'<hp:cellSz width="(\d+)" height="(\d+)"', tc).groups())
            ml, mr, mt, mb = map(int, re.search(r'<hp:cellMargin left="(\d+)" right="(\d+)" top="(\d+)" bottom="(\d+)"', tc).groups())
            inner = sum(para_height(p, w - ml - mr)[0] for p in re.findall(r"<hp:p\b.*?</hp:p>", tc, re.S))
            row = max(row, h, inner + mt + mb)
        total += row
    return total


def top_height(frag, width):
    if "<hp:tbl" in frag:
        return table_height(frag), 0
    return para_height(frag, width)
