import requests,sys,xml.etree.ElementTree as ET
import os
KEY=os.environ['KIPRIS_KEY']
def adv(page=1,rows=500,**kw):
    p={"applicant":"농촌진흥청","applicationDate":"20161023~20261024","patent":"true","utility":"true","numOfRows":rows,"pageNo":page,"ServiceKey":KEY}
    p.update(kw)
    r=requests.get("http://plus.kipris.or.kr/kipo-api/kipi/patUtiModInfoSearchSevice/getAdvancedSearch",params=p,timeout=60)
    return r.text
if __name__=="__main__":
    t=adv(1,3)
    print(t[:3000].replace(KEY,'***'))
