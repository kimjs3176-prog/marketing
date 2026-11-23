/* 국유특허 기술이전 시리즈 — 과학원별 테마 컬러
 *
 * <html data-institute="horti|animal|agri"> 로 과학원을 지정하면 그 과학원의
 * 파트너링 행사 페이지(vol.02~04)와 같은 팔레트가 적용됩니다. 없으면 기본 그린.
 * Tailwind 스크립트 바로 다음, 페이지 스타일보다 먼저 불러옵니다.
 *   leaf  = 배경·본문 계열(50~950),  lime2 = 강조색(300·400·500)
 */
const PATENT_THEMES = {
  // 국립원예특작과학원 — vol.04 K-Natural Bio Tech (퍼플·오키드)
  horti: {
    name: '국립원예특작과학원',
    leaf: { 50: '#f5f1ff', 100: '#e8defe', 200: '#d2c1fb', 300: '#b69cf6', 400: '#9a7bec', 500: '#7c5cd6', 600: '#6346b6', 700: '#4c3591', 800: '#26185e', 900: '#1a0f4a', 950: '#110a33' },
    lime2: { 300: '#eab0e3', 400: '#df94d6', 500: '#cf74c4' },
  },
  // 국립축산과학원 — vol.03 NEXT ANIMAL-TECH (올리브·골드)
  animal: {
    name: '국립축산과학원',
    leaf: { 50: '#f3f8ec', 100: '#e1eed3', 200: '#c5dcaa', 300: '#a3c47a', 400: '#82a852', 500: '#658a3a', 600: '#4e6e2c', 700: '#3c5623', 800: '#24401e', 900: '#1a3016', 950: '#0f200d' },
    lime2: { 300: '#e0c47f', 400: '#d8b978', 500: '#c9a24a' },
  },
  // 국립농업과학원 — vol.02 SMART AGRI-FRESH TECH (틸·골드)
  agri: {
    name: '국립농업과학원',
    leaf: { 50: '#eefaf7', 100: '#d3f2ec', 200: '#a9e5da', 300: '#72d1c2', 400: '#3fb5a4', 500: '#279788', 600: '#1e7a6f', 700: '#1c615a', 800: '#0d3833', 900: '#0a2e2a', 950: '#06201d' },
    lime2: { 300: '#e0c47f', 400: '#d8b978', 500: '#c9a24a' },
  },
  // 기본 — 그린·라임
  default: {
    name: '농촌진흥청',
    leaf: { 50: '#effdf4', 100: '#d8fbe5', 200: '#b3f5cd', 300: '#79eaa9', 400: '#3fd67f', 500: '#19bb61', 600: '#0e984d', 700: '#0f773f', 800: '#115e35', 900: '#0b3d23', 950: '#04170f' },
    lime2: { 300: '#d4f78a', 400: '#bdf05a', 500: '#a3e033' },
  },
};

(() => {
  const key = document.documentElement.dataset.institute;
  const theme = PATENT_THEMES[key] || PATENT_THEMES.default;
  const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(' ');

  // CSS 변수: --leaf-500: "25 187 97" → rgb(var(--leaf-500) / .5) 처럼 투명도와 함께 사용
  const vars = [];
  const ramp = name => Object.fromEntries(Object.entries(theme[name]).map(([step, hex]) => {
    vars.push(`--${name}-${step}: ${rgb(hex)};`);
    return [step, `rgb(var(--${name}-${step}) / <alpha-value>)`];
  }));
  const colors = { leaf: ramp('leaf'), lime2: ramp('lime2') };
  const style = document.createElement('style');
  style.textContent = `:root { ${vars.join(' ')} }`;
  document.head.appendChild(style);

  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme.leaf[950]);

  tailwind.config = {
    theme: {
      extend: {
        fontFamily: {
          sans: ['Pretendard', 'system-ui', 'sans-serif'],
          display: ['"Space Grotesk"', 'Pretendard', 'sans-serif'],
          mono: ['"JetBrains Mono"', 'monospace'],
        },
        colors,
      },
    },
  };
  window.PATENT_THEME = theme;
})();
