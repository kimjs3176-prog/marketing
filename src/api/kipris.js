import { proxied, buildQS } from "./config.js";

const KIPRIS_BASE = "https://plus.kipris.or.kr/kipo-api/kipi";

// ─── 출원인명으로 특허 검색 ───────────────────────────────────────────────
export async function kiprisSearchByApplicant({ apiKey, applicantName, docsStart = 1, docsCount = 10 }) {
  const qs = buildQS({
    ServiceKey:    apiKey,
    applicantName,
    docsStart,
    docsCount,
    patent:        "true",
    utility:       "true",  // 실용신안 포함
  });
  const url = proxied(`${KIPRIS_BASE}/patUtiModInfoSearchSevice/getWordSearch?${qs}`);
  const res  = await fetch(url, { headers: { Accept: "application/xml, text/xml, */*" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  return parseKiprisXml(text);
}

// ─── 키워드(발명의 명칭/요약)로 특허 검색 ───────────────────────────────
export async function kiprisSearchByKeyword({ apiKey, keyword, docsStart = 1, docsCount = 10 }) {
  const qs = buildQS({
    ServiceKey: apiKey,
    word:       keyword,
    docsStart,
    docsCount,
    patent:     "true",
    utility:    "true",
  });
  const url = proxied(`${KIPRIS_BASE}/patUtiModInfoSearchSevice/getWordSearch?${qs}`);
  const res  = await fetch(url, { headers: { Accept: "application/xml, text/xml, */*" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  return parseKiprisXml(text);
}

// ─── IPC 코드로 기술분야 특허 검색 ──────────────────────────────────────
export async function kiprisSearchByIpc({ apiKey, ipcCode, docsStart = 1, docsCount = 10 }) {
  const qs = buildQS({
    ServiceKey: apiKey,
    ipcCode,
    docsStart,
    docsCount,
    patent:     "true",
  });
  const url = proxied(`${KIPRIS_BASE}/patUtiModInfoSearchSevice/getWordSearch?${qs}`);
  const res  = await fetch(url, { headers: { Accept: "application/xml, text/xml, */*" } });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const text = await res.text();
  return parseKiprisXml(text);
}

// ─── XML 파싱 ─────────────────────────────────────────────────────────────
function getText(el, tag) {
  return el.getElementsByTagName(tag)?.[0]?.textContent?.trim() || "";
}

function parseKiprisXml(xmlText) {
  const parser = new DOMParser();
  const doc    = parser.parseFromString(xmlText, "text/xml");

  // 오류 확인
  const errCode = getText(doc, "successYN");
  if (errCode === "N") {
    const msg = getText(doc, "resultMsg") || "KIPRIS 오류";
    throw new Error(msg);
  }

  const totalCnt = parseInt(getText(doc, "totalCount") || "0");
  const items    = Array.from(doc.getElementsByTagName("item"));

  const patents = items.map(item => ({
    applicationNumber: getText(item, "applicationNumber"),
    inventionTitle:    getText(item, "inventionTitle"),
    applicantName:     getText(item, "applicantName"),
    applicationDate:   getText(item, "applicationDate"),
    registerStatus:    getText(item, "registerStatus"),
    ipcNumber:         getText(item, "ipcNumber"),
    openNumber:        getText(item, "openNumber"),
    openDate:          getText(item, "openDate"),
  }));

  return { totalCount: totalCnt, patents };
}

// ─── IPC 코드 → 기술분야 라벨 ────────────────────────────────────────────
export const IPC_PRESETS = [
  { label: "농업·식품",     code: "A01",  icon: "🌾" },
  { label: "바이오·의약",   code: "A61",  icon: "🧬" },
  { label: "IT·통신",       code: "H04",  icon: "📡" },
  { label: "반도체",         code: "H01L", icon: "💾" },
  { label: "배터리·에너지", code: "H01M", icon: "🔋" },
  { label: "로봇·자동화",   code: "B25J", icon: "🤖" },
  { label: "소재·나노",     code: "B82",  icon: "⚗️" },
  { label: "환경·정화",     code: "B09",  icon: "♻️" },
];

// 등록상태 라벨
export function statusLabel(status) {
  const map = {
    "등록": { text: "등록", color: "#4ade80" },
    "공개": { text: "공개", color: "#60a5fa" },
    "출원": { text: "출원", color: "#f59e0b" },
    "소멸": { text: "소멸", color: "#94a3b8" },
    "거절": { text: "거절", color: "#f87171" },
  };
  return map[status] || { text: status || "-", color: "#475569" };
}
