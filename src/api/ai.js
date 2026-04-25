export async function analyzeProfile(profile, targetProduct) {
  const prompt = `당신은 B2B 마케팅 전문가입니다. 3개 공공 API(금융위·DART·KIPRIS)에서 수집한 기업 데이터를 분석하여 마케팅 인사이트를 제공하세요.

=== 기업 기본정보 (금융위원회) ===
기업명: ${profile.name}
대표자: ${profile.ceo} / 설립일: ${profile.estb}
업종: ${profile.industry} / 지역: ${profile.region}
규모: ${profile.size} (임직원 ${profile.employeesStr})
자본금: ${profile.capitalStr}
상장여부: ${profile.listed ? "상장" : "비상장"}${profile.stockCode ? ` (${profile.stockCode})` : ""}

=== 재무정보 (Open DART · ${profile.finYear}년) ===
매출액: ${profile.revenueStr} (전년: ${profile.revenuePrevStr})
전년대비 성장률: ${profile.growth != null ? `${profile.growth > 0 ? "+" : ""}${profile.growth}%` : "데이터 없음"}
영업이익: ${profile.opProfitStr}
당기순이익: ${profile.netIncomeStr}

=== 특허 현황 (KIPRIS) ===
총 특허·실용신안: ${profile.patentTotal}건 (등록 ${profile.patentRegistered}건 / 출원중 ${profile.patentPending}건)
기술분야 IPC: ${profile.patentTopIpc.join(", ") || "없음"}
최근 출원: ${profile.patentRecent.slice(0,3).map(p=>p.title).join(" / ") || "없음"}

=== 최근 공시 ===
${profile.disclosures.slice(0,3).map(d=>`- ${d.date} ${d.title}`).join("\n") || "없음"}

마케팅 대상: ${targetProduct || "B2B SaaS 솔루션"}

JSON만 응답(백틱 없이):
{"score":숫자,"grade":"S/A/B/C","headline":"한줄 핵심 인사이트","summary":"3줄 종합 평가","strengths":["강점1","강점2","강점3"],"risks":["리스크1","리스크2"],"approach":"영업 접근전략 3-4문장","timing":"최적 컨택 타이밍 구체적으로","persona":"주요 의사결정자 페르소나","keywords":["키워드1","키워드2","키워드3","키워드4"],"signals":["긍정시그널1","긍정시그널2","긍정시그널3"]}`;

  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({ model:"claude-sonnet-4-20250514", max_tokens:1500, messages:[{role:"user",content:prompt}] }),
    });
    const d = await r.json();
    return JSON.parse((d.content?.[0]?.text||"{}").replace(/```json|```/g,"").trim());
  } catch { return null; }
}

export async function quickScore(profiles, targetProduct) {
  const list = profiles.map(p=>
    `- ${p.name} (${p.industry}, ${p.size}, 매출 ${p.revenueStr}, 성장률 ${p.growth!=null?p.growth+"%":"미상"}, 특허 ${p.patentTotal}건)`
  ).join("\n");
  const prompt = `B2B 마케팅 전문가로서 다음 기업들을 마케팅 잠재력 순으로 평가하세요.
마케팅 대상: ${targetProduct||"B2B SaaS"}
${list}
JSON 배열만(백틱 없이): [{"name":"기업명","score":숫자,"grade":"S/A/B/C","reason":"한줄이유"}]`;
  try {
    const r = await fetch("https://api.anthropic.com/v1/messages", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({ model:"claude-sonnet-4-20250514", max_tokens:1000, messages:[{role:"user",content:prompt}] }),
    });
    const d = await r.json();
    return JSON.parse((d.content?.[0]?.text||"[]").replace(/```json|```/g,"").trim());
  } catch { return []; }
}
