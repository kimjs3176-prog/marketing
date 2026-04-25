import { useState } from "react";
import { kiprisSearchByApplicant, kiprisSearchByKeyword, kiprisSearchByIpc, IPC_PRESETS, statusLabel } from "../api/kipris.js";

const C = {
  bg:     "#060d18",
  panel:  "#080f1e",
  card:   "#0b1526",
  border: "#1e293b",
  accent: "#a78bfa",
  dim:    "#334155",
  text:   "#e2e8f0",
  muted:  "#64748b",
};

function PatentRow({ p, idx }) {
  const st = statusLabel(p.registerStatus);
  const date = p.applicationDate?.replace(/(\d{4})(\d{2})(\d{2})/, "$1.$2.$3") || "-";
  return (
    <div style={{ background: idx % 2 === 0 ? "transparent" : "#07101a",
      borderBottom:`0.5px solid ${C.border}`, padding:"7px 12px", display:"flex", gap:8, alignItems:"flex-start" }}>
      <div style={{ flex:1, minWidth:0 }}>
        <div style={{ fontSize:12, color:C.text, fontWeight:500, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
          {p.inventionTitle || "-"}
        </div>
        <div style={{ fontSize:10, color:C.muted, marginTop:2, display:"flex", gap:8 }}>
          <span>{p.applicationNumber}</span>
          <span>출원 {date}</span>
          {p.ipcNumber && <span>IPC: {p.ipcNumber.split(",")[0]}</span>}
        </div>
      </div>
      <span style={{ fontSize:9, padding:"2px 6px", borderRadius:3, flexShrink:0,
        background:`${st.color}22`, color:st.color, border:`0.5px solid ${st.color}44` }}>
        {st.text}
      </span>
    </div>
  );
}

export default function KiprisPanel({ apiKey, onEnrichCompany }) {
  const [mode,    setMode]    = useState("applicant"); // applicant|keyword|ipc
  const [query,   setQuery]   = useState("");
  const [ipcCode, setIpcCode] = useState("");
  const [phase,   setPhase]   = useState("idle"); // idle|loading|done|error
  const [result,  setResult]  = useState(null);
  const [err,     setErr]     = useState("");
  const [page,    setPage]    = useState(1);
  const PAGE_SIZE = 10;

  const doSearch = async (pageNo = 1) => {
    if (!apiKey) { setErr("KIPRIS API 키를 설정 탭에서 입력해주세요."); setPhase("error"); return; }
    const needsQuery = mode !== "ipc";
    if (needsQuery && !query.trim()) return;
    if (mode === "ipc" && !ipcCode) return;
    setPhase("loading"); setResult(null); setErr(""); setPage(pageNo);
    try {
      let res;
      const start = (pageNo - 1) * PAGE_SIZE + 1;
      if (mode === "applicant") {
        res = await kiprisSearchByApplicant({ apiKey, applicantName: query.trim(), docsStart: start, docsCount: PAGE_SIZE });
      } else if (mode === "keyword") {
        res = await kiprisSearchByKeyword({ apiKey, keyword: query.trim(), docsStart: start, docsCount: PAGE_SIZE });
      } else {
        res = await kiprisSearchByIpc({ apiKey, ipcCode, docsStart: start, docsCount: PAGE_SIZE });
      }
      setResult(res);
      setPhase("done");
    } catch (e) { setErr(e.message || "KIPRIS 오류"); setPhase("error"); }
  };

  const totalPages = result ? Math.ceil(result.totalCount / PAGE_SIZE) : 0;

  return (
    <div style={{ background: C.panel, border:"1px solid #2d1a5e", borderRadius:12, padding:"16px 18px" }}>
      {/* HEADER */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
        <span style={{ fontSize:16 }}>⚗️</span>
        <span style={{ fontSize:12, fontWeight:700, color:C.accent, letterSpacing:"0.04em" }}>KIPRIS Plus — 특허정보</span>
        <code style={{ fontSize:9, color:C.dim, marginLeft:"auto" }}>plus.kipris.or.kr</code>
      </div>

      {/* KEY STATUS */}
      {!apiKey && (
        <div style={{ fontSize:11, color:"#f59e0b", background:"#451a0322", border:"1px solid #78350f44", borderRadius:7, padding:"7px 10px", marginBottom:10 }}>
          ⚠️ API 키 미설정 — <b>⚙️ API 설정</b> 탭에서 KIPRIS 키를 입력하세요 (<a href="https://plus.kipris.or.kr" target="_blank" rel="noopener" style={{ color:"#60a5fa" }}>plus.kipris.or.kr</a> 무료 발급, 월 1,000건)
        </div>
      )}

      {/* MODE TOGGLE */}
      <div style={{ display:"flex", gap:4, marginBottom:10, background:C.bg, borderRadius:8, padding:4 }}>
        {[
          { id:"applicant", label:"출원인 검색" },
          { id:"keyword",   label:"키워드 검색" },
          { id:"ipc",       label:"IPC 기술분야" },
        ].map(m => (
          <button key={m.id} onClick={() => { setMode(m.id); setResult(null); setQuery(""); }}
            style={{ flex:1, padding:"6px 0", fontSize:11, fontWeight:600, cursor:"pointer", border:"none", borderRadius:6,
              background: mode === m.id ? "#2d1a5e" : "transparent",
              color:       mode === m.id ? C.accent : C.muted,
              transition:"all .15s" }}>
            {m.label}
          </button>
        ))}
      </div>

      {/* IPC PRESET PILLS */}
      {mode === "ipc" && (
        <div style={{ display:"flex", flexWrap:"wrap", gap:5, marginBottom:10 }}>
          {IPC_PRESETS.map(p => (
            <button key={p.code} onClick={() => { setIpcCode(p.code); }}
              style={{ fontSize:10, padding:"3px 9px", borderRadius:20, cursor:"pointer", border:"none", transition:"all .15s",
                background: ipcCode === p.code ? "#2d1a5e" : C.card,
                color:       ipcCode === p.code ? C.accent : C.muted,
                border:     `0.5px solid ${ipcCode === p.code ? C.accent : C.border}` }}>
              {p.icon} {p.label} <span style={{ opacity:.6 }}>({p.code})</span>
            </button>
          ))}
        </div>
      )}

      {/* SEARCH ROW */}
      <div style={{ display:"flex", gap:8, marginBottom:10 }}>
        {mode !== "ipc" ? (
          <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()}
            placeholder={ mode === "applicant" ? "출원인명 (예: 삼성전자, LG화학)" : "발명 키워드 (예: 스마트팜, 그래핀 배터리)" }
            disabled={!apiKey}
            style={{ flex:1, background:C.bg, border:`1px solid ${C.border}`, color:C.text, borderRadius:8, padding:"7px 12px", fontSize:12, outline:"none" }}/>
        ) : (
          <input value={ipcCode} onChange={e => setIpcCode(e.target.value)}
            placeholder="IPC 코드 직접 입력 (예: A01B, H04L)"
            disabled={!apiKey}
            style={{ flex:1, background:C.bg, border:`1px solid ${C.border}`, color:C.text, borderRadius:8, padding:"7px 12px", fontSize:12, outline:"none", fontFamily:"monospace" }}/>
        )}
        <button onClick={() => doSearch(1)} disabled={!apiKey || phase === "loading"}
          style={{ padding:"7px 18px", fontSize:12, fontWeight:700, border:"none", borderRadius:8,
            cursor: !apiKey || phase === "loading" ? "not-allowed" : "pointer",
            background: !apiKey || phase === "loading" ? "#1e293b" : `linear-gradient(135deg, #5b21b6, ${C.accent})`,
            color: !apiKey || phase === "loading" ? C.dim : "#fff" }}>
          {phase === "loading" ? "검색 중…" : "검색"}
        </button>
      </div>

      {/* LOADING */}
      {phase === "loading" && (
        <div style={{ display:"flex", alignItems:"center", gap:6, padding:"10px 0", fontSize:11, color:C.accent }}>
          <span style={{ animation:"spin 1s linear infinite", display:"inline-block" }}>⟳</span> KIPRIS API 요청 중…
        </div>
      )}

      {/* ERROR */}
      {phase === "error" && (
        <div style={{ background:"#1c0b0b", border:"1px solid #7f1d1d44", borderRadius:8, padding:"10px 12px" }}>
          <div style={{ fontSize:12, color:"#f87171" }}>⚠️ {err}</div>
        </div>
      )}

      {/* RESULTS */}
      {phase === "done" && result && (
        <>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", margin:"4px 0 8px" }}>
            <span style={{ fontSize:11, color:C.muted }}>
              총 <b style={{ color:C.accent }}>{result.totalCount.toLocaleString()}</b>건 · {page}페이지 / {totalPages}페이지
              {mode === "applicant" && result.totalCount > 0 && (
                <span style={{ marginLeft:10, fontSize:10, color:"#fbbf24" }}>
                  → 특허 보유 <b>{result.totalCount}</b>건
                </span>
              )}
            </span>
            {mode === "applicant" && result.totalCount > 0 && onEnrichCompany && (
              <button onClick={() => onEnrichCompany({ name: query, patentCount: result.totalCount })}
                style={{ fontSize:10, padding:"3px 10px", background:"#2d1a5e", border:`0.5px solid ${C.accent}`, borderRadius:6, color:C.accent, cursor:"pointer" }}>
                기업 카드에 특허 수 반영
              </button>
            )}
          </div>

          {result.patents.length === 0 ? (
            <div style={{ padding:"12px 0", fontSize:12, color:C.dim, textAlign:"center" }}>검색 결과가 없습니다.</div>
          ) : (
            <div style={{ border:`0.5px solid ${C.border}`, borderRadius:8, overflow:"hidden", maxHeight:360, overflowY:"auto" }}>
              {result.patents.map((p, i) => <PatentRow key={p.applicationNumber || i} p={p} idx={i}/>)}
            </div>
          )}

          {/* PAGINATION */}
          {totalPages > 1 && (
            <div style={{ display:"flex", justifyContent:"center", gap:6, marginTop:10 }}>
              <button onClick={() => doSearch(page - 1)} disabled={page <= 1}
                style={{ padding:"4px 10px", fontSize:11, background:C.card, border:`0.5px solid ${C.border}`, borderRadius:6, color:C.muted, cursor:page<=1?"not-allowed":"pointer" }}>
                ← 이전
              </button>
              <span style={{ fontSize:11, color:C.muted, padding:"4px 8px" }}>{page} / {totalPages}</span>
              <button onClick={() => doSearch(page + 1)} disabled={page >= totalPages}
                style={{ padding:"4px 10px", fontSize:11, background:C.card, border:`0.5px solid ${C.border}`, borderRadius:6, color:C.muted, cursor:page>=totalPages?"not-allowed":"pointer" }}>
                다음 →
              </button>
            </div>
          )}
        </>
      )}
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
