import json,time,math
import os
from kipris_web import search
from tt_config import DATA
os.chdir(DATA)
q="AP=[농촌진흥청]*AD=[20161023~20261023]"
keep=["AN","AD","OPN","OPD","GN","GD","LSTO","LD","TL","AB","IPC","AP","IN","TRH","RH","PR"]
out=[];p=1
while True:
    for t in range(3):
        try: d=search(q,p,100);break
        except Exception as e: print("retry",p,e);time.sleep(5)
    rl=d['resultList']
    out+= [{k:r.get(k) for k in keep} for r in rl]
    tot=d['countInfo']['totalcount']; print(p,len(out),tot,flush=True)
    if not rl or len(out)>=tot: break
    p+=1; time.sleep(1)
json.dump(out,open("rda.json","w",encoding="utf-8"),ensure_ascii=False)
