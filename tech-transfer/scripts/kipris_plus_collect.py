import json,time,xml.etree.ElementTree as ET,collections
import os
from kipris_plus import adv
from tt_config import DATA
os.chdir(DATA)
out={};p=1
while True:
    t=adv(p,500); root=ET.fromstring(t)
    items=root.findall('.//item')
    for it in items:
        x={c.tag:(c.text or '') for c in it}; out[x['applicationNumber']]=x
    tc=root.findtext('.//totalCount') or root.findtext('.//count/totalCount')
    print(p,len(items),len(out),tc,flush=True)
    if len(items)<500: break
    p+=1; time.sleep(1)
json.dump(out,open('kp_rda.json','w',encoding='utf-8'),ensure_ascii=False)
print(collections.Counter(x['registerStatus'] for x in out.values()))
