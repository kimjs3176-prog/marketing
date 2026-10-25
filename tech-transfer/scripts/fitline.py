"""1쪽 문단 중 마지막 줄이 짧게 넘어간 문단만 자간을 줄여 한 줄 덜 쓰게 한다.

한글에서 문단별 (시작 줄, 끝 줄, 마지막 줄 글자 수)를 재고, 필요한 만큼만
해당 문단 run의 charPr를 자간 음수 복제본으로 바꾼 뒤 다시 잰다.
"""
import io, json, math, re, sys, zipfile
from pathlib import Path
import win32com.client as w
from tt_config import DATA

MAX_SHRINK = int(__import__('os').environ.get('MAX_SHRINK', '12'))
START = int(__import__('os').environ.get('START', '0'))      # 자간 최대 -15% (-10% 이하부터 장평 95%)
TAIL_RATIO = 0.22    # 마지막 줄이 문단 글자의 18% 이하일 때만 대상


def measure(h, path):
    """1쪽 최상위 문단별 {index: (lines, tail, total)}."""
    h.Open(str(path), "HWPX", "forceopen:true")
    out = {}
    i = 0
    while h.SetPos(0, i, 0):
        a = h.KeyIndicator()
        if a[3] > 1:
            break
        h.Run("MoveParaEnd")
        b = h.KeyIndicator()
        total = h.GetPos()[2]
        h.Run("MoveLineBegin")
        tail = total - h.GetPos()[2]
        lines = b[5] - a[5] + 1 if b[3] == a[3] else 9
        out[i] = (lines, tail, total)
        i += 1
    h.Clear(1)
    return out


def top_paragraph_spans(s):
    """<hs:sec> 바로 아래 <hp:p> 들의 (start, end) — 중첩 문단(표 셀 등)은 건너뛴다."""
    spans, depth, pos, start = [], 0, 0, None
    tok = re.compile(r"<hp:p\b|</hp:p>")
    for m in tok.finditer(s):
        if m.group(0).startswith("<hp:p"):
            if depth == 0:
                start = m.start()
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                spans.append((start, m.end()))
    return spans


def tighten(path, idxs):
    """해당 문단 텍스트의 ' · ' 를 '·' 로 바꿔 폭을 줄인다."""
    zin = zipfile.ZipFile(io.BytesIO(Path(path).read_bytes()))
    files = {n: zin.read(n) for n in zin.namelist()}
    infos = {n: zin.getinfo(n) for n in zin.namelist()}
    sname = next(n for n in files if n.endswith("section0.xml"))
    s = files[sname].decode("utf-8")
    spans = top_paragraph_spans(s)
    out, last = [], 0
    for idx, (a, b) in enumerate(spans):
        if idx in idxs:
            out += [s[last:a], s[a:b].replace(" · ", "·")]
            last = b
    out.append(s[last:])
    files[sname] = "".join(out).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in zin.namelist():
            z.writestr(infos[n], files[n], compress_type=infos[n].compress_type)
    Path(path).write_bytes(buf.getvalue())


def untighten(path, idxs):
    """줄이 줄지 않은 문단은 '·' 를 다시 ' · ' 로 (원래 띄어 쓴 체크리스트 문단만)."""
    zin = zipfile.ZipFile(io.BytesIO(Path(path).read_bytes()))
    files = {n: zin.read(n) for n in zin.namelist()}
    infos = {n: zin.getinfo(n) for n in zin.namelist()}
    sname = next(n for n in files if n.endswith("section0.xml"))
    s = files[sname].decode("utf-8")
    spans = top_paragraph_spans(s)
    out, last = [], 0
    for idx, (a, b) in enumerate(spans):
        if idx in idxs:
            para = re.sub(r"(<hp:t>)([^<]*)(</hp:t>)", lambda m: m.group(1) + re.sub(r"\s*·\s*", " · ", m.group(2)) + m.group(3), s[a:b])
            out += [s[last:a], para]
            last = b
    out.append(s[last:])
    files[sname] = "".join(out).encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in zin.namelist():
            z.writestr(infos[n], files[n], compress_type=infos[n].compress_type)
    Path(path).write_bytes(buf.getvalue())


