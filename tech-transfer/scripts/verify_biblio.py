import json,requests,time,re,xml.etree.ElementTree as ET
import os
from tt_config import DATA
os.chdir(DATA)
K=os.environ['KIPRIS_KEY']
F=json.load(open('final.json')); SF=json.load(open('seoul_final.json',encoding='utf-8'))
ans=sorted({a for l in F.values() for a in l}|{a for l in SF.values() for a,_ in l})
res={}
for a in ans:
    t=requests.get('http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getBibliographyDetailInfoSearch',params={'applicationNumber':a,'ServiceKey':K},timeout=60).text
    r=ET.fromstring(t); s=r.find('.//biblioSummaryInfo')
    g=lambda k:(s.findtext(k) or '').strip() if s is not None else ''
    res[a]={'status':g('registerStatus'),'final':g('finalDisposal'),'regno':g('registerNumber'),'regdate':g('registerDate'),'appdate':g('applicationDate'),
            'orig':g('originalApplicationKind'),'origno':g('originalApplicationNumber'),'origdate':g('originalApplicationDate'),
            'applicants':[x.findtext('name') for x in r.findall('.//applicantInfo')]}
    time.sleep(0.3)
json.dump(res,open('bib.json','w',encoding='utf-8'),ensure_ascii=False)
import collections
print(len(res),collections.Counter(v['status'] for v in res.values()))
for a,v in res.items():
    if v['status'] not in('등록','공개') or v['applicants']!=['대한민국(농촌진흥청장)'] or (v['origdate'] and v['origdate']<'2016.10.23'):
        print('FLAG',a,v)
