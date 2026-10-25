"""AIS(atipsum.lovable.app) 백엔드로 특허 AI 요약·사업화 분석 수집."""
import json, os, sys, time, concurrent.futures as cf
from pathlib import Path
import requests

from tt_config import DATA
KEY = os.environ["AIS_ANON_KEY"]
BASE = "https://rrvraugvigylkdpstwsl.supabase.co/functions/v1/"
H = {"Content-Type": "application/json", "Authorization": f"Bearer {KEY}", "apikey": KEY,
     "Origin": "https://atipsum.lovable.app", "Referer": "https://atipsum.lovable.app/"}
OUT = DATA / "ais"
OUT.mkdir(exist_ok=True)


def call(fn, body, stream=False, timeout=240):
    for k in range(7):
        r = requests.post(BASE + fn, headers=H, json=body, timeout=timeout, stream=stream)
        if r.status_code != 429:
            break
        wait = int(r.headers.get("Retry-After") or 0) or 30 * 2 ** k
        print(f"429 {fn} wait {wait}s", flush=True)
        time.sleep(min(wait, 600))
    r.raise_for_status()
    r.encoding = 'utf-8'
    if not stream:
        return r.json()
    txt = []
    for line in r.iter_lines(decode_unicode=True):
        if line and line.startswith("data:"):
            d = line[5:].strip()
            if d == "[DONE]":
                break
            try:
                txt.append(json.loads(d)["choices"][0]["delta"].get("content", ""))
            except Exception:
                pass
    return "".join(txt)


def fan(a):
    return f"{a[:2]}-{a[2:6]}-{a[6:]}"


def one(an):
    f = OUT / f"{an}.json"
    if f.exists():
        old = json.loads(f.read_text(encoding="utf-8"))
        if len(old.get("summary", "")) > 500 and "commercialization" in old:
            return an, "cached"
    pn = fan(an)
    res = {"an": an}
    fp = call("fetch-patent", {"patentNumber": pn, "forceRegenerate": False})
    pdata = fp["data"]
    res["patent"] = {k: pdata.get(k) for k in ("title", "applicationNumber", "registrationNumber", "filingDate", "registrationDate", "legalStatus", "inventors", "classifications")}
    res["summary"] = call("summarize-patent", {"patentNumber": pn, "patentData": pdata, "forceRegenerate": False}, stream=True)
    try:
        res["commercialization"] = call("analyze-commercialization", {"patentNumber": pn, "patentData": pdata, "summaryContent": res["summary"], "analysisMode": "detailed"}, timeout=300)
    except Exception as e:
        res["commercialization_error"] = str(e)[:200]
    reg = (pdata.get("registrationNumber") or "").replace("-", "")
    if reg:
        reg = reg if len(reg) >= 13 else (reg + "0000")
        try:
            res["govt"] = call("govt-patent", {"registrationNumber": reg}).get("data")
            res["register"] = call("patent-register", {"registrationNumber": reg}).get("data")
        except Exception as e:
            res["govt_error"] = str(e)[:200]
    f.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return an, "ok"


if __name__ == "__main__":
    ans = sys.argv[1:]
    with cf.ThreadPoolExecutor(1) as ex:
        for fut in cf.as_completed([ex.submit(one, a) for a in ans]):
            try:
                print(*fut.result(), flush=True)
            except Exception as e:
                print("ERR", e, flush=True)
