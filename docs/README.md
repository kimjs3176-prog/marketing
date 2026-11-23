# 농식품 테마기술 파트너링 vol.02 — 행사 홍보 페이지

국립농업과학원 · 한국농업기술진흥원(KOAT) 주최 **농식품 테마기술 파트너링 vol.02 — SMART AGRI-FRESH TECH** 사전 홍보용 정적 페이지입니다.
빌드 도구 없이 단일 `index.html` 하나로 동작하며, GitHub Pages에서 바로 배포할 수 있습니다.

- 일시 : 2026. 9. 9.(수) 14:00
- 장소 : 서울성암아트홀
- 참가신청 : https://smore.im/form/eVRXQuGqFu

## 구성

- **Hero** — 행사명·슬로건, 일시·장소, 포스터 모티프(스마트 저장 스피어), 참가신청 CTA, 주최기관
- **행사 프로그램(About)** — 테마기술 소개 / 전시·토크 / 네트워킹 / 상담·지원
- **행사정보(Event Info)** — 일시 · 장소 · 참가대상 · 참가비
- **소개 특허기술(Tech)** — 3열 카드 그리드 13건 + 분야 필터(가공·안전 / 디지털 품질 / 정밀제어·저장)
- **오시는 길(Location)** — 공식 홈페이지 · 네이버/카카오 지도 검색 링크
- **사전등록(Register)** / **문의(Footer)**

## 페이지 목록

| 파일 | 내용 |
|------|------|
| `index.html` | **대표 페이지** — 농식품 테마기술 파트너링 vol.02 · SMART AGRI-FRESH TECH (2026. 9. 9. · 서울성암아트홀) |
| `vol3.html` | 파트너링 vol.03 · NEXT ANIMAL-TECH — 국립축산과학원 (2026. 10. 13. · 서울 성암아트홀) |
| `vol4.html` | 파트너링 vol.04 · K-Natural Bio Tech — 국립원예특작과학원 (2026. 10. 14. · 서울 성암아트홀) |
| `patents.html` | 천연물 × 유산균 발효 바이오소재 특허 3선 — 10-2839159(오가피 열매 발효 면역증진) · 10-2185438(발효오디 항산화) · 10-2024-0165540(식방풍 신바이오틱스) |
| `yumang-tech-seminar.html` | (이전) 농식품 유망기술 설명회 (2026. 9. 14. · ST 과학기술컨벤션센터) |

### 공식 포스터 (vol.03 · vol.04)

- 파일 : `assets/vol3-poster.jpg`, `assets/vol4-poster.jpg` (히어로 우측 포스터 카드 · 클릭 시 라이트박스 · 저장 버튼, `og:image` 공유 썸네일)
- `assets/volN-poster-ambient.jpg` 는 히어로 배경에 번지는 색감용 저해상도 블러 이미지입니다.
- 포스터를 교체할 때는 같은 파일명으로 덮어쓰고, 해상도가 바뀌면 `<img>`의 `width`/`height` 값도 함께 수정하세요.

### 국유특허 기술이전 시리즈 (patents*.html, 2주 간격 발행)

| 호 | 파일 | 테마 | 특허 |
|---|---|---|---|
| No.01 | `patents.html` | 천연물 × 유산균 발효 바이오소재 | 10-2839159 · 10-2185438 · 10-2024-0165540 |
| No.02 | `patents-2.html` | 기후변화 대응 한우 사료 첨가제 | 10-3013564 · 10-3013445 |

- 글래스모피즘 테마. 화면 그리기는 공통 파일 `assets/patent-series.js`가 맡고, 각 호 페이지에는 문구와 `ISSUE`·`PATENTS` 데이터만 있습니다.
- **과학원별 테마 컬러** (`assets/patent-theme.js`): `<html data-institute="…">`로 지정하면 그 과학원 파트너링 행사 페이지와 같은 팔레트가 적용됩니다.
  `horti` 국립원예특작과학원(퍼플·오키드, vol.04) · `animal` 국립축산과학원(올리브·골드, vol.03) · `agri` 국립농업과학원(틸·골드, vol.02) · 지정 없음 = 기본 그린.
  새 과학원은 `PATENT_THEMES`에 팔레트를 추가합니다. `SERIES`의 `institute`는 시리즈 카드의 색 점에 쓰입니다.
