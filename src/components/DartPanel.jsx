import { useState } from "react";
import { dartSearchCorp, dartGetCompany, dartGetFinancials, dartGetDisclosures, parseFinancials, disclosureLabel } from "../api/dart.js";

const C = {
  bg:     "#060d18",
  panel:  "#080f1e",
  card:   "#0b1526",
  border: "#1e293b",
  accent: "#34d399",
  dim:    "#334155",
  text:   "#e2e8f0",
  muted:  "#64748b",
};

function Row({ label, value, highlight = false }) {
  return (
    <div style={{ display:"flex", justifyContent:"space-between", padding:"4px 0", borderBottom:`0.5px solid ${C.border}` }}>
      <span style={{ fontSize:11, color:C.muted }}>{label}</span>
      <span style={{ fontSize:11, color: highlight ? C.accent : C.text, fontWeight: highlight ? 600 : 400 }}>{value || "-"}</span>
    </div>
  );
}

function DisclosurePill({ d }) {
  const { label, color } = disclosureLabel(d.report_nm);
  const date = d.rcept_dt ? `${d.rcept_dt.slice(0,4)}.${d.rcept_dt.slice(4,6)}.${d.rcept_dt.slice(6)}` : "";
  return (
    <div style={{ background:C.card, border:`0.5px solid ${C.border}`, borderRadius:7, padding:"7px 10px", marginBottom:5 }}>
      <div style={{ display:"flex", alignItems:"center", gap:6 }}>
        <span style={{ fontSize:9, padding:"1px 6px", borderRadius:3, background:`${color}22`, color, border:`0.5px solid ${color}44` }}>{label}</span>
        <span style={{ fontSize:11, color:C.text, flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{d.report_nm}</span>
        <span style={{ fontSize:10, color:C.muted, flexShrink:0 }}>{date}</span>
      </div>
      <div style={{ fontSize:10, color:C.muted, marginTop:2 }}>{d.corp_nm} · {d.flr_nm}</div>
    </div>
  );
}

export default function DartPanel({ apiKey, onAddCompanies }) {
  const [query,    setQuery]   = useState("");
  const [phase,    setPhase]   = useState("idle"); // idle|searching|detail|error
  const [corps,    setCorps]   = useState([]);      // corp list from search
  const [selected, setSelected]= useState(null);    // chosen corp
  const [detail,   setDetail]  = useState(null);    // company + financials + disclosures
  const [err,      setErr]     = useState("");
  const [year,     setYear]    = useState(new Date().getFullYear() - 1);

  const thisYear = new Date().getFullYear();

  const doSearch = async () => {
    if (!apiKey) { setErr("Open DART API 키를 설정 탭에서 입력해주세요."); setPhase("error"); return; }
    if (!query.trim()) return;
    setPhase("searching"); setCorps([]); setDetail(null); setErr("");
    try {
      const list = await dartSearchCorp({ apiKey, corpName: query.trim(), pageCount: 15 });
      setCorps(list);
      setPhase("idle");
    } catch (e) { setErr(e.message); setPhase("error"); }
  };

  const doDetail = async (corp) => {
    setSelected(corp);
    setPhase("searching");
    setDetail(null);
    try {
      const [company, finRaw, disclosures] = await Promise.all([
        dartGetCompany({ apiKey, corpCode: corp.corp_code }),
        dartGetFinancials({ apiKey, corpCode: corp.corp_code, year }).catch(() => []),
        dartGetDisclosures({ apiKey, corpCode: corp.corp_code, pageCount: 5 }),
      ]);
      const fin = finRaw.length ? parseFinancials(finRaw) : null;
      setDetail({ company, fin, disclosures });
      setPhase("detail");
    } catch (e) { setErr(e.message); setPhase("error"); }
  };

  const addToList = () => {
    if (!detail) return;
    const c = detail.company;
    const f = detail.fin || {};
    const emp = parseInt(c.emp_no) || 0;
    onAddCompanies([{
      id:        `dart-${c.corp_code}`,
      name:      c.corp_name || query,
      industry:  c.induty_code_name || "기타",
      region:    c.adres ? (["서울","경기","인천","부산","대구","광주","대전","울산","세종","강원","충북","충남","전북","전남","경북","경남","제주"].find(r => c.adres.startsWith(r)) || "기타") : "기타",
      size:      emp > 1000 ? "대기업" : emp > 300 ? "중견기업" : emp > 50 ? "중기업" : emp > 5 ? "소기업" : "스타트업",
      employees: emp,
      founded:   c.est_dt ? parseInt(c.est_dt.slice(0,4)) : null,
      revenue:   f.revenue || "-",
      revenueRaw:f.revenueRaw || 0,
      growth:    f.growth ?? null,
      patent:    null,
      export:    false,
      tech:      [],
      desc:      [c.adres, c.phn_no ? `☎ ${c.phn_no}` : null].filter(Boolean).join(" · "),
      ceo:       c.ceo_nm || "-",
      homepage:  c.hm_url || null,
      crno:      c.jurir_no || null,
      listed:    !!c.stock_code,
      capital:   "-",
      source:    "dart",
      dart:      { opProfit: f.opProfit, netIncome: f.netIncome, corpCode: c.corp_code, year },
      kipris:    null,
    }]);
  };

  return (
    <div style={{ background: C.panel, border:"1px solid #1e4060", borderRadius:12, padding:"16px 18px" }}>
      {/* HEADER */}
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:12 }}>
        <span style={{ fontSize:16 }}>📊</span>
        <span style={{ fontSize:12, fontWeight:700, color:C.accent, letterSpacing:"0.04em" }}>Open DART — 전자공시</span>
        <code style={{ fontSize:9, color:C.dim, marginLeft:"auto" }}>opendart.fss.or.kr</code>
      </div>

      {/* KEY STATUS */}
      {!apiKey && (
        <div style={{ fontSize:11, color:"#f59e0b", background:"#451a0322", border:"1px solid #78350f44", borderRadius:7, padding:"7px 10px", marginBottom:10 }}>
          ⚠️ API 키 미설정 — <b>⚙️ API 설정</b> 탭에서 Open DART 키를 입력하세요 (<a href="https://opendart.fss.or.kr" target="_blank" rel="noopener" style={{ color:"#60a5fa" }}>opendart.fss.or.kr</a> 무료 발급)
        </div>
      )}

      {/* SEARCH ROW */}
      <div style={{ display:"flex", gap:8, marginBottom:10 }}>
        <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === "Enter" && doSearch()}
          placeholder="법인명 검색 (예: 카카오, 셀트리온)" disabled={!apiKey}
          style={{ flex:1, background:C.bg, border:`1px solid ${C.border}`, color:C.text, borderRadius:8, padding:"7px 12px", fontSize:12, outline:"none" }}/>
        <select value={year} onChange={e => setYear(Number(e.target.value))}
          style={{ background:C.bg, border:`1px solid ${C.border}`, color:C.muted, borderRadius:8, padding:"7px 10px", fontSize:12 }}>
          {[thisYear-1, thisYear-2, thisYear-3].map(y => <option key={y} value={y}>{y}년</option>)}
        </select>
        <button onClick={doSearch} disabled={!apiKey || phase==="searching"}
          style={{ padding:"7px 18px", fontSize:12, fontWeight:700, border:"none", borderRadius:8, cursor: !apiKey||phase==="searching"?"not-allowed":"pointer",
            background: !apiKey||phase==="searching" ? "#1e293b" : `linear-gradient(135deg, #059669, ${C.accent})`,
            color: !apiKey||phase==="searching" ? C.dim : "#000" }}>
          {phase==="searching" ? "조회 중…" : "조회"}
        </button>
      </div>

      {/* LOADING */}
      {phase === "searching" && (
        <div style={{ display:"flex", alignItems:"center", gap:6, padding:"10px 0", fontSize:11, color:C.accent }}>
          <span style={{ animation:"spin 1s linear infinite", display:"inline-block" }}>⟳</span> DART API 요청 중…
        </div>
      )}

      {/* ERROR */}
      {phase === "error" && (
        <div style={{ background:"#1c0b0b", border:"1px solid #7f1d1d44", borderRadius:8, padding:"10px 12px", marginTop:4 }}>
          <div style={{ fontSize:12, color:"#f87171" }}>⚠️ {err}</div>
        </div>
      )}

      {/* CORP LIST */}
      {corps.length > 0 && phase !== "detail" && (
        <div>
          <div style={{ fontSize:11, color:C.muted, marginBottom:6 }}>{corps.length}개 기업 검색됨 — 클릭하면 재무정보를 조회합니다</div>
          <div style={{ maxHeight:240, overflowY:"auto", border:`0.5px solid ${C.border}`, borderRadius:8 }}>
            {corps.map((c, i) => (
              <div key={c.corp_code} onClick={() => doDetail(c)} style={{
                display:"flex", justifyContent:"space-between", alignItems:"center",
                padding:"8px 12px", borderBottom:`0.5px solid ${C.border}`,
                background: i % 2 === 0 ? "transparent" : "#07101a",
                cursor:"pointer", transition:"background .1s",
              }}
                onMouseEnter={e => e.currentTarget.style.background = "#0d2a4a"}
                onMouseLeave={e => e.currentTarget.style.background = i % 2 === 0 ? "transparent" : "#07101a"}>
                <span style={{ fontSize:12, color:C.text, fontWeight:500 }}>{c.corp_name}</span>
                <div style={{ display:"flex", gap:6, alignItems:"center" }}>
                  {c.stock_code && <span style={{ fontSize:9, padding:"2px 5px", borderRadius:3, background:"#0d2a4a", color:"#60a5fa" }}>상장 {c.stock_code}</span>}
                  <span style={{ fontSize:11, color:C.muted }}>{c.corp_code}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DETAIL */}
      {phase === "detail" && detail && (
        <div>
          <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
            <button onClick={() => { setPhase("idle"); setDetail(null); }}
              style={{ fontSize:11, color:C.accent, background:"transparent", border:`0.5px solid #059669`, borderRadius:6, padding:"3px 10px", cursor:"pointer" }}>
              ← 목록
            </button>
            <span style={{ fontSize:13, fontWeight:700, color:C.text }}>{detail.company.corp_name}</span>
            <button onClick={addToList}
              style={{ marginLeft:"auto", fontSize:11, fontWeight:700, padding:"5px 14px", background:`linear-gradient(135deg,#059669,${C.accent})`,
                border:"none", borderRadius:7, color:"#000", cursor:"pointer" }}>
              + 발굴 목록에 추가
            </button>
          </div>

          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:12 }}>
            {/* 기업개황 */}
            <div style={{ background:C.card, border:`0.5px solid ${C.border}`, borderRadius:8, padding:"10px 12px" }}>
              <div style={{ fontSize:11, fontWeight:600, color:C.muted, marginBottom:6 }}>🏢 기업개황</div>
              <Row label="대표이사" value={detail.company.ceo_nm}/>
              <Row label="설립일"   value={detail.company.est_dt?.replace(/(\d{4})(\d{2})(\d{2})/, "$1-$2-$3")}/>
              <Row label="업종"     value={detail.company.induty_code_name}/>
              <Row label="임직원"   value={detail.company.emp_no ? `${detail.company.emp_no}명` : "-"}/>
              <Row label="자본금"   value={detail.company.capital_amount ? `${Math.round(parseInt(detail.company.capital_amount.replace(/,/g,""))/1e8)}억` : "-"}/>
              {detail.company.hm_url && (
                <a href={`https://${detail.company.hm_url.replace(/^https?:\/\//,"")}`} target="_blank" rel="noopener"
                  style={{ fontSize:10, color:"#3b82f6", display:"block", marginTop:5 }}>🔗 {detail.company.hm_url}</a>
              )}
            </div>

            {/* 재무정보 */}
            <div style={{ background:C.card, border:`0.5px solid ${C.border}`, borderRadius:8, padding:"10px 12px" }}>
              <div style={{ fontSize:11, fontWeight:600, color:C.muted, marginBottom:6 }}>💰 {year}년 재무정보 (연결)</div>
              {detail.fin ? (
                <>
                  <Row label="매출액"     value={detail.fin.revenue}   highlight={true}/>
                  <Row label="전년比 성장" value={detail.fin.growth != null ? `${detail.fin.growth > 0 ? "+" : ""}${detail.fin.growth}%` : "-"} highlight={detail.fin.growth > 20}/>
                  <Row label="영업이익"   value={detail.fin.opProfit}/>
                  <Row label="당기순이익" value={detail.fin.netIncome}/>
                </>
              ) : (
                <div style={{ fontSize:11, color:C.dim, padding:"8px 0" }}>재무정보 없음 (비상장·미공시)</div>
              )}
            </div>
          </div>

          {/* 최근 공시 */}
          {detail.disclosures.length > 0 && (
            <div>
              <div style={{ fontSize:11, fontWeight:600, color:C.muted, marginBottom:6 }}>📋 최근 공시</div>
              {detail.disclosures.map((d, i) => <DisclosurePill key={i} d={d}/>)}
            </div>
          )}
        </div>
      )}

      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
