import { proxied, buildQS } from "./config.js";

const FSC_BASE    = "https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2";
const DART_BASE   = "https://opendart.fss.or.kr/api";
const KIPRIS_BASE = "https://plus.kipris.or.kr/kipo-api/kipi";
const TODAY       = new Date().toISOString().slice(0, 10).replace(/-/g, "");

// ─── FSC ────────────────────────────────────────────────────────────────────
async function searchFsc(corpNm, apiKey) {
  if (!apiKey) return null;
  try {
    const qs  = buildQS({ serviceKey:apiKey, pageNo:1, numOfRows:3, resultType:"json", basDt:TODAY, corpNm });
    const res = await fetch(proxied(`${FSC_BASE}/getCorpOutline_V2?${qs}`), { headers:{ Accept:"application/json" } });
    const json = await res.json();
    const items = json?.response?.body?.items?.item;
    if (!items) return null;
    const arr = Array.isArray(items) ? items : [items];
    // 가장 근접한 이름 매칭
    const best = arr.find(d => d.corpNm?.includes(corpNm) || corpNm.includes(d.corpNm?.replace(/㈜|주식회사/g,""))) || arr[0];
    const emp  = parseInt(best.enpEmpeCnt) || 0;
    const sale = parseInt(best.enpSaleAmt) || 0;
    const cap  = parseInt(best.enpCptlAmt) || 0;
    const RGN  = ["서울","경기","인천","부산","대구","광주","대전","울산","세종","강원","충북","충남","전북","전남","경북","경남","제주"];
    const addr = best.enpBsadr || "";
    return {
      corpNm:    best.corpNm,
      ceo:       best.enpRprFnm || "-",
      estb:      best.enpEstbDt?.replace(/(\d{4})(\d{2})(\d{2})/, "$1-$2-$3") || "-",
      industry:  best.indutyNm || "-",
      employees: emp,
      revenue:   sale,
      capital:   cap,
      address:   addr,
      region:    RGN.find(k => addr.startsWith(k)) || "기타",
      phone:     best.enpTlno || null,
      homepage:  best.enpHmpgUrl || null,
      crno:      best.crno || null,
      listed:    best.stckMrktListgYn === "Y" || best.kosdaqMrktListgYn === "Y",
      size:      emp>1000?"대기업":emp>300?"중견기업":emp>50?"중기업":emp>5?"소기업":"스타트업",
    };
  } catch { return null; }
}