- 서지정보·청구항·대표 도면은 KIPRIS Plus, 리포트 링크는 Agri IP Summary(atipsum)입니다.
- 대표 도면 : `assets/patent-<번호>.jpg`
- **기술소개영상** : `assets/video/<출원번호>.mp4`(+ 포스터 `.jpg`). 특허 데이터의 `video: 'assets/video/<출원번호>'`로 카드 상단에 표시됩니다.
  `patent-tech-video` 스킬(템플릿 S, 나레이션·자막 포함)로 만든 영상을 웹용으로 압축해 넣습니다.
  ```bash
  ffmpeg -i <원본>.mp4 -c:v libx264 -preset slow -crf 27 -pix_fmt yuv420p -c:a aac -b:a 96k -movflags +faststart docs/assets/video/<출원번호>.mp4
  ```

**새 호 발행 순서**

1. KIPRIS 데이터·도면 받기 (환경변수 `KIPRIS_API_KEY` 필요)
   ```bash
   python3 scripts/kipris_fetch.py <출원번호 또는 등록번호> ... --drawings docs/assets > /tmp/issue.json
   ```
2. 최신 호 파일을 복사해 `patents-<N>.html` 생성 → `<title>`·메타·히어로 문구·하단 문구 수정
3. 같은 파일의 `const ISSUE = N;`과 `PATENTS` 배열을 새 특허로 교체 (비교 표 항목은 `cmp`의 키 순서대로 표시, 대표 도면이 없으면 `drawing` 대신 `facts`에 청구항 핵심 수치 3개)
4. `<html data-institute>`에 과학원 키 지정, `assets/patent-series.js`의 `SERIES`에 한 줄 추가(`institute` 포함) → 모든 호의 '시리즈' 목록에 자동 반영
5. `index.html`의 '특허 시리즈' 링크 3곳(메뉴·배너·푸터)을 새 호로 변경

## 외부 리소스 무결성(SRI)

모든 페이지는 외부 스크립트·스타일이 변조되면 브라우저가 실행을 차단하도록 구성되어 있습니다.

| 리소스 | 방식 |
|---|---|
| Tailwind CSS 3.4.17 (Play CDN) | `cdn.tailwindcss.com`이 CORS를 지원하지 않아 SRI를 걸 수 없으므로 `assets/vendor/tailwindcss-3.4.17.js`로 저장소에 포함(동일 출처). 원본 sha384 `igm5BeiBt36UU4gqwWS7imYmelpTsZlQ45FZf+XBn9MuJbn4nQr7yx1yFydocC/K` |
| iconify-icon 2.3.0 | `integrity` + `crossorigin="anonymous"` |
| Pretendard 1.3.9 (jsDelivr npm) | 버전 고정 + `integrity` + `crossorigin="anonymous"` |
| Google Fonts CSS | 브라우저마다 응답이 달라 SRI 불가(스타일시트만, 스크립트 아님) |

버전을 올릴 때는 새 파일의 해시를 다시 계산해 `integrity` 값을 교체하세요.

```bash
curl -s <URL> | openssl dgst -sha384 -binary | base64   # 결과 앞에 sha384- 를 붙임
```

## GitHub Pages 배포

1. GitHub 저장소 → **Settings → Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `main` / 폴더 `/docs` 선택 후 **Save**
4. 잠시 후 `https://<계정>.github.io/<저장소>/` 에서 `index.html`이 공개됩니다.

## 내용 수정

- **참가신청 링크** : 이미 `https://smore.im/form/eVRXQuGqFu` 로 연결되어 있습니다. 변경 시 `index.html`에서 해당 URL을 교체하세요.
- **오시는 길 주소** : `#location` 섹션의 "주소" 항목에 확정 주소를 표기하세요.
- **특허 카드** : `index.html` 하단 `<script>`의 `PATENTS` 배열을 추가/수정하면 카드와 필터가 자동 갱신됩니다.

## 로컬 미리보기

```bash
python3 -m http.server 8080 --directory docs
# http://localhost:8080
```
