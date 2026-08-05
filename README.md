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

## 매출액 기준 기업 선별 (`scripts/screen_revenue.py`)

기첨부 기업의 사업자등록번호 목록에서 **직전연도 매출액 50억 원 이상** 기업을 골라내는 CLI입니다.

### 데이터 흐름과 제약

공공데이터포털 API 두 개를 순차로 씁니다.

| 단계 | API | 입력 키 | 얻는 것 |
| --- | --- | --- | --- |
| 1 | 국세청_사업자등록정보 진위확인 및 상태조회 (`api.odcloud.kr`) | 사업자등록번호 | 계속/휴업/폐업, 과세유형 |
| 2 | 금융위원회_기업재무정보 요약재무제표 (`apis.data.go.kr`) | **법인등록번호(`crno`)** | 매출액 |

**두 API 사이에 키가 이어지지 않습니다.** 국세청 API는 사업자등록번호만 받고 법인등록번호를
돌려주지 않으며, 금융위 재무 API는 법인등록번호만 받습니다. 공공데이터포털에는 사업자등록번호를
법인등록번호로 변환해 주는 무료 API가 없으므로, 그 매핑은 `--crno-map` CSV로 주입해야 합니다.

매핑 확보 경로:

- Open DART `company.json` — `bizr_no`(사업자등록번호)와 `jurir_no`(법인등록번호)를 함께 반환.
  단 `corp_code` 단위 조회라 전수 색인에는 10만 건 이상 호출이 필요합니다(일 한도 20,000건).
- 기관이 이미 보유한 기업 대장·계약 관리 시스템의 법인등록번호 컬럼 (가장 현실적).
- NICE·KED 등 유료 기업정보 서비스의 매핑 파일.

또한 금융위 재무정보는 **외부감사 대상 법인 위주**입니다. 개인사업자와 소규모 법인은 재무
데이터가 없어 `판정 불가`로 남습니다 — 이는 "50억 미달"과 구분해 표기됩니다.

### 사용법

```bash
export DATA_GO_KR_API_KEY=<공공데이터포털 Decoding 인증키>

# 1) 목록 정제 — 네트워크 없이 즉시 실행. 중복·이상값 제거 후 통계 출력
python scripts/screen_revenue.py normalize data/business_numbers.txt -o data/clean.txt

# 2) 국세청 상태조회 — 폐업·휴업·간이과세자 사전 제거 (100건 단위 배치)
python scripts/screen_revenue.py status data/clean.txt -o out/status.csv

# 3) 매출액 조회 후 최종 선별
python scripts/screen_revenue.py screen data/clean.txt \
    --crno-map data/crno_map.csv --biz-year 2025 -o out/qualified.csv

# 4) 응답 필드명·금액 단위 확인용 원본 덤프
python scripts/screen_revenue.py probe --crno 1101110043221 --biz-year 2025
```

주요 옵션: `--threshold`(기본 5,000,000,000), `--biz-year`(기본 2025), `--no-fallback`(직전연도
데이터가 없을 때 전년도로 대체하지 않음), `--sleep`(호출 간 대기, 트래픽 제한 회피), `--limit`(앞
N건만 조회), `--include-all`(미달·불가 건도 CSV에 포함).

`--crno-map` CSV 형식 (헤더는 한글/영문 모두 인식):

```csv
사업자등록번호,법인등록번호,기업명
613-83-00570,110111-0043221,예시테크
```

### 입력 목록 정제 규칙

원본 목록에 섞여 있는 값들을 다음과 같이 처리합니다. 제외 사유별 건수가 집계되어 출력됩니다.

| 입력 예 | 처리 |
| --- | --- |
| `613-83-00570`, `6138300570` | 정상 → `6138300570` |
| `"\t130-81-74011"`, ` 316-81-18063` | 공백·탭·따옴표 제거 후 정상 |
| `개인`, `확인불가`, `무상`, `개인(이름)` | `NON_BRN_MARKER` |
| `245-96-0120`, `616-81-7013`, `5935900`, `415-291-11745` | `BAD_LENGTH` |
| `000-00-00000`, `130-00-00000` | `ALL_ZERO` |
| 체크섬 불일치 | `BAD_CHECKSUM` (`--no-checksum`으로 우회 가능) |

사업자등록번호 검증은 국세청 체크섬 규칙(가중치 `1,3,7,1,3,7,1,3,5`)을 사용합니다.

### 조회량 관리

매출액 조회는 사업자당 1~2회 호출이므로, 유효 번호 N건이면 최대 2N건입니다. 공공데이터포털
개발계정 일 한도(보통 1,000건)를 넘길 수 있으니 `--limit`으로 나눠 실행하거나 운영계정 상향
승인을 받으십시오. `--sleep 0.2` 정도를 주면 순간 트래픽 제한을 피할 수 있습니다.

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