// ─── DART ────────────────────────────────────────────────────────────────────
async function searchDart(corpNm, apiKey) {
  if (!apiKey) return null;
  try {
    const thisYear = new Date().getFullYear();
    // 1) 공시 목록에서 corp_code 획득
    const qs1 = buildQS({ crtfc_key:apiKey, corp_name:corpNm, bgn_de:`${thisYear-1}0101`, page_count:20, sort:"date", sort_mth:"desc" });
    const r1  = await fetch(proxied(`${DART_BASE}/list.json?${qs1}`), { headers:{ Accept:"application/json" } });
    const j1  = await r1.json();
    if (j1.status !== "000" || !j1.list?.length) return null;

    // 가장 근접한 이름 매칭
    const match = j1.list.find(d => d.corp_nm?.includes(corpNm) || corpNm.includes(d.corp_nm?.replace(/㈜|주식회사/g,""))) || j1.list[0];
    const corpCode = match.corp_code;

    // 2) 기업개황 + 재무 + 공시 병렬 조회
    const [r2, r3, r4] = await Promise.allSettled([
      fetch(proxied(`${DART_BASE}/company.json?${buildQS({ crtfc_key:apiKey, corp_code:corpCode })}`), { headers:{ Accept:"application/json" } }).then(r=>r.json()),
      fetch(proxied(`${DART_BASE}/fnlttSinglAcnt.json?${buildQS({ crtfc_key:apiKey, corp_code:corpCode, bsns_year:thisYear-1, reprt_code:"11011", fs_div:"CFS" })}`), { headers:{ Accept:"application/json" } }).then(r=>r.json()),
      fetch(proxied(`${DART_BASE}/list.json?${buildQS({ crtfc_key:apiKey, corp_code:corpCode, bgn_de:`${thisYear-1}0101`, page_count:5, sort:"date", sort_mth:"desc" })}`), { headers:{ Accept:"application/json" } }).then(r=>r.json()),
    ]);

    const company     = r2.status==="fulfilled" && r2.value.status==="000" ? r2.value : null;
    const finList     = r3.status==="fulfilled" && r3.value.status==="000" ? r3.value.list||[] : [];
    const discList    = r4.status==="fulfilled" && r4.value.status==="000" ? r4.value.list||[] : [];

    // 재무 파싱
    const find = (nm) => finList.find(r=>r.account_nm===nm);
    const toN  = (r)  => parseInt((r?.thstrm_amount||"0").replace(/,/g,""))||0;
    const toNP = (r)  => parseInt((r?.frmtrm_amount||"0").replace(/,/g,""))||0;
    const rev  = find("매출액")||find("수익(매출액)")||find("영업수익");
    const op   = find("영업이익")||find("영업이익(손실)");
    const ni   = find("당기순이익")||find("당기순이익(손실)");
    const revN = toN(rev), revP = toNP(rev);
    const opN  = toN(op),  niN  = toN(ni);
    const growth = revP>0 ? Math.round(((revN-revP)/revP)*100) : null;

    const fmt = n => n>=1e12?`${(n/1e12).toFixed(1)}조`:n>=1e8?`${Math.round(n/1e8)}억`:n>0?`${Math.round(n/1e6)}백만`:"-";

    return {
      corpCode,
      stockCode:  company?.stock_code || match.stock_code || null,
      ceo:        company?.ceo_nm || "-",
      estb:       company?.est_dt?.replace(/(\d{4})(\d{2})(\d{2})/, "$1-$2-$3") || "-",
      employees:  parseInt(company?.emp_no)||0,
      homepage:   company?.hm_url||null,
      capital:    parseInt((company?.capital_amount||"0").replace(/,/g,""))||0,
      industry:   company?.induty_code_name||"-",
      address:    company?.adres||"-",
      revenue:    revN, revenueStr: fmt(revN),
      revenuePrev:revP, revenuePrevStr:fmt(revP),
      opProfit:   opN,  opProfitStr:  fmt(opN),
      netIncome:  niN,  netIncomeStr: fmt(niN),
      growth,
      finYear:    thisYear-1,
      disclosures: discList.slice(0,5).map(d=>({
        title: d.report_nm,
        date:  d.rcept_dt?.replace(/(\d{4})(\d{2})(\d{2})/, "$1.$2.$3"),
        corp:  d.corp_nm,
        filer: d.flr_nm,
        url:   `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${d.rcept_no}`,
      })),
    };
  } catch { return null; }
}

// ─── KIPRIS ─────────────────────────────────────────────────────────────────
function parseKiprisXml(xml) {
  const doc   = new DOMParser().parseFromString(xml, "text/xml");
  const get   = (el,tag)=>el.getElementsByTagName(tag)?.[0]?.textContent?.trim()||"";
  const total = parseInt(get(doc,"totalCount")||"0");
  const items = Array.from(doc.getElementsByTagName("item")).slice(0,5).map(el=>({
    title:  get(el,"inventionTitle"),
    number: get(el,"applicationNumber"),
    date:   get(el,"applicationDate")?.replace(/(\d{4})(\d{2})(\d{2})/, "$1.$2.$3"),
    status: get(el,"registerStatus"),
    ipc:    get(el,"ipcNumber")?.split(",")[0],
    applicant: get(el,"applicantName"),
  }));
  return { total, items };
}

async function searchKipris(corpNm, apiKey) {
  if (!apiKey) return null;
  try {
    // 출원인명으로 검색 (㈜ 제거한 이름으로도 시도)
    const cleanName = corpNm.replace(/㈜|주식회사\s*/g,"").trim();
    const qs  = buildQS({ ServiceKey:apiKey, applicantName:cleanName, docsStart:1, docsCount:20, patent:"true", utility:"true" });
    const res = await fetch(proxied(`${KIPRIS_BASE}/patUtiModInfoSearchSevice/getWordSearch?${qs}`), { headers:{ Accept:"application/xml,*/*" } });
    const xml = await res.text();
    const { total, items } = parseKiprisXml(xml);

    // 상태별 분류
    const registered = items.filter(p=>p.status==="등록").length;
    const pending    = items.filter(p=>p.status==="출원"||p.status==="공개").length;

    // IPC 기술분야 TOP
    const ipcMap = {};
    items.forEach(p=>{ if(p.ipc){ const k=p.ipc.slice(0,3); ipcMap[k]=(ipcMap[k]||0)+1; }});
    const topIpc = Object.entries(ipcMap).sort((a,b)=>b[1]-a[1]).slice(0,3).map(([k])=>k);

    return { total, registered, pending, recent:items, topIpc };
  } catch { return null; }
}

