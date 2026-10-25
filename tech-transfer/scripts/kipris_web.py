import requests,json,sys
S=requests.Session()
S.headers.update({"X-Requested-With":"XMLHttpRequest","Referer":"https://www.kipris.or.kr/khome/search/searchResult.do","User-Agent":"Mozilla/5.0"})
def search(q,page=1,n=100):
    r=S.post("https://www.kipris.or.kr/kpat/resulta.do",data={"queryText":q,"expression":q,"currentPage":page,"numPerPage":n},timeout=60)
    return r.json()
if __name__=="__main__":
    d=search(sys.argv[1],1,5)
    print(d['countInfo'])
    for r in d['resultList']: print(r['AN'],r['AD'],r['LSTO'],r['AP'],r['TL'])
