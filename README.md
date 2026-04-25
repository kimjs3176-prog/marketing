# BizRadar 기술이전 마케팅 기업 발굴 API (초안)

첨부된 카드형 UI에서 필요한 기업 인텔리전스 데이터를 제공하기 위한 백엔드 초안입니다.

## 이번 고도화 범위

1. **기업 기본정보 레이어 통합**
   - Open DART + 금융위(기업기본정보) 데이터를 `corp_no`(법인번호)로 조인
   - 단일 응답에서 재무 정보 + 계열 구조를 함께 제공
2. **KIPRIS 특허 조회 연동**
   - 기업명 기준 특허 보유 현황 조회
   - 등록/소멸 상태 및 상위 기술분류(IPC major) 요약 제공

## API


### `GET /api/v1/companies/search?query={기업명}&limit=20`

기업명 입력 기반 자동완성/검색용 API입니다. Open DART 기업코드 목록(`corpCode.xml`)을 기반으로 회사명을 검색해 `corp_code`를 반환합니다.

응답 예시:

```json
{
  "query": "테스트",
  "count": 2,
  "items": [
    {"corp_name": "테스트기업", "corp_code": "00126380", "stock_code": "123456", "modify_date": "20260102"}
  ]
}
```

### `GET /api/v1/companies/{corp_no}/intel?corp_code={dart_corp_code}`

- `corp_code`를 모를 경우 `company_name` 파라미터를 사용하면 서버에서 기업명으로 `corp_code`를 자동 해석합니다.

응답 예시:

```json
{
  "profile": {
    "corp_no": "110111-1234567",
    "corp_name": "예시테크",
    "financials": [
      {"year": 2025, "revenue": 12000000000.0, "operating_profit": 1800000000.0}
    ],
    "affiliates": [
      {"corp_no": "110111-7654321", "corp_name": "예시홀딩스", "relation": "지배회사"}
    ]
  },
  "patents": {
    "total_patents": 18,
    "active_patents": 12,
    "expired_patents": 6,
    "top_technologies": ["G06F", "A61K"]
  },
  "metadata": {
    "join_key": "corp_no",
    "sources": ["OpenDART", "FSC Basic Info", "KIPRIS"]
  }
}
```

## 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 환경 변수

- `OPENDART_API_KEY`
- `FSC_BASIC_INFO_API_KEY`
- `FSC_BASIC_INFO_API_URL` (옵션)
- `KIPRIS_API_KEY`
- `BIZRADAR_REFERENCE_YEAR` (옵션, 기본 2025)

## Vercel 배포 가이드

기존 `404: NOT_FOUND`는 Vercel이 FastAPI 엔트리포인트를 찾지 못해 발생할 수 있습니다. 이를 위해 아래 파일을 추가했습니다.

- `api/index.py`: Vercel Python 런타임용 ASGI entrypoint
- `vercel.json`: 모든 요청을 `api/index.py`로 라우팅

배포 후 확인:

- `/health` 경로에서 `{"status":"ok"}` 응답 확인
- 프로젝트 환경 변수에 아래 키 등록
  - `OPENDART_API_KEY`
  - `FSC_BASIC_INFO_API_KEY`
  - `FSC_BASIC_INFO_API_URL` (옵션)
  - `KIPRIS_API_KEY`