// ─── UNIFIED SEARCH ──────────────────────────────────────────────────────────
export async function searchAllApis(corpNm, keys, onProgress) {
  onProgress?.("fsc", "loading");
  onProgress?.("dart", "loading");
  onProgress?.("kipris", "loading");

  const [fsc, dart, kipris] = await Promise.allSettled([
    searchFsc(corpNm, keys.fsc).then(r=>{    onProgress?.("fsc",    r?"done":"empty"); return r; }).catch(e=>{ onProgress?.("fsc",    "error"); return null; }),
    searchDart(corpNm, keys.dart).then(r=>{ onProgress?.("dart",   r?"done":"empty"); return r; }).catch(e=>{ onProgress?.("dart",   "error"); return null; }),
    searchKipris(corpNm, keys.kipris).then(r=>{onProgress?.("kipris", r?"done":"empty"); return r;}).catch(e=>{ onProgress?.("kipris","error"); return null; }),
  ]);

  return {
    corpNm,
    fsc:    fsc.status    === "fulfilled" ? fsc.value    : null,
    dart:   dart.status   === "fulfilled" ? dart.value   : null,
    kipris: kipris.status === "fulfilled" ? kipris.value : null,
    searchedAt: new Date().toLocaleString("ko-KR"),
  };
}

// ─── MERGE: 3개 소스 → 통합 프로필 ─────────────────────────────────────────
export function mergeProfile(result) {
  const { fsc, dart, kipris } = result;

  // 우선순위: DART > FSC
  const revenue    = dart?.revenue    || fsc?.revenue    || 0;
  const employees  = dart?.employees  || fsc?.employees  || 0;
  const ceo        = dart?.ceo !== "-" ? dart?.ceo : fsc?.ceo || "-";
  const estb       = dart?.estb !== "-" ? dart?.estb : fsc?.estb || "-";
  const industry   = dart?.industry   || fsc?.industry   || "-";
  const homepage   = dart?.homepage   || fsc?.homepage   || null;
  const address    = dart?.address    || fsc?.address    || "-";
  const capital    = dart?.capital    || fsc?.capital    || 0;
  const listed     = fsc?.listed ?? !!dart?.stockCode;
  const region     = fsc?.region || "기타";

  const fmt = n => n>=1e12?`${(n/1e12).toFixed(1)}조`:n>=1e8?`${Math.round(n/1e8)}억`:n>0?`${Math.round(n/1e6)}백만`:"-";

  return {
    name:       result.corpNm,
    ceo, estb, industry, homepage, address, region, listed,
    employees:  employees,
    employeesStr: employees>0 ? `${employees.toLocaleString()}명` : "-",
    revenue, revenueStr: dart?.revenueStr || fmt(revenue),
    opProfit:   dart?.opProfit  || 0, opProfitStr:  dart?.opProfitStr  || "-",
    netIncome:  dart?.netIncome || 0, netIncomeStr: dart?.netIncomeStr || "-",
    capital, capitalStr: fmt(capital),
    revenuePrev:dart?.revenuePrev||0, revenuePrevStr:dart?.revenuePrevStr||"-",
    growth:     dart?.growth ?? null,
    finYear:    dart?.finYear || new Date().getFullYear()-1,
    stockCode:  dart?.stockCode || null,
    crno:       fsc?.crno || null,
    size:       fsc?.size || (employees>1000?"대기업":employees>300?"중견기업":employees>50?"중기업":employees>5?"소기업":"스타트업"),
    // DART 공시
    disclosures: dart?.disclosures || [],
    // KIPRIS 특허
    patentTotal:      kipris?.total      || 0,
    patentRegistered: kipris?.registered || 0,
    patentPending:    kipris?.pending    || 0,
    patentRecent:     kipris?.recent     || [],
    patentTopIpc:     kipris?.topIpc     || [],
    // 데이터 소스 상태
    sources: {
      fsc:    !!fsc,
      dart:   !!dart,
      kipris: !!kipris,
    },
  };
}
