import { proxied, buildQS } from "./config.js";

const DART_BASE = "https://opendart.fss.or.kr/api";

// ─── 1. 회사명으로 공시목록 검색 → corp_code 획득 ─────────────────────────
export async function dartSearchCorp({ apiKey, corpName, pageCount = 10 }) {
  const thisYear = new Date().getFullYear();
  const qs = buildQS({
    crtfc_key: apiKey,
    corp_name:  corpName,
    bgn_de:     `${thisYear - 1}0101`,
    page_count: pageCount,
    sort:       "date",
    sort_mth:   "desc",
  });
  const res  = await fetch(proxied(`${DART_BASE}/list.json?${qs}`), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  if (json.status !== "000") throw new Error(json.message || "DART 오류");
  const list = json.list || [];
  // 중복 corp_code 제거 → 고유 기업 목록
  const seen = new Set();
  return list.filter(d => { if (seen.has(d.corp_code)) return false; seen.add(d.corp_code); return true; })
             .map(d => ({ corp_code: d.corp_code, corp_name: d.corp_nm, stock_code: d.stock_code }));
}

// ─── 2. 기업개황 조회 ────────────────────────────────────────────────────
export async function dartGetCompany({ apiKey, corpCode }) {
  const qs  = buildQS({ crtfc_key: apiKey, corp_code: corpCode });
  const res = await fetch(proxied(`${DART_BASE}/company.json?${qs}`), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  if (json.status !== "000") throw new Error(json.message || "DART 오류");
  return json;
}

// ─── 3. 단일 재무제표 조회 (사업보고서 기준) ─────────────────────────────
export async function dartGetFinancials({ apiKey, corpCode, year }) {
  const qs  = buildQS({ crtfc_key: apiKey, corp_code: corpCode, bsns_year: year, reprt_code: "11011", fs_div: "CFS" });
  const res = await fetch(proxied(`${DART_BASE}/fnlttSinglAcnt.json?${qs}`), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  if (json.status !== "000") throw new Error(json.message || "DART 재무 오류");
  return json.list || [];
}

// ─── 4. 최근 공시 목록 ───────────────────────────────────────────────────
export async function dartGetDisclosures({ apiKey, corpCode, pageCount = 5 }) {
  const thisYear = new Date().getFullYear();
  const qs  = buildQS({
    crtfc_key:  apiKey,
    corp_code:  corpCode,
    bgn_de:     `${thisYear - 1}0101`,
    page_count: pageCount,
    sort:       "date",
    sort_mth:   "desc",
  });
  const res = await fetch(proxied(`${DART_BASE}/list.json?${qs}`), { headers: { Accept: "application/json" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  if (json.status !== "000") throw new Error(json.message || "DART 오류");
  return json.list || [];
}

// ─── 재무 파싱 헬퍼 ──────────────────────────────────────────────────────
export function parseFinancials(list) {
  const find = (name) => list.find(r => r.account_nm === name);
  const toN   = (r)  => parseInt((r?.thstrm_amount || "0").replace(/,/g, "")) || 0;
  const toNP  = (r)  => parseInt((r?.frmtrm_amount || "0").replace(/,/g, "")) || 0;

  const rev  = find("매출액") || find("수익(매출액)") || find("영업수익");
  const op   = find("영업이익") || find("영업이익(손실)");
  const ni   = find("당기순이익") || find("당기순이익(손실)");

  const revN   = toN(rev),   revP  = toNP(rev);
  const opN    = toN(op);
  const niN    = toN(ni);
  const growth = revP > 0 ? Math.round(((revN - revP) / revP) * 100) : null;

  return {
    revenue:    revN >= 1e8 ? `${Math.round(revN / 1e8)}억` : revN > 0 ? `${Math.round(revN / 1e6)}백만` : "-",
    revenueRaw: revN,
    opProfit:   opN >= 1e8  ? `${Math.round(opN  / 1e8)}억` : opN  > 0 ? `${Math.round(opN  / 1e6)}백만` : "-",
    netIncome:  niN >= 1e8  ? `${Math.round(niN  / 1e8)}억` : niN  > 0 ? `${Math.round(niN  / 1e6)}백만` : "-",
    growth,
  };
}

// ─── 공시 타입 라벨 매핑 ─────────────────────────────────────────────────
export function disclosureLabel(rptNm) {
  if (rptNm.includes("사업보고서"))   return { label: "사업보고서",    color: "#60a5fa" };
  if (rptNm.includes("분기보고서"))   return { label: "분기보고서",    color: "#818cf8" };
  if (rptNm.includes("반기보고서"))   return { label: "반기보고서",    color: "#a78bfa" };
  if (rptNm.includes("증자"))        return { label: "유상증자",      color: "#4ade80" };
  if (rptNm.includes("합병"))        return { label: "합병",          color: "#f59e0b" };
  if (rptNm.includes("인수"))        return { label: "M&A",          color: "#f59e0b" };
  if (rptNm.includes("임원"))        return { label: "임원변동",      color: "#94a3b8" };
  return { label: "공시",            color: "#475569" };
}
