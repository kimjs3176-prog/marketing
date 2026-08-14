# 농식품 테마기술 파트너링 — 행사 홍보 페이지

농촌진흥청 · 한국농업기술진흥원(KOAT) **농식품 테마기술 파트너링** 행사 홍보용 정적 페이지입니다.
빌드 도구 없이 단일 `index.html` 파일 하나로 동작하며, GitHub Pages에서 바로 배포할 수 있습니다.

## 구성

- **Hero** — 행사명 · 슬로건 · 사전등록 CTA
- **행사소개(About)** — 파트너링 취지 및 핵심 가치
- **행사정보(Event Info)** — 일시 · 장소 · 참가대상 · 참가비
- **프로그램(Program)** — 세부 일정 타임라인
- **소개특허목록(Patents)** — 카드형 목록 + 분야별 필터
- **사전등록(Register)** — 신청 CTA
- **문의(Contact)** — 문의처 · 오시는 길

## GitHub Pages 배포

1. GitHub 저장소 → **Settings → Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `main` / 폴더 `/docs` 선택 후 **Save**
4. 잠시 후 `https://<계정>.github.io/<저장소>/` 에서 공개됩니다.

> 별도 빌드가 필요 없습니다. `/docs` 폴더의 `index.html`이 그대로 게시됩니다.

## 내용 수정 (플레이스홀더 교체)

`index.html`을 열고 `<!-- EDIT: ... -->` 주석이 달린 부분을 실제 정보로 바꾸면 됩니다.

| 항목 | 위치 |
|------|------|
| 행사 일시 · 장소 · 참가정보 | `EVENT INFO` 섹션 카드 (`<!-- EDIT -->`) |
| 프로그램 일정 | `PROGRAM` 섹션 `<ol>` 타임라인 항목 |
| 사전등록 신청 링크 | 페이지 내 `href="#"` / `href="#register"` 버튼을 실제 신청 URL(구글폼 등)로 교체 |
| 문의처 · 오시는 길 | `CONTACT` 섹션 카드 |

### 소개 특허 목록 수정

특허 카드는 `index.html` 하단 `<script>`의 `PATENTS` 배열에서 관리합니다.
객체를 추가/수정하면 카드와 상단 분야 필터가 자동으로 갱신됩니다.

```js
const PATENTS = [
  {
    title: "기술명",
    category: "분야",          // 같은 category끼리 필터로 묶임
    appNo: "10-2026-000000",  // 출원(등록)번호
    applicant: "출원인",
    icon: "solar:leaf-bold-duotone", // Iconify Solar 아이콘
    summary: "기술 요약 설명"
  },
  // ...
];
```

## 로컬 미리보기

```bash
# 저장소 루트에서
python3 -m http.server 8080 --directory docs
# 브라우저에서 http://localhost:8080 접속
```
