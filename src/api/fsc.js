import { proxied, buildQS } from "./config.js";

const FSC_BASE = "https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2";
const TODAY    = new Date().toISOString().slice(0, 10).replace(/-/g, "");

export async function fetchFscCorpOutline({ apiKey, corpNm = "", crno = "", pageNo = 1, numOfRows = 10 }) {
  const qs  = buildQS({ serviceKey: apiKey, pageNo, numOfRows, resultType: "json", basDt: TODAY,
    ...(corpNm ? { corpNm } : {}), ...(crno ? { crno } : {}) });
  const res = await fetch(proxied(`${FSC_BASE}/getCorpOutline_V2?${qs}`), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json  = await res.json();
  const items = json?.response?.body?.items?.item;
  if (!items) return [];
  return Array.isArray(items) ? items : [items];
}

const RGN = ["서울","경기","인천","부산","대구","광주","대전","울산","세종","강원","충북","충남","전북","전남","경북","경남","제주"];

export function fscToCompany(raw, idx) {
  const emp   = parseInt(raw.enpEmpeCnt) || 0;
  const sale  = parseInt(raw.enpSaleAmt) || 0;
  const cap   = parseInt(raw.enpCptlAmt) || 0;
  const estb  = raw.enpEstbDt?.slice(0, 4) || null;
  const addr  = raw.enpBsadr || "";
  return {
    id:         `fsc-${raw.crno || idx}`,
    name:       raw.corpNm || "-",
    industry:   raw.indutyNm || "기타",
    region:     RGN.find(k => addr.startsWith(k)) || "기타",
    size:       emp > 1000 ? "대기업" : emp > 300 ? "중견기업" : emp > 50 ? "중기업" : emp > 5 ? "소기업" : "스타트업",
    employees:  emp,
    founded:    estb ? parseInt(estb) : null,
    revenue:    sale >= 1e8 ? `${Math.round(sale / 1e8)}억` : sale > 0 ? `${Math.round(sale / 1e6)}백만` : "-",
    revenueRaw: sale,
    capital:    cap  >= 1e8 ? `${Math.round(cap  / 1e8)}억` : cap  > 0 ? `${Math.round(cap  / 1e6)}백만` : "-",
    growth:     null,
    patent:     null,
    export:     false,
    tech:       [],
    desc:       [addr, raw.enpTlno ? `☎ ${raw.enpTlno}` : null].filter(Boolean).join(" · "),
    ceo:        raw.enpRprFnm  || "-",
    homepage:   raw.enpHmpgUrl || null,
    crno:       raw.crno       || null,
    listed:     raw.stckMrktListgYn === "Y" || raw.kosdaqMrktListgYn === "Y",
    source:     "fsc",
    dart:       null,
    kipris:     null,
  };
}
