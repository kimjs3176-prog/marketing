/* 국유특허 기술이전 시리즈 — 공통 렌더러
 *
 * 각 호 페이지(patents.html, patents-2.html, …)는 이 파일보다 먼저
 *   const ISSUE = <호수>;
 *   const PATENTS = [ … ];
 * 를 선언합니다. 새 호를 낼 때는 아래 SERIES 에 한 줄을 추가하세요.
 */

// 시리즈 목록 (2주 간격 발행)
const SERIES = [
  { no: 1, href: 'patents.html',   date: '2026.10.26', title: '천연물 × 유산균 발효 바이오소재', topics: '면역 · 항산화 · 장-뇌 건강' },
  { no: 2, href: 'patents-2.html', date: '2026.11.23', title: '기후변화 대응 한우 사료 첨가제', topics: '메탄 저감 · 고온 스트레스 저감' },
];

const REPORT = no => 'https://atipsum.lovable.app/?patent=' + no;
const DEFAULT_OWNER = '대한민국(농촌진흥청장)';
const pad = n => String(n).padStart(2, '0');

const STEPS = [
  ['solar:magnifer-bold-duotone', '기술 탐색', '관심 특허 확인 및 상담'],
  ['solar:document-add-bold-duotone', '신청서 제출', '기술이전 신청서 작성'],
  ['solar:checklist-minimalistic-bold-duotone', '검토 및 접수', '신청 내용 검토'],
  ['solar:pen-new-square-bold-duotone', '신청서 결재', '관리기관 승인'],
  ['solar:hand-shake-bold-duotone', '계약 체결', '통상실시권 계약'],
  ['solar:wallet-money-bold-duotone', '정산·납부', '실시료 납부 후 사업화'],
];

const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// 특허 건수 · 호수
document.querySelectorAll('[data-count]').forEach(el => el.textContent = PATENTS.length);
document.querySelectorAll('[data-issue]').forEach(el => el.textContent = 'No.' + pad(ISSUE));

// 히어로 미니 리스트
document.getElementById('heroList').innerHTML = PATENTS.map(p => `
  <li><a href="#p-${p.id}" class="flex items-center gap-4 rounded-2xl bg-white/5 border border-white/10 p-4 hover:bg-white/10 hover:border-lime2-400/50 spring">
    <span class="w-12 h-12 rounded-xl bg-gradient-to-br from-leaf-500/40 to-lime2-400/30 grid place-items-center shrink-0">
      <iconify-icon icon="${p.icon}" class="text-[1.7rem] text-lime2-300"></iconify-icon></span>
    <span class="min-w-0 flex-1">
      <span class="block text-base md:text-lg font-semibold leading-snug keep">${esc(p.short)}</span>
      <span class="block mt-0.5 text-sm font-mono text-leaf-100/60">${p.status === '등록' ? '등록' : '출원'} ${p.id}</span>
    </span>
  </a></li>`).join('');

