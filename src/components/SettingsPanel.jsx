import { useState } from "react";
import { saveKeys, DEFAULT_KEYS } from "../api/config.js";

const C = {
  bg:     "#060d18",
  panel:  "#080f1e",
  card:   "#0b1526",
  border: "#1e293b",
  dim:    "#334155",
  text:   "#e2e8f0",
  muted:  "#64748b",
};

const API_INFO = [
  {
    id:       "fsc",
    name:     "금융위원회 기업기본정보 API",
    icon:     "🏦",
    color:    "#60a5fa",
    keyLabel: "일반 인증키 (serviceKey)",
    guide:    "https://apis.data.go.kr",
    signup:   "공공데이터포털(data.go.kr) → 데이터 활용신청 → 즉시 발급",
    fields:   ["법인명·대표자·임직원수·매출액·자본금·사업장주소·홈페이지·상장여부"],
    limit:    "일 1회 갱신 / 무료",
  },
  {
    id:       "dart",
    name:     "Open DART 전자공시 API",
    icon:     "📊",
    color:    "#34d399",
    keyLabel: "crtfc_key (인증키)",
    guide:    "https://opendart.fss.or.kr",
    signup:   "opendart.fss.or.kr → 개발자 가이드 → 인증키 신청 → 최대 1일 소요",
    fields:   ["재무제표(매출·영업이익·순이익)·공시목록·기업개황·임원현황"],
    limit:    "개인 10,000건/일 / 무료",
  },
  {
    id:       "kipris",
    name:     "KIPRIS Plus 특허정보 API",
    icon:     "⚗️",
    color:    "#a78bfa",
    keyLabel: "ServiceKey (서비스키)",
    guide:    "https://plus.kipris.or.kr",
    signup:   "plus.kipris.or.kr → 서비스 신청 → 심사 후 발급 (3~5일 소요)",
    fields:   ["특허·실용신안 검색·출원인·IPC코드·등록상태·발명의명칭"],
    limit:    "월 1,000건 / 무료 (기관: 무제한)",
  },
];

export default function SettingsPanel({ keys, onSave }) {
  const [draft,  setDraft]  = useState({ ...DEFAULT_KEYS, ...keys });
  const [saved,  setSaved]  = useState(false);
  const [show,   setShow]   = useState({});

  const handleSave = () => {
    saveKeys(draft);
    onSave(draft);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const toggleShow = (id) => setShow(p => ({ ...p, [id]: !p[id] }));

  return (
    <div>
      <div style={{ marginBottom:16 }}>
        <h2 style={{ fontSize:14, fontWeight:700, color:"#94a3b8", marginBottom:3 }}>⚙️ API 키 설정</h2>
        <p style={{ fontSize:12, color:C.muted }}>각 API 키를 입력하면 해당 탭에서 실시간 데이터를 조회할 수 있습니다. 키는 브라우저 로컬 스토리지에 저장됩니다.</p>
      </div>

      <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
        {API_INFO.map(api => {
          const val = draft[api.id] || "";
          const isSet = val.length > 8;
          return (
            <div key={api.id} style={{ background:C.panel, border:`1px solid ${isSet ? api.color + "44" : C.border}`, borderRadius:12, padding:"14px 16px" }}>
              {/* HEADER */}
              <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
                <span style={{ fontSize:18 }}>{api.icon}</span>
                <div style={{ flex:1 }}>
                  <div style={{ fontSize:12, fontWeight:700, color: isSet ? api.color : "#64748b" }}>{api.name}</div>
                  <div style={{ fontSize:10, color:C.dim }}>{api.limit}</div>
                </div>
                <div style={{ display:"flex", alignItems:"center", gap:6 }}>
                  {isSet
                    ? <span style={{ fontSize:10, padding:"2px 8px", borderRadius:20, background:`${api.color}22`, color:api.color, border:`0.5px solid ${api.color}44` }}>✓ 설정됨</span>
                    : <span style={{ fontSize:10, padding:"2px 8px", borderRadius:20, background:C.card, color:C.dim, border:`0.5px solid ${C.border}` }}>미설정</span>
                  }
                </div>
              </div>

              {/* KEY INPUT */}
              <div style={{ display:"flex", gap:8, marginBottom:10 }}>
                <div style={{ flex:1, position:"relative" }}>
                  <input
                    type={show[api.id] ? "text" : "password"}
                    value={val}
                    onChange={e => setDraft(p => ({ ...p, [api.id]: e.target.value }))}
                    placeholder={`${api.keyLabel} 입력`}
                    style={{ width:"100%", background:C.bg, border:`1px solid ${isSet ? api.color + "44" : C.border}`,
                      color:C.text, borderRadius:8, padding:"7px 36px 7px 10px", fontSize:12, outline:"none", fontFamily:"monospace" }}/>
                  <button onClick={() => toggleShow(api.id)}
                    style={{ position:"absolute", right:8, top:"50%", transform:"translateY(-50%)", background:"none", border:"none", cursor:"pointer", fontSize:13, color:C.muted }}>
                    {show[api.id] ? "🙈" : "👁️"}
                  </button>
                </div>
              </div>

              {/* GUIDE */}
              <div style={{ background:C.card, border:`0.5px solid ${C.border}`, borderRadius:7, padding:"8px 10px" }}>
                <div style={{ fontSize:10, color:C.dim, marginBottom:4 }}>📋 발급 방법</div>
                <div style={{ fontSize:11, color:C.muted, lineHeight:1.5, marginBottom:4 }}>{api.signup}</div>
                <div style={{ fontSize:10, color:C.dim, marginBottom:3 }}>📦 제공 데이터</div>
                <div style={{ fontSize:11, color:C.muted }}>{api.fields.join(" · ")}</div>
                <a href={api.guide} target="_blank" rel="noopener"
                  style={{ fontSize:10, color:"#3b82f6", display:"inline-block", marginTop:5 }}>🔗 {api.guide}</a>
              </div>
            </div>
          );
        })}
      </div>

      {/* SAVE BUTTON */}
      <div style={{ marginTop:16, display:"flex", justifyContent:"flex-end", gap:10, alignItems:"center" }}>
        <button onClick={() => { setDraft({ ...DEFAULT_KEYS }); }}
          style={{ padding:"8px 16px", background:C.card, border:`0.5px solid ${C.border}`, borderRadius:8, color:C.muted, fontSize:12, cursor:"pointer" }}>
          초기화
        </button>
        <button onClick={handleSave}
          style={{ padding:"8px 24px", background: saved ? "#059669" : "linear-gradient(135deg, #1d4ed8, #3b82f6)",
            border:"none", borderRadius:8, color:"#fff", fontSize:12, fontWeight:700, cursor:"pointer", transition:"background .3s" }}>
          {saved ? "✓ 저장 완료" : "💾 키 저장"}
        </button>
      </div>

      {/* SECURITY NOTE */}
      <div style={{ marginTop:10, padding:"8px 12px", background:"#0f172a", border:`0.5px solid ${C.border}`, borderRadius:8 }}>
        <div style={{ fontSize:10, color:C.dim, lineHeight:1.5 }}>
          🔒 보안 안내: API 키는 브라우저 로컬 스토리지에만 저장되며, 외부로 전송되지 않습니다.
          Vercel 배포 시 <code style={{ color:"#94a3b8" }}>VITE_FSC_API_KEY</code> 등의 환경변수로 관리하는 것을 권장합니다.
        </div>
      </div>
    </div>
  );
}
