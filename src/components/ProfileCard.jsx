import { useState } from "react";

const C = {
  bg:     "#060d18",
  panel:  "#090f1d",
  card:   "#0b1526",
  card2:  "#0d1b2e",
  border: "#1a2744",
  border2:"#1e3a5f",
  text:   "#e2e8f0",
  muted:  "#64748b",
  dim:    "#334155",
};

const gradeColor = g => ({ S:"#FFD700", A:"#4ADE80", B:"#60A5FA", C:"#94A3B8" }[g] || "#94A3B8");
const fmt = n => !n||n===0 ? "-" : n>=1e12?`${(n/1e12).toFixed(1)}조`:n>=1e8?`${Math.round(n/1e8)}억`:`${Math.round(n/1e6)}백만`;

// ─── 데이터 소스 뱃지 ─────────────────────────────────────────────────────
function SourcePill({ label, active, color }) {
  return (
    <span style={{
      fontSize:9, padding:"2px 7px", borderRadius:20, fontWeight:700, letterSpacing:"0.04em",
      background: active ? `${color}18` : "#1a2744",
      color:      active ? color         : C.dim,
      border:     `1px solid ${active ? color + "55" : "#1e293b"}`,
    }}>
      {active ? "✓" : "✕"} {label}
    </span>
  );
}

// ─── 섹션 헤더 ────────────────────────────────────────────────────────────
function SectionHead({ icon, label, color, extra }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:8 }}>
      <span style={{ fontSize:12 }}>{icon}</span>
      <span style={{ fontSize:11, fontWeight:700, color: color || C.muted, letterSpacing:"0.04em" }}>{label}</span>
      {extra && <span style={{ marginLeft:"auto", fontSize:10, color:C.dim }}>{extra}</span>}
    </div>
  );
}

// ─── 스탯 타일 ────────────────────────────────────────────────────────────
function StatTile({ label, value, sub, color, span = 1 }) {
  return (
    <div style={{
      background: C.card, borderRadius:8, padding:"10px 12px",
      border:`0.5px solid ${C.border}`, gridColumn:`span ${span}`,
    }}>
      <div style={{ fontSize:13, fontWeight:700, color: color || C.text, marginBottom:2 }}>{value || "-"}</div>
      <div style={{ fontSize:10, color:C.muted }}>{label}</div>
      {sub && <div style={{ fontSize:10, color:C.dim, marginTop:1 }}>{sub}</div>}
    </div>
  );
}

