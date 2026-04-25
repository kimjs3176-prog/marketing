# 🔭 BIZRADAR

> 공공 API 기반 B2B 마케팅 기업발굴 플랫폼

## 연동 API

| API | 기관 | 데이터 |
|-----|------|--------|
| GetCorpBasicInfoService_V2 | 금융위원회 | 기업기본정보 (임직원·매출·자본금·대표자) |
| DART OpenAPI | 금융감독원 | 재무제표·공시정보 (예정) |
| KIPRIS Plus | 한국특허정보원 | 특허·실용신안 (예정) |

## 로컬 실행

```bash
npm install
npm run dev
```

## 배포

GitHub 저장소를 Vercel에 연결하면 `main` 브랜치 푸시 시 자동 배포됩니다.

## 환경변수 (.env.local)

```
VITE_FSC_API_KEY=your_key_here
VITE_ANTHROPIC_API_KEY=your_key_here  # 프로덕션에서는 백엔드 프록시 권장
```
