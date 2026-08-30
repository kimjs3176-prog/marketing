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
| `index.html` | **대표 페이지** — 농식품 테마기술 파트너링 vol.02 (2026. 9. 9. · 서울성암아트홀) |
| `yumang-tech-seminar.html` | (이전) 농식품 유망기술 설명회 (2026. 9. 14. · ST 과학기술컨벤션센터) |

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