// ─── AI 점수 링 ───────────────────────────────────────────────────────────
function GradeRing({ score, grade }) {
  const c    = gradeColor(grade);
  const r    = 34;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  return (
    <div style={{ position:"relative", width:80, height:80, display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
      <svg style={{ position:"absolute", inset:0, transform:"rotate(-90deg)" }} width="80" height="80">
        <circle cx="40" cy="40" r={r} fill="none" stroke="#1e293b" strokeWidth="5"/>
        <circle cx="40" cy="40" r={r} fill="none" stroke={c} strokeWidth="5"
          strokeDasharray={`${dash} ${circ}`} strokeLinecap="round"
          style={{ transition:"stroke-dasharray 1.2s cubic-bezier(.4,0,.2,1)" }}/>
      </svg>
      <div style={{ textAlign:"center" }}>
        <div style={{ fontSize:22, fontWeight:900, color:c, lineHeight:1 }}>{grade}</div>
        <div style={{ fontSize:11, color:C.muted, marginTop:1 }}>{score}점</div>
      </div>
    </div>
  );
}

// ─── 공시 타입 파싱 ────────────────────────────────────────────────────────
function disclosureType(title) {
  if (title.includes("사업보고서"))  return { label:"사업보고서", color:"#60a5fa" };
  if (title.includes("분기보고서"))  return { label:"분기보고서", color:"#818cf8" };
  if (title.includes("반기보고서"))  return { label:"반기보고서", color:"#a78bfa" };
  if (title.includes("증자"))        return { label:"유상증자",   color:"#4ade80" };
  if (title.includes("합병")||title.includes("인수")) return { label:"M&A", color:"#f59e0b" };
  if (title.includes("임원"))        return { label:"임원변동",   color:"#94a3b8" };
  return { label:"공시", color:"#475569" };
}

// ─── 특허 상태 ─────────────────────────────────────────────────────────────
function patentStatus(s) {
  return { "등록":["#4ade80","#052e16"], "출원":["#f59e0b","#451a03"], "공개":["#60a5fa","#0d2a4a"], "소멸":["#94a3b8","#1e293b"] }[s] || ["#475569","#1e293b"];
}

// ─── GROWTH BADGE ──────────────────────────────────────────────────────────
function GrowthBadge({ growth }) {
  if (growth == null) return <span style={{ fontSize:11, color:C.dim }}>-</span>;
  const pos = growth >= 0;
  return (
    <span style={{ fontSize:12, fontWeight:700, color: growth > 20 ? "#4ade80" : growth >= 0 ? "#a3e635" : "#f87171" }}>
      {pos ? "▲" : "▼"} {Math.abs(growth)}%
    </span>
  );
}

// ─── MAIN PROFILE CARD ─────────────────────────────────────────────────────
export default function ProfileCard({ profile, ai, analyzing, onAnalyze, onSave, saved, targetProduct }) {
  const [tab, setTab] = useState("overview"); // overview | financial | patent | disclosure | ai

  const TABS = [
    { id:"overview",    label:"개요" },
    { id:"financial",   label:"재무", disabled:!profile.sources.dart },
    { id:"patent",      label:`특허${profile.patentTotal>0?` (${profile.patentTotal})`:""}`, disabled:!profile.sources.kipris },
    { id:"disclosure",  label:`공시${profile.disclosures.length>0?` (${profile.disclosures.length})`:""}`, disabled:!profile.sources.dart },
    { id:"ai",          label:"AI 분석", accent:true },
  ];

  return (
    <div style={{
      background: C.panel, borderRadius:14, overflow:"hidden",
      border: saved ? "1px solid #78350f88" : `1px solid ${C.border2}`,
      boxShadow:"0 4px 24px #00000055",
    }}>
      {/* ── TOP HEADER ── */}
      <div style={{ background:`linear-gradient(135deg, #0d1b35, #0a1220)`, padding:"16px 18px", borderBottom:`1px solid ${C.border}` }}>
        <div style={{ display:"flex", gap:12, alignItems:"flex-start" }}>
          {/* Logo placeholder */}
          <div style={{ width:44, height:44, borderRadius:10, background:"linear-gradient(135deg,#1e3a5f,#2563eb22)", border:`1px solid ${C.border2}`,
            display:"flex", alignItems:"center", justifyContent:"center", fontSize:18, flexShrink:0 }}>
            🏢
          </div>
          <div style={{ flex:1, minWidth:0 }}>
            <div style={{ display:"flex", alignItems:"center", gap:6, flexWrap:"wrap", marginBottom:4 }}>
              <h2 style={{ fontSize:16, fontWeight:900, color:C.text, margin:0 }}>{profile.name}</h2>
              {profile.listed && (
                <span style={{ fontSize:9, padding:"2px 7px", borderRadius:3, background:"#0d2a4a", color:"#60a5fa", border:"1px solid #1e40af44", fontWeight:700 }}>
                  {profile.stockCode ? `KOSPI ${profile.stockCode}` : "상장"}
                </span>
              )}
            </div>
            <div style={{ fontSize:12, color:C.muted, marginBottom:6 }}>
              {[profile.industry, profile.region, profile.size].filter(d=>d&&d!=="-").join(" · ")}
            </div>
            {/* Source pills */}
            <div style={{ display:"flex", gap:5, flexWrap:"wrap" }}>
              <SourcePill label="금융위" active={profile.sources.fsc}    color="#60a5fa"/>
              <SourcePill label="DART"   active={profile.sources.dart}   color="#34d399"/>
              <SourcePill label="KIPRIS" active={profile.sources.kipris} color="#a78bfa"/>
            </div>
          </div>
          {/* AI Grade */}
          {ai && <GradeRing score={ai.score} grade={ai.grade}/>}
        </div>

        {/* AI HEADLINE */}
        {ai?.headline && (
          <div style={{ marginTop:12, padding:"8px 12px", background:"#fbbf2412", border:"1px solid #78350f44", borderRadius:8 }}>
            <span style={{ fontSize:12, color:"#fbbf24", fontWeight:600 }}>💡 {ai.headline}</span>
          </div>
        )}
      </div>

      {/* ── QUICK STATS ROW ── */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:1, background:C.border, borderBottom:`1px solid ${C.border}` }}>
        {[
          { label:"매출액",  value:profile.revenueStr,    color: profile.revenue > 1e11 ? "#4ade80" : C.text },
          { label:"성장률",  value:<GrowthBadge growth={profile.growth}/> },
          { label:"임직원",  value:profile.employeesStr },
          { label:"특허",    value:profile.patentTotal > 0 ? `${profile.patentTotal}건` : "-", color:"#a78bfa" },
        ].map((s,i) => (
          <div key={i} style={{ background:C.card, padding:"10px 0", textAlign:"center" }}>
            <div style={{ fontSize:13, fontWeight:700, color: s.color || C.text }}>{s.value}</div>
            <div style={{ fontSize:10, color:C.dim, marginTop:2 }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── TABS ── */}
      <div style={{ display:"flex", gap:0, background:C.bg, borderBottom:`1px solid ${C.border}` }}>
        {TABS.filter(t=>!t.disabled).map(t => (
          <button key={t.id} onClick={()=>setTab(t.id)}
            style={{ flex:1, padding:"9px 4px", fontSize:11, fontWeight:600, cursor:"pointer", border:"none", transition:"all .15s",
              background: tab===t.id ? C.card : "transparent",
              color: tab===t.id ? (t.accent ? "#fbbf24" : "#60a5fa") : C.dim,
              borderBottom: tab===t.id ? `2px solid ${t.accent ? "#fbbf24" : "#2563eb"}` : "2px solid transparent",
            }}>
            {t.label}
          </button>
        ))}
      </div>

      {/* ── TAB CONTENT ── */}
      <div style={{ padding:"14px 16px", minHeight:200 }}>

        {/* OVERVIEW */}
        {tab==="overview" && (
          <div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:6, marginBottom:12 }}>
              {[
                ["대표자",   profile.ceo],
                ["설립일",   profile.estb],
                ["업종",     profile.industry],
                ["자본금",   profile.capitalStr],
                ["법인번호", profile.crno ? profile.crno.slice(0,6)+"****" : "-"],
                ["지역",     profile.region],
              ].map(([l,v])=>(
                <div key={l} style={{ background:C.card2, borderRadius:7, padding:"7px 10px", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                  <span style={{ fontSize:10, color:C.dim }}>{l}</span>
                  <span style={{ fontSize:11, color:C.muted, fontWeight:500 }}>{v||"-"}</span>
                </div>
              ))}
            </div>
            {profile.address && profile.address !== "-" && (
              <div style={{ background:C.card2, borderRadius:7, padding:"7px 10px", marginBottom:8, display:"flex", gap:8 }}>
                <span style={{ fontSize:10, color:C.dim, flexShrink:0 }}>주소</span>
                <span style={{ fontSize:11, color:C.muted }}>{profile.address}</span>
              </div>
            )}
            {profile.homepage && (
              <a href={`https://${profile.homepage.replace(/^https?:\/\//,"")}`} target="_blank" rel="noopener"
                style={{ fontSize:11, color:"#3b82f6", textDecoration:"none", display:"flex", alignItems:"center", gap:4 }}>
                🔗 {profile.homepage}
              </a>
            )}
          </div>
        )}

        {/* FINANCIAL */}
        {tab==="financial" && profile.sources.dart && (
          <div>
            <SectionHead icon="💰" label={`${profile.finYear}년 재무정보 (연결재무제표)`} color="#34d399"/>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:6, marginBottom:12 }}>
              <StatTile label="매출액"     value={profile.revenueStr}    color={profile.revenue>1e11?"#4ade80":C.text}  sub={`전년 ${profile.revenuePrevStr}`}/>
              <StatTile label="전년대비 성장" value={profile.growth!=null?`${profile.growth>0?"+":""}${profile.growth}%`:"-"} color={profile.growth>20?"#4ade80":profile.growth>=0?"#a3e635":"#f87171"}/>
              <StatTile label="영업이익"   value={profile.opProfitStr}/>
              <StatTile label="당기순이익" value={profile.netIncomeStr}/>
            </div>
            {/* 마진율 */}
            {profile.revenue > 0 && profile.opProfit > 0 && (
              <div style={{ background:C.card2, borderRadius:8, padding:"10px 12px" }}>
                <div style={{ fontSize:10, color:C.dim, marginBottom:6 }}>수익성 지표</div>
                <div style={{ display:"flex", gap:12 }}>
                  {[
                    ["영업이익률", `${((profile.opProfit/profile.revenue)*100).toFixed(1)}%`],
                    ["순이익률",   `${((profile.netIncome/profile.revenue)*100).toFixed(1)}%`],
                  ].map(([l,v])=>(
                    <div key={l}>
                      <div style={{ fontSize:13, fontWeight:700, color:"#34d399" }}>{v}</div>
                      <div style={{ fontSize:10, color:C.muted }}>{l}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* PATENT */}
        {tab==="patent" && profile.sources.kipris && (
          <div>
            <SectionHead icon="⚗️" label="특허·실용신안 현황" color="#a78bfa" extra={`총 ${profile.patentTotal}건`}/>
            <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:6, marginBottom:12 }}>
              <StatTile label="전체"   value={`${profile.patentTotal}건`}   color="#a78bfa"/>
              <StatTile label="등록"   value={`${profile.patentRegistered}건`} color="#4ade80"/>
              <StatTile label="출원·심사" value={`${profile.patentPending}건`} color="#f59e0b"/>
            </div>
            {profile.patentTopIpc.length > 0 && (
              <div style={{ marginBottom:10 }}>
                <div style={{ fontSize:10, color:C.dim, marginBottom:4 }}>주요 IPC 기술분야</div>
                <div style={{ display:"flex", gap:5, flexWrap:"wrap" }}>
                  {profile.patentTopIpc.map(ipc=>(
                    <span key={ipc} style={{ fontSize:10, padding:"2px 9px", borderRadius:4, background:"#1a0d3a", color:"#a78bfa", border:"1px solid #5b21b644", fontFamily:"monospace" }}>{ipc}</span>
                  ))}
                </div>
              </div>
            )}
            {profile.patentRecent.length > 0 && (
              <div>
                <div style={{ fontSize:10, color:C.dim, marginBottom:6 }}>최근 출원 목록</div>
                {profile.patentRecent.map((p,i)=>{
                  const [col, bg] = patentStatus(p.status);
                  return (
                    <div key={i} style={{ background:C.card2, borderRadius:7, padding:"8px 10px", marginBottom:5, display:"flex", gap:8, alignItems:"flex-start" }}>
                      <div style={{ flex:1, minWidth:0 }}>
                        <div style={{ fontSize:11, color:C.text, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{p.title||"-"}</div>
                        <div style={{ fontSize:10, color:C.muted, marginTop:2, display:"flex", gap:8 }}>
                          <span>{p.number}</span>
                          <span>{p.date}</span>
                          {p.ipc&&<span style={{ fontFamily:"monospace" }}>{p.ipc}</span>}
                        </div>
                      </div>
                      <span style={{ fontSize:9, padding:"2px 6px", borderRadius:3, flexShrink:0, background:bg, color:col, border:`1px solid ${col}44` }}>{p.status||"-"}</span>
                    </div>
                  );
                })}
              </div>
            )}
            {profile.patentTotal === 0 && (
              <div style={{ textAlign:"center", padding:"20px 0", color:C.dim, fontSize:12 }}>검색된 특허가 없습니다.</div>
            )}
          </div>
        )}

        {/* DISCLOSURE */}
        {tab==="disclosure" && profile.sources.dart && (
          <div>
            <SectionHead icon="📋" label="최근 전자공시 (DART)" color="#60a5fa"/>
            {profile.disclosures.length === 0 ? (
              <div style={{ textAlign:"center", padding:"20px 0", color:C.dim, fontSize:12 }}>최근 공시가 없습니다.</div>
            ) : (
              profile.disclosures.map((d,i)=>{
                const { label, color } = disclosureType(d.title);
                return (
                  <a key={i} href={d.url} target="_blank" rel="noopener" style={{ textDecoration:"none" }}>
                    <div style={{ background:C.card2, borderRadius:8, padding:"9px 12px", marginBottom:6, cursor:"pointer",
                      border:`0.5px solid ${C.border}`, transition:"border-color .15s" }}
                      onMouseEnter={e=>e.currentTarget.style.borderColor="#2563eb"}
                      onMouseLeave={e=>e.currentTarget.style.borderColor=C.border}>
                      <div style={{ display:"flex", alignItems:"center", gap:6, marginBottom:3 }}>
                        <span style={{ fontSize:9, padding:"2px 6px", borderRadius:3, background:`${color}22`, color, border:`0.5px solid ${color}44`, flexShrink:0 }}>{label}</span>
                        <span style={{ fontSize:11, color:C.text, flex:1, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{d.title}</span>
                        <span style={{ fontSize:10, color:C.dim, flexShrink:0 }}>{d.date}</span>
                      </div>
                      <div style={{ fontSize:10, color:C.muted }}>{d.corp} · {d.filer} ↗</div>
                    </div>
                  </a>
                );
              })
            )}
          </div>
        )}

        {/* AI ANALYSIS */}
        {tab==="ai" && (
          <div>
            {!ai && !analyzing && (
              <div style={{ textAlign:"center", padding:"24px 0" }}>
                <div style={{ fontSize:36, marginBottom:10 }}>🤖</div>
                <div style={{ fontSize:12, color:C.muted, marginBottom:14 }}>
                  3개 API 데이터를 종합하여 마케팅 인사이트를 생성합니다.
                </div>
                <button onClick={onAnalyze}
                  style={{ padding:"10px 28px", background:"linear-gradient(135deg,#d97706,#f59e0b)", border:"none", borderRadius:9, color:"#000", fontSize:13, fontWeight:700, cursor:"pointer" }}>
                  AI 마케팅 분석 시작
                </button>
              </div>
            )}
            {analyzing && (
              <div style={{ textAlign:"center", padding:"24px 0", color:"#f59e0b", fontSize:12 }}>
                <div style={{ fontSize:28, marginBottom:10, animation:"spin 1.2s linear infinite", display:"inline-block" }}>⟳</div>
                <div>3개 API 데이터 종합 분석 중…</div>
              </div>
            )}
            {ai && !analyzing && (
              <div>
                {/* Score + Grade */}
                <div style={{ display:"flex", gap:12, alignItems:"center", marginBottom:14, background:C.card2, borderRadius:10, padding:"12px 14px" }}>
                  <GradeRing score={ai.score} grade={ai.grade}/>
                  <div style={{ flex:1 }}>
                    <div style={{ fontSize:13, fontWeight:700, color:"#fbbf24", marginBottom:4 }}>💡 {ai.headline}</div>
                    <p style={{ fontSize:11, color:C.muted, lineHeight:1.6, margin:0 }}>{ai.summary}</p>
                  </div>
                </div>

                {/* Strengths + Risks */}
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:10 }}>
                  <div style={{ background:"#042a1e", borderRadius:8, padding:"10px 12px", border:"1px solid #05996533" }}>
                    <div style={{ fontSize:10, fontWeight:600, color:"#34d399", marginBottom:6 }}>💪 강점</div>
                    {ai.strengths?.map((s,i)=>(
                      <div key={i} style={{ display:"flex", gap:5, marginBottom:4 }}>
                        <span style={{ color:"#34d399", fontSize:10, lineHeight:"16px", flexShrink:0 }}>▸</span>
                        <span style={{ fontSize:11, color:C.muted, lineHeight:1.4 }}>{s}</span>
                      </div>
                    ))}
                  </div>
                  <div style={{ background:"#1c0b0b", borderRadius:8, padding:"10px 12px", border:"1px solid #7f1d1d33" }}>
                    <div style={{ fontSize:10, fontWeight:600, color:"#f87171", marginBottom:6 }}>⚠️ 리스크</div>
                    {ai.risks?.map((r,i)=>(
                      <div key={i} style={{ display:"flex", gap:5, marginBottom:4 }}>
                        <span style={{ color:"#f87171", fontSize:10, lineHeight:"16px", flexShrink:0 }}>▸</span>
                        <span style={{ fontSize:11, color:C.muted, lineHeight:1.4 }}>{r}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Approach */}
                <div style={{ background:C.card2, borderRadius:8, padding:"10px 12px", marginBottom:10, border:`0.5px solid ${C.border}` }}>
                  <div style={{ fontSize:10, fontWeight:600, color:"#60a5fa", marginBottom:5 }}>🎯 영업 접근 전략</div>
                  <p style={{ fontSize:11, color:C.muted, lineHeight:1.6, margin:"0 0 6px" }}>{ai.approach}</p>
                  <div style={{ fontSize:11, color:C.muted }}>
                    ⏰ <span style={{ color:"#4ade80", fontWeight:600 }}>{ai.timing}</span>
                  </div>
                </div>

                {/* Persona + Signals */}
                <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:10 }}>
                  {ai.persona && (
                    <div style={{ background:C.card2, borderRadius:8, padding:"10px 12px", border:`0.5px solid ${C.border}` }}>
                      <div style={{ fontSize:10, fontWeight:600, color:"#818cf8", marginBottom:4 }}>👤 의사결정자 페르소나</div>
                      <div style={{ fontSize:11, color:C.muted, lineHeight:1.4 }}>{ai.persona}</div>
                    </div>
                  )}
                  {ai.signals?.length > 0 && (
                    <div style={{ background:C.card2, borderRadius:8, padding:"10px 12px", border:`0.5px solid ${C.border}` }}>
                      <div style={{ fontSize:10, fontWeight:600, color:"#f59e0b", marginBottom:4 }}>📡 긍정 시그널</div>
                      {ai.signals.map((s,i)=>(
                        <div key={i} style={{ fontSize:11, color:C.muted, marginBottom:3 }}>· {s}</div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Keywords */}
                {ai.keywords?.length > 0 && (
                  <div style={{ display:"flex", gap:5, flexWrap:"wrap" }}>
                    {ai.keywords.map(k=>(
                      <span key={k} style={{ fontSize:10, padding:"3px 9px", borderRadius:20, background:"#1e293b", color:C.muted, border:`0.5px solid ${C.border}` }}>#{k}</span>
                    ))}
                  </div>
                )}

                <button onClick={onAnalyze} style={{ marginTop:12, fontSize:10, padding:"5px 14px", background:"transparent", border:`0.5px solid ${C.border}`, borderRadius:6, color:C.dim, cursor:"pointer" }}>
                  ↺ 재분석
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── FOOTER ACTIONS ── */}
      <div style={{ display:"flex", borderTop:`1px solid ${C.border}`, background:C.bg }}>
        {[
          { label:analyzing?"⟳ AI 분석중":"🤖 AI 분석", onClick:()=>{ setTab("ai"); onAnalyze(); }, disabled:analyzing, color:analyzing?"#475569":"#f59e0b" },
          { label:saved?"★ 저장됨":"☆ 저장", onClick:onSave, disabled:false, color:saved?"#fbbf24":C.muted },
        ].map((btn,i)=>(
          <button key={i} onClick={btn.onClick} disabled={btn.disabled}
            style={{ flex:1, padding:"10px 0", fontSize:11, fontWeight:600, cursor:btn.disabled?"not-allowed":"pointer",
              background:"transparent", border:"none", borderLeft:i>0?`0.5px solid ${C.border}`:"none",
              color:btn.color, transition:"color .15s, background .15s" }}
            onMouseEnter={e=>{if(!btn.disabled){e.currentTarget.style.background="#1e293b55";e.currentTarget.style.color=C.text;}}}
            onMouseLeave={e=>{e.currentTarget.style.background="transparent";e.currentTarget.style.color=btn.color;}}>
            {btn.label}
          </button>
        ))}
      </div>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
    </div>
  );
}