// 특허 상세 카드
document.getElementById('patentList').innerHTML = PATENTS.map((p, i) => `
  <article id="p-${p.id}" class="reveal glass rounded-3xl p-6 md:p-10 scroll-mt-24">
    <div class="flex flex-wrap items-center gap-2 text-sm">
      <span class="px-3 py-1 rounded-full bg-lime2-400 text-leaf-950 font-bold">${esc(p.badge)}</span>
      <span class="px-3 py-1 rounded-full border ${p.status === '등록' ? 'border-leaf-300/50 text-leaf-200' : 'border-amber-300/50 text-amber-200'}">${p.status}</span>
      <span class="font-mono text-leaf-100/60">${p.status === '등록' ? '등록번호' : '출원번호'} ${p.id}</span>
      <span class="ml-auto font-mono text-leaf-100/40">${pad(i + 1)} / ${pad(PATENTS.length)}</span>
    </div>
    <h3 class="mt-4 text-[1.7rem] md:text-4xl font-bold leading-snug keep">${esc(p.title)}</h3>
    <p class="mt-3 text-lg md:text-xl text-lime2-300 keep">${esc(p.tagline)}</p>

    <div class="mt-8 grid lg:grid-cols-[1.25fr_.75fr] gap-8">
      <div class="space-y-6">
        <div class="rounded-2xl bg-white/5 border border-white/10 p-5">
          <p class="text-sm md:text-base font-semibold text-leaf-100/70 flex items-center gap-1.5"><iconify-icon icon="solar:danger-triangle-bold-duotone" class="text-amber-300 text-xl"></iconify-icon> 기존 한계</p>
          <p class="mt-2 text-base md:text-lg leading-relaxed text-leaf-50/90 keep">${esc(p.problem)}</p>
        </div>
        <div>
          <p class="text-sm md:text-base font-semibold text-leaf-100/70 flex items-center gap-1.5"><iconify-icon icon="solar:lightbulb-bolt-bold-duotone" class="text-lime2-300 text-xl"></iconify-icon> 핵심 기술</p>
          <ul class="mt-3 space-y-3">${p.solution.map(s => `
            <li class="flex gap-3 keep"><iconify-icon icon="solar:check-circle-bold" class="text-leaf-300 text-xl shrink-0 mt-1"></iconify-icon><span class="text-base md:text-lg leading-relaxed text-leaf-50/90">${esc(s)}</span></li>`).join('')}
          </ul>
        </div>
        <div>
          <p class="text-sm md:text-base font-semibold text-leaf-100/70 flex items-center gap-1.5"><iconify-icon icon="solar:widget-5-bold-duotone" class="text-lime2-300 text-xl"></iconify-icon> 활용 분야</p>
          <div class="mt-3 flex flex-wrap gap-2">${p.uses.map(u => `<span class="px-3.5 py-2 rounded-xl bg-leaf-500/15 border border-leaf-300/25 text-base text-leaf-100 keep">${esc(u)}</span>`).join('')}</div>
        </div>
        ${p.drawing ? `
        <figure class="rounded-2xl bg-white/5 border border-white/10 p-3">
          <img src="${p.drawing}" alt="${esc(p.title)} 대표 도면" loading="lazy" class="drawing w-full h-auto max-h-80 object-contain p-2" />
          <figcaption class="mt-2.5 px-1 text-sm text-leaf-100/70 keep">【대표 도면】 ${esc(p.drawingCap)}</figcaption>
        </figure>` : `
        <div class="rounded-2xl bg-white/5 border border-white/10 p-5">
          <p class="text-sm md:text-base font-semibold text-leaf-100/70 flex items-center gap-1.5"><iconify-icon icon="solar:chart-square-bold-duotone" class="text-lime2-300 text-xl"></iconify-icon> 청구항 핵심 수치</p>
          <div class="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3">${p.facts.map(([v, l]) => `
            <div class="rounded-xl bg-leaf-500/10 border border-leaf-300/20 p-4">
              <p class="font-display text-xl md:text-2xl font-bold text-lime2-300 keep">${esc(v)}</p>
              <p class="mt-1 text-sm text-leaf-100/70 keep">${esc(l)}</p>
            </div>`).join('')}
          </div>
        </div>`}
      </div>

      <aside class="space-y-5">
        <dl class="rounded-2xl bg-white/5 border border-white/10 p-5 text-base space-y-3">
          <div class="flex justify-between gap-4"><dt class="text-leaf-100/60 shrink-0">출원번호</dt><dd class="font-mono text-right">${p.appNo}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-leaf-100/60 shrink-0">출원일</dt><dd class="text-right">${p.appDate}</dd></div>
          ${p.regDate ? `<div class="flex justify-between gap-4"><dt class="text-leaf-100/60 shrink-0">등록일</dt><dd class="text-right">${p.regDate}</dd></div>` : ''}
          ${p.openDate ? `<div class="flex justify-between gap-4"><dt class="text-leaf-100/60 shrink-0">공개일</dt><dd class="text-right">${p.openDate}</dd></div>` : ''}
          <div class="flex justify-between gap-4"><dt class="text-leaf-100/60 shrink-0">존속기간 만료</dt><dd class="text-right">${p.expire}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-leaf-100/60 shrink-0">권리자</dt><dd class="text-right keep">${esc(p.owner || DEFAULT_OWNER)}</dd></div>
          <div class="flex justify-between gap-4"><dt class="text-leaf-100/60 shrink-0">발명자</dt><dd class="text-right keep">${esc(p.inventors)}</dd></div>
          <div class="pt-2 border-t border-white/10"><dt class="text-leaf-100/60">IPC</dt><dd class="mt-1 font-mono text-sm text-leaf-100/80 leading-relaxed">${esc(p.ipc)}</dd></div>
        </dl>
        <div class="flex flex-wrap gap-1.5">${p.keywords.map(k => `<span class="text-sm px-3 py-1 rounded-full bg-white/5 border border-white/10 text-leaf-100/80">#${esc(k)}</span>`).join('')}</div>
        <div class="grid grid-cols-2 gap-2">
          <a href="${REPORT(p.id)}" target="_blank" rel="noopener" class="inline-flex items-center justify-center gap-1.5 px-3 py-3 rounded-xl glass text-base font-semibold hover:border-lime2-400/60 spring">
            <iconify-icon icon="solar:document-text-bold-duotone" class="text-lg text-lime2-300"></iconify-icon> AI 분석 리포트</a>
          <a href="#contact" class="inline-flex items-center justify-center gap-1.5 px-3 py-3 rounded-xl bg-lime2-400 text-leaf-950 text-base font-bold hover:bg-lime2-300 spring">
            <iconify-icon icon="solar:hand-shake-bold" class="text-lg"></iconify-icon> 이전 문의</a>
        </div>
      </aside>
    </div>
  </article>`).join('');

// 비교 표 — 행 이름은 첫 특허의 cmp 순서를 따르고, 권리 상태 행을 덧붙임
document.getElementById('compareHead').insertAdjacentHTML('beforeend', PATENTS.map(p =>
  `<th class="p-5 font-medium"><span class="text-lime2-300 font-semibold">${esc(p.badge)}</span><br><span class="text-sm font-mono">${p.id}</span></th>`).join(''));
const ROWS = Object.keys(PATENTS[0].cmp).map(k => [esc(k), PATENTS.map(p => esc(p.cmp[k] ?? '—'))]);
ROWS.splice(ROWS.length - 1, 0, ['권리 상태', PATENTS.map(p => p.status + (p.regDate ? ` (${p.regDate})` : ` (공개 ${p.openDate})`))]);
document.getElementById('compareBody').innerHTML = ROWS.map(([k, vals]) => `
  <tr class="border-b border-white/5 last:border-0">
    <th scope="row" class="p-5 text-left font-medium text-leaf-100/60 whitespace-nowrap">${k}</th>
    ${vals.map(v => `<td class="p-5 text-leaf-50/90">${v}</td>`).join('')}
  </tr>`).join('');

// 기술이전 절차
document.getElementById('steps').innerHTML = STEPS.map(([icon, t, d], i) => `
  <li class="reveal glass glass-hover spring rounded-2xl p-5" style="--i:${i}">
    <div class="flex items-center justify-between">
      <iconify-icon icon="${icon}" class="text-3xl text-lime2-300"></iconify-icon>
      <span class="font-display text-xs text-leaf-100/40">STEP ${i + 1}</span>
    </div>
    <p class="mt-4 font-semibold">${t}</p>
    <p class="mt-1 text-xs text-leaf-100/60 keep">${d}</p>
  </li>`).join('');

// 시리즈 목록 (모든 호)
const seriesEl = document.getElementById('seriesList');
if (seriesEl) seriesEl.innerHTML = SERIES.map(s => {
  const cur = s.no === ISSUE;
  return `
  <a href="${cur ? '#top' : s.href}" ${cur ? 'aria-current="page"' : ''} class="glass ${cur ? 'border-lime2-400/60' : 'glass-hover'} spring rounded-2xl p-5 flex flex-col gap-2">
    <span class="flex items-center justify-between text-sm">
      <span class="font-display font-bold text-lime2-300">No.${pad(s.no)}</span>
      <span class="${cur ? 'px-2 py-0.5 rounded-full bg-lime2-400 text-leaf-950 text-xs font-bold' : 'text-leaf-100/50 font-mono text-xs'}">${cur ? '현재 호' : s.date}</span>
    </span>
    <span class="text-lg font-semibold leading-snug keep">${esc(s.title)}</span>
    <span class="text-sm text-leaf-100/60 keep">${esc(s.topics)}</span>
  </a>`;
}).join('');

// 스크롤 등장
const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } }), { threshold: .12 });
document.querySelectorAll('.reveal').forEach(el => io.observe(el));