def apply(path, plan):
    """plan = {para_index: spacing(음수%)} 를 XML에 반영."""
    zin = zipfile.ZipFile(io.BytesIO(Path(path).read_bytes()))
    files = {n: zin.read(n) for n in zin.namelist()}
    infos = {n: zin.getinfo(n) for n in zin.namelist()}
    hname = next(n for n in files if n.endswith("header.xml"))
    sname = next(n for n in files if n.endswith("section0.xml"))
    h, s = files[hname].decode("utf-8"), files[sname].decode("utf-8")
    cnt = int(re.search(r'<hh:charProperties itemCnt="(\d+)"', h).group(1))
    clones = {}

    def clone(cid, sp):
        nonlocal h, cnt
        key = (cid, sp)
        if key in clones:
            return clones[key]
        m = re.search(r'<hh:charPr id="%s".*?</hh:charPr>' % cid, h, re.S)
        c = re.sub(r'id="%s"' % cid, 'id="%d"' % cnt, m.group(0), count=1)
        c = re.sub(r'<hh:spacing [^/]*/>', '<hh:spacing hangul="{0}" latin="{0}" hanja="{0}" japanese="{0}" other="{0}" symbol="{0}" user="{0}"/>'.format(sp), c)
        r = 95 if sp <= -10 else 100
        c = re.sub(r'<hh:ratio [^/]*/>', '<hh:ratio hangul="{0}" latin="{0}" hanja="{0}" japanese="{0}" other="{0}" symbol="{0}" user="{0}"/>'.format(r), c)
        e = h.index("</hh:charProperties>")
        h = h[:e] + c + h[e:]
        clones[key] = cnt
        cnt += 1
        return clones[key]

    spans = top_paragraph_spans(s)
    pieces, last = [], 0
    for idx, (a, b) in enumerate(spans):
        if idx not in plan:
            continue
        para = s[a:b]
        para = re.sub(r'(<hp:run charPrIDRef=")(\d+)(")', lambda m: m.group(1) + str(clone(m.group(2), plan[idx])) + m.group(3), para)
        pieces.append(s[last:a])
        pieces.append(para)
        last = b
    pieces.append(s[last:])
    s = "".join(pieces)
    h = re.sub(r'<hh:charProperties itemCnt="\d+"', f'<hh:charProperties itemCnt="{cnt}"', h, count=1)
    files[hname], files[sname] = h.encode("utf-8"), s.encode("utf-8")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n in zin.namelist():
            z.writestr(infos[n], files[n], compress_type=infos[n].compress_type)
    Path(path).write_bytes(buf.getvalue())


def candidates(meas, done):
    plan = {}
    for i, (lines, tail, total) in meas.items():
        if lines < 2 or total == 0 or lines > 4:
            continue
        need = tail / total * 100
        cur = done.get(i, 0)
        if tail / total <= TAIL_RATIO:
            sp = -min(MAX_SHRINK, max(-cur + 3, math.ceil(need * 0.8) + 2, START + 1))
            if sp != cur:
                plan[i] = sp
    return plan


if __name__ == "__main__":
    files = [Path(x).resolve() for x in sys.argv[1:]]
    h = w.Dispatch("HWPFrame.HwpObject")
    h.RegisterModule("FilePathCheckDLL", "FilePathCheckerModule")
    h.XHwpWindows.Item(0).Visible = True
    report = {}
    for f in files:
        done = {}
        first = candidates(measure(h, f), {})
        if first:
            tighten(f, set(first))
        for rnd in range(4):
            meas = measure(h, f)
            plan = candidates(meas, done)
            if not plan:
                break
            done.update(plan)
            # apply는 원본 charPr 기준으로 다시 복제해야 하므로 매 라운드 누적 plan 전체를 새로 적용
            apply(f, {k: v for k, v in plan.items()})
        meas = measure(h, f)
        left = [i for i, (l, t, tot) in meas.items() if l >= 2 and l <= 4 and tot and t / tot <= TAIL_RATIO]
        left_before = list(left)
        if left:
            tighten(f, set(left))
            meas = measure(h, f)
            left = [i for i, (l, t, tot) in meas.items() if l >= 2 and l <= 4 and tot and t / tot <= TAIL_RATIO]
        # 끝내 한 줄로 안 된 문단은 원상 복구(자간 0, '·' 띄어쓰기) → 어색한 벌어짐·빽빽함 방지
        meas = measure(h, f)
        multi = {i for i, (l, t, tot) in meas.items() if l >= 2}
        back = {i: 0 for i in done if i in multi}
        if back:
            apply(f, back)
        tight = (set(first) | set(left_before)) & multi & {12, 13, 14}
        if tight:
            untighten(f, tight)
        for i in back:
            done.pop(i, None)
        report[f.name] = {"condensed": done, "still_short_tail": left, "reverted": sorted(set(back) | tight)}
        print(f.name, done, "left", left, flush=True)
    h.Quit()
    json.dump(report, open(DATA / "fitline.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
