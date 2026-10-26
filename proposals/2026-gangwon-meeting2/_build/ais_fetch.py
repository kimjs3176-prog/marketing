"""AIS(Agri IP Summary, atipsum.lovable.app)에서 특허별 AI 요약서와 사업화 평가를 가져와 ais.json에 저장한다.
AIS 웹화면과 같은 순서(특허 조회 → AI 요약서 → 사업화 분석)로 호출하며, 이미 받은 특허는 건너뛴다.
사용: python3 ais_fetch.py"""
import json, time, urllib.request
from pathlib import Path

FN = "https://rrvraugvigylkdpstwsl.supabase.co/functions/v1/"
# AIS 웹앱에 공개된 anon 키
ANON = ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJydnJhdWd2aWd5bGtkcHN0d3NsIiwicm9sZSI6"
        "ImFub24iLCJpYXQiOjE3Njg5NTk4MTgsImV4cCI6MjA4NDUzNTgxOH0.Ie360VrutksbiJ8vTxW7FCSMPij7qf-BPzvwoBsMFU8")
here = Path(__file__).parent
out_path = here / "ais.json"
out = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}

def post(fn, body, timeout=240):
    req = urllib.request.Request(FN + fn, data=json.dumps(body, ensure_ascii=False).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": f"Bearer {ANON}"})
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8")

def summarize(app, data):
    text, final = "", None
    for line in post("summarize-patent", {"patentNumber": app, "patentData": data, "forceRegenerate": False}).splitlines():
        if not line.startswith("data: ") or line == "data: [DONE]":
            continue
        d = json.loads(line[6:])
        if "final_content" in d:
            final = d["final_content"]
        elif d.get("choices"):
            text += d["choices"][0]["delta"].get("content", "")
    return final or text

apps = sorted({a for v in json.loads((here / "selection.json").read_text()).values() for a in v})
for app in apps:
    if out.get(app, {}).get("score") is not None:
        continue
    try:
        fp = json.loads(post("fetch-patent", {"patentNumber": app}, 90))
        data = fp["data"]
        summary = summarize(app, data)
        ac = json.loads(post("analyze-commercialization", {"patentNumber": app, "patentData": data,
                                                           "summaryContent": summary, "analysisMode": "detailed"}))
        out[app] = {"summary": summary, "score": ac.get("score"), "details": ac.get("details"),
                    "inventors": data.get("inventors"), "classifications": data.get("classifications")}
        print(app, ac.get("score"), flush=True)
    except Exception as e:
        print(app, "ERROR", e, flush=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    time.sleep(2)
