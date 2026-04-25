import { useState, useCallback } from "react";
import { loadKeys, saveKeys, DEFAULT_KEYS } from "./api/config.js";
import { searchAllApis, mergeProfile }       from "./api/search.js";
import { analyzeProfile }                    from "./api/ai.js";
import SettingsPanel                         from "./components/SettingsPanel.jsx";
import ProfileCard                           from "./components/ProfileCard.jsx";

const C = { bg:"#060d18", panel:"#090f1d", card:"#0b1526", border:"#1a2744", text:"#e2e8f0", muted:"#64748b", dim:"#334155" };

// ─── API 진행상태 인디케이터 ───────────────────────────────────────────────
function ApiStatus({ label, icon, color, state }) {
  const cfg = {
    idle:    { text:C.dim,    bg:"#1a2744",        dot:"#334155",  msg:"대기" },
    loading: { text:color,    bg:`${color}18`,      dot:color,      msg:"조회 중…" },
    done:    { text:color,    bg:`${color}18`,      dot:color,      msg:"완료" },
    empty:   { text:"#64748b",bg:"#1e293b",         dot:"#475569",  msg:"데이터 없음" },
    error:   { text:"#f87171",bg:"#1c0b0b",         dot:"#f87171",  msg:"오류" },
    nokey:   { text:"#f59e0b",bg:"#451a0322",       dot:"#f59e0b",  msg:"키 미설정" },
  };
  const s = cfg[state] || cfg.idle;
  return (
    <div style={{ display:"flex", alignItems:"center", gap:8, padding:"7px 12px", borderRadius:8, background:s.bg, border:`0.5px solid ${s.dot}33`, flex:1 }}>
      <div style={{ width:7, height:7, borderRadius:"50%", background:s.dot,
        boxShadow: state==="loading" ? `0 0 8px ${s.dot}` : "none",
        animation: state==="loading" ? "pulse 1s ease-in-out infinite" : "none" }}/>
      <span style={{ fontSize:13 }}>{icon}</span>
      <span style={{ fontSize:11, fontWeight:600, color:s.text }}>{label}</span>
      <span style={{ fontSize:10, color:C.muted, marginLeft:"auto" }}>{s.msg}</span>
    </div>
  );
}

// ─── 최근 검색 히스토리 칩 ────────────────────────────────────────────────
function HistoryChip({ name, onClick }) {
  return (
    <button onClick={onClick}
      style={{ fontSize:11, padding:"4px 12px", borderRadius:20, cursor:"pointer", border:`0.5px solid #1a2744`, transition:"all .15s",
        background:"#0d1b2e", color:C.muted }}
      onMouseEnter={e=>{e.currentTarget.style.background="#1e3a5f";e.currentTarget.style.color=C.text;}}
      onMouseLeave={e=>{e.currentTarget.style.background="#0d1b2e";e.currentTarget.style.color=C.muted;}}>
      {name}
    </button>
  );
}

