// ─── CORS proxy (개발/프리뷰 환경) ──────────────────────────────────────
// 운영 환경에서는 /api/* Vercel Serverless Function 또는 Flask 프록시 사용 권장
export const PROXY = "https://corsproxy.io/?";

export function proxied(url) {
  return `${PROXY}${encodeURIComponent(url)}`;
}

export function buildQS(obj) {
  return Object.entries(obj)
    .filter(([, v]) => v != null && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");
}

// ─── API Key storage ─────────────────────────────────────────────────────
const LS_KEY = "bizradar_api_keys";

export function loadKeys() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || "{}");
  } catch {
    return {};
  }
}

export function saveKeys(keys) {
  localStorage.setItem(LS_KEY, JSON.stringify(keys));
}

// ─── Default (pre-filled) keys ───────────────────────────────────────────
export const DEFAULT_KEYS = {
  fsc:    "56e0be3845e195ff1e1856d46a6199a4c48e3fb5459bd8380c510534d8cc9041",
  dart:   "",   // opendart.fss.or.kr 에서 발급
  kipris: "",   // plus.kipris.or.kr 에서 발급
};