// ─── 저장 목록 테이블 ─────────────────────────────────────────────────────
function ProspectsTable({ profiles }) {
  if (!profiles.length) return (
    <div style={{ textAlign:"center", padding:"60px 0", color:C.dim }}>
      <div style={{ fontSize:36, marginBottom:10 }}>⭐</div>
      <div>검색된 기업 카드에서 ☆ 버튼으로 저장하세요</div>
    </div>
  );

  const gradeColor = g => ({ S:"#FFD700", A:"#4ADE80", B:"#60A5FA", C:"#94A3B8" }[g] || "#94A3B8");

  return (
    <div style={{ background:C.card, borderRadius:12, border:`0.5px solid ${C.border}`, overflowX:"auto" }}>
      <table style={{ width:"100%", borderCollapse:"collapse", fontSize:11 }}>
        <thead>
          <tr style={{ background:C.bg }}>
            {["기업명","업종","지역","규모","매출","성장률","영업이익","특허","공시","AI점수"].map(h=>(
              <th key={h} style={{ padding:"9px 12px", textAlign:"left", color:C.dim, fontWeight:600, borderBottom:`0.5px solid ${C.border}`, whiteSpace:"nowrap" }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {profiles.map((p,i)=>(
            <tr key={p.name+i} style={{ borderBottom:`0.5px solid #0f172a`, background:i%2===0?"transparent":"#07101a" }}>
              <td style={{ padding:"8px 12px", color:C.text, fontWeight:600 }}>{p.name}</td>
              <td style={{ padding:"8px 12px", color:C.muted }}>{p.industry}</td>
              <td style={{ padding:"8px 12px", color:C.muted }}>{p.region}</td>
              <td style={{ padding:"8px 12px", color:C.muted }}>{p.size}</td>
              <td style={{ padding:"8px 12px", color:C.text }}>{p.revenueStr}</td>
              <td style={{ padding:"8px 12px", color:p.growth>20?"#4ade80":p.growth>=0?"#a3e635":p.growth!=null?"#f87171":C.dim }}>
                {p.growth!=null?`${p.growth>0?"+":""}${p.growth}%`:"-"}
              </td>
              <td style={{ padding:"8px 12px", color:"#34d399" }}>{p.opProfitStr}</td>
              <td style={{ padding:"8px 12px", color:"#a78bfa" }}>{p.patentTotal>0?`${p.patentTotal}건`:"-"}</td>
              <td style={{ padding:"8px 12px", color:C.muted }}>{p.disclosures.length>0?`${p.disclosures.length}건`:"-"}</td>
              <td style={{ padding:"8px 12px" }}>
                {p.ai ? <b style={{ color:gradeColor(p.ai.grade) }}>{p.ai.grade} {p.ai.score}</b> : <span style={{ color:C.dim }}>-</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────
export default function BizRadar() {
  const [keys,      setKeys]      = useState({ ...DEFAULT_KEYS, ...loadKeys() });
  const [query,     setQuery]     = useState("");
  const [target,    setTarget]    = useState("농업용 AI 데이터 분석 SaaS");
  const [searching, setSearching] = useState(false);
  const [apiStates, setApiStates] = useState({ fsc:"idle", dart:"idle", kipris:"idle" });
  const [results,   setResults]   = useState([]);   // { raw, profile, ai, saved }
  const [history,   setHistory]   = useState([]);
  const [analyzing, setAnalyzing] = useState(new Set());
  const [tab,       setTab]       = useState("search"); // search | prospects | settings

  const updateApiState = useCallback((api, state) => {
    setApiStates(p => ({ ...p, [api]: state }));
  }, []);

  const doSearch = useCallback(async (corpNm) => {
    const name = (corpNm || query).trim();
    if (!name) return;

    // 이미 검색된 기업인지 확인
    if (results.find(r => r.profile.name === name)) return;

    setSearching(true);
    setApiStates({ fsc:"loading", dart:"loading", kipris:"loading" });

    // API 키 미설정 상태 반영
    if (!keys.fsc)    setApiStates(p => ({ ...p, fsc:"nokey" }));
    if (!keys.dart)   setApiStates(p => ({ ...p, dart:"nokey" }));
    if (!keys.kipris) setApiStates(p => ({ ...p, kipris:"nokey" }));

    try {
      const raw = await searchAllApis(name, keys, (api, state) => {
        setApiStates(p => ({ ...p, [api]: state }));
      });
      const profile = mergeProfile(raw);

      setResults(prev => [{ raw, profile, ai:null, saved:false }, ...prev]);
      setHistory(prev => [name, ...prev.filter(h => h !== name)].slice(0, 8));
    } catch (e) {
      console.error(e);
    } finally {
      setSearching(false);
    }
  }, [query, keys, results]);

  const handleAnalyze = useCallback(async (profileName) => {
    setAnalyzing(p => new Set([...p, profileName]));
    const entry = results.find(r => r.profile.name === profileName);
    if (!entry) return;
    const ai = await analyzeProfile(entry.profile, target);
    setResults(p => p.map(r => r.profile.name === profileName ? { ...r, ai } : r));
    setAnalyzing(p => { const s = new Set(p); s.delete(profileName); return s; });
  }, [results, target]);

  const handleSave = useCallback((profileName) => {
    setResults(p => p.map(r => r.profile.name === profileName ? { ...r, saved: !r.saved } : r));
  }, []);

  const handleRemove = useCallback((profileName) => {
    setResults(p => p.filter(r => r.profile.name !== profileName));
  }, []);

  const savedProfiles = results.filter(r => r.saved).map(r => ({ ...r.profile, ai: r.ai }));
  const keyCount      = [keys.fsc, keys.dart, keys.kipris].filter(Boolean).length;

  return (
    <div style={{ fontFamily:"'Noto Sans KR',sans-serif", background:C.bg, minHeight:"100vh", color:C.text }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');
        *{box-sizing:border-box;margin:0;padding:0;}
        select,input{font-family:inherit;}
        ::-webkit-scrollbar{width:4px;height:4px;}
        ::-webkit-scrollbar-track{background:#0f172a;}
        ::-webkit-scrollbar-thumb{background:#334155;border-radius:2px;}
        @keyframes spin{to{transform:rotate(360deg)}}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
      `}</style>

      {/* ── NAV ── */}
      <nav style={{ background:"#050c16", borderBottom:"1px solid #0f2040", position:"sticky", top:0, zIndex:100 }}>
        <div style={{ maxWidth:1200, margin:"0 auto", padding:"0 20px", height:50, display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <div style={{ width:27, height:27, background:"linear-gradient(135deg,#f59e0b,#d97706)", borderRadius:7, display:"flex", alignItems:"center", justifyContent:"center", fontSize:13 }}>🔭</div>
            <span style={{ fontSize:13, fontWeight:900, color:"#f59e0b", letterSpacing:"0.08em", fontFamily:"monospace" }}>BIZRADAR</span>
            <span style={{ fontSize:10, color:C.dim }}>기업발굴 플랫폼</span>
          </div>

          <div style={{ display:"flex", gap:2, marginLeft:"auto" }}>
            {[
              { id:"search",    label:"🔍 기업 검색" },
              { id:"prospects", label:`⭐ 저장${savedProfiles.length>0?` (${savedProfiles.length})`:""}`},
              { id:"settings",  label:`⚙️ API 설정${keyCount<3?` (${keyCount}/3)`:""}`},
            ].map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                style={{ padding:"6px 12px", borderRadius:6, fontSize:11, fontWeight:600, cursor:"pointer", border:"none", transition:"all .15s",
                  background: tab===t.id ? "#0f2040" : "transparent",
                  color:       tab===t.id ? "#60a5fa" : C.dim }}>
                {t.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      <div style={{ maxWidth:1200, margin:"0 auto", padding:"24px 20px" }}>

        {/* ── SEARCH TAB ── */}
        {tab === "search" && (
          <>
            {/* SEARCH BAR */}
            <div style={{ background:"linear-gradient(135deg,#0d1b35,#0a1220)", border:"1px solid #1e4080", borderRadius:14, padding:"18px 20px", marginBottom:16 }}>
              <div style={{ fontSize:11, color:C.dim, fontWeight:600, marginBottom:8, letterSpacing:"0.06em" }}>
                기업명 검색 — 금융위 · DART · KIPRIS 3개 API 동시 조회
              </div>
              <div style={{ display:"flex", gap:10, marginBottom:12 }}>
                <input
                  value={query} onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && doSearch()}
                  placeholder="법인명 입력 (예: 삼성바이오로직스, 카카오페이, LG에너지솔루션)"
                  style={{ flex:1, background:"#060d18", border:"1px solid #1e3a5f", color:C.text, borderRadius:9, padding:"11px 14px", fontSize:14, outline:"none", transition:"border-color .2s" }}
                  onFocus={e=>e.target.style.borderColor="#3b82f6"}
                  onBlur={e=>e.target.style.borderColor="#1e3a5f"}
                />
                <button onClick={() => doSearch()} disabled={searching || !query.trim()}
                  style={{ padding:"11px 28px", background: searching||!query.trim() ? "#1e293b" : "linear-gradient(135deg,#1d4ed8,#3b82f6)",
                    border:"none", borderRadius:9, color: searching||!query.trim() ? C.dim : "#fff",
                    fontSize:13, fontWeight:700, cursor: searching||!query.trim() ? "not-allowed" : "pointer", whiteSpace:"nowrap" }}>
                  {searching ? "조회 중…" : "검색"}
                </button>
              </div>

              {/* 마케팅 타겟 */}
              <div style={{ display:"flex", alignItems:"center", gap:8, padding:"8px 12px", background:"#060d18", borderRadius:8, border:`0.5px solid ${C.border}` }}>
                <span style={{ fontSize:11, color:C.dim, flexShrink:0 }}>🎯 마케팅 대상:</span>
                <input value={target} onChange={e => setTarget(e.target.value)}
                  style={{ flex:1, background:"transparent", border:"none", color:C.muted, fontSize:12, outline:"none" }}
                  placeholder="예: B2B SaaS, 스마트팩토리 솔루션…"/>
              </div>
            </div>

            {/* API STATUS */}
            {(searching || Object.values(apiStates).some(s => s !== "idle")) && (
              <div style={{ display:"flex", gap:8, marginBottom:14, flexWrap:"wrap" }}>
                <ApiStatus label="금융위원회" icon="🏦" color="#60a5fa" state={!keys.fsc?"nokey":apiStates.fsc}/>
                <ApiStatus label="Open DART"  icon="📊" color="#34d399" state={!keys.dart?"nokey":apiStates.dart}/>
                <ApiStatus label="KIPRIS"      icon="⚗️" color="#a78bfa" state={!keys.kipris?"nokey":apiStates.kipris}/>
              </div>
            )}

            {/* RECENT HISTORY */}
            {history.length > 0 && results.length === 0 && (
              <div style={{ marginBottom:16 }}>
                <div style={{ fontSize:11, color:C.dim, marginBottom:6 }}>최근 검색</div>
                <div style={{ display:"flex", gap:6, flexWrap:"wrap" }}>
                  {history.map(h => <HistoryChip key={h} name={h} onClick={() => doSearch(h)}/>)}
                </div>
              </div>
            )}

            {/* EMPTY STATE */}
            {results.length === 0 && !searching && (
              <div style={{ textAlign:"center", padding:"60px 20px" }}>
                <div style={{ fontSize:48, marginBottom:14 }}>🔭</div>
                <h3 style={{ fontSize:16, fontWeight:700, color:C.muted, marginBottom:8 }}>기업명을 검색하면 통합 프로필이 생성됩니다</h3>
                <p style={{ fontSize:12, color:C.dim, lineHeight:1.7, maxWidth:420, margin:"0 auto 20px" }}>
                  금융위원회(기업기본정보) + Open DART(재무·공시) + KIPRIS(특허)를<br/>
                  동시에 조회하여 하나의 마케팅 인텔리전스 카드로 제공합니다.
                </p>
                <div style={{ display:"flex", gap:8, justifyContent:"center", flexWrap:"wrap" }}>
                  {["삼성전자","LG화학","현대자동차","카카오","셀트리온"].map(n=>(
                    <HistoryChip key={n} name={n} onClick={()=>{ setQuery(n); doSearch(n); }}/>
                  ))}
                </div>
                {keyCount < 3 && (
                  <div style={{ marginTop:20, padding:"10px 16px", background:"#451a0322", border:"1px solid #78350f44", borderRadius:8, display:"inline-block" }}>
                    <span style={{ fontSize:11, color:"#f59e0b" }}>⚠️ API 키 {keyCount}/3 설정됨 — </span>
                    <button onClick={() => setTab("settings")}
                      style={{ fontSize:11, color:"#60a5fa", background:"none", border:"none", cursor:"pointer", textDecoration:"underline" }}>
                      API 설정에서 키를 입력하면 더 많은 데이터를 조회할 수 있습니다
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* SEARCH LOADING SKELETON */}
            {searching && results.length === 0 && (
              <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(340px,1fr))", gap:14 }}>
                {[1].map(i=>(
                  <div key={i} style={{ background:C.panel, borderRadius:14, border:`1px solid ${C.border}`, padding:18, height:320 }}>
                    {[100,60,80,40,100].map((w,j)=>(
                      <div key={j} style={{ height:12, borderRadius:6, background:"#1e293b", width:`${w}%`, marginBottom:10,
                        animation:"pulse 1.5s ease-in-out infinite" }}/>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {/* RESULTS GRID */}
            {results.length > 0 && (
              <>
                <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:10 }}>
                  <span style={{ fontSize:11, color:C.dim }}>{results.length}개 기업 조회됨</span>
                  <button onClick={() => setResults([])}
                    style={{ fontSize:10, padding:"3px 10px", background:C.card, border:`0.5px solid ${C.border}`, borderRadius:6, color:C.muted, cursor:"pointer" }}>
                    전체 초기화
                  </button>
                </div>
                <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(340px,1fr))", gap:14 }}>
                  {results.map(r => (
                    <div key={r.profile.name} style={{ position:"relative" }}>
                      <ProfileCard
                        profile={r.profile}
                        ai={r.ai}
                        analyzing={analyzing.has(r.profile.name)}
                        onAnalyze={() => handleAnalyze(r.profile.name)}
                        onSave={() => handleSave(r.profile.name)}
                        saved={r.saved}
                        targetProduct={target}
                      />
                      {/* 제거 버튼 */}
                      <button onClick={() => handleRemove(r.profile.name)}
                        style={{ position:"absolute", top:8, right:8, width:22, height:22, borderRadius:"50%",
                          background:"#1e293b", border:`0.5px solid ${C.border}`, color:C.muted, cursor:"pointer",
                          fontSize:12, display:"flex", alignItems:"center", justifyContent:"center" }}>
                        ×
                      </button>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}

        {/* ── PROSPECTS TAB ── */}
        {tab === "prospects" && (
          <div>
            <h2 style={{ fontSize:14, fontWeight:700, color:"#f59e0b", marginBottom:14 }}>⭐ 저장된 잠재 고객 — {savedProfiles.length}개</h2>
            <ProspectsTable profiles={savedProfiles}/>
          </div>
        )}

        {/* ── SETTINGS TAB ── */}
        {tab === "settings" && (
          <SettingsPanel keys={keys} onSave={k => { setKeys(k); saveKeys(k); }}/>
        )}
      </div>
    </div>
  );
}
