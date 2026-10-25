# 농진청 특허 기술이전 제안서 자동 생성

A+센터 참여기업 아이템에 맞는 농촌진흥청 단독출원 특허(출원 10년 이내, 등록·공개)를 골라
기업별 기술이전 제안서(HWPX, 1쪽 제안서 + 특허당 1쪽 AI 요약서)를 만드는 스크립트 모음.

> 기업 목록·엑셀·제안서·수집 데이터·API 키는 이 저장소에 넣지 않는다. 모두 `TT_DATA`/`TT_OUT` 폴더(로컬)에 둔다.

## 준비

```bash
pip install requests openpyxl lxml jsonschema Pillow pywin32
```

- HWPX 생성: [jkf87/hwpx-skill](https://github.com/jkf87/hwpx-skill) 을 `~/.claude/skills/hwpx-skill` 에 설치
- 쪽수 확인·PDF·렌더: Windows + 한컴오피스 한글 (COM 자동화, 보안 모듈 `FilePathCheckerModule` 등록 권장)

| 환경변수 | 내용 |
|---|---|
| `TT_DATA` | 작업 데이터 폴더 (`rda.json`, `bib.json`, `packets/`, `content/`, `ais/`, `src/` …) |
| `TT_OUT` | 산출 폴더 (`경기A+센터/`, `서울A+센터/` 아래 HWPX·PDF) |
| `KIPRIS_KEY` | KIPRIS Plus Open API 서비스 키 |
| `AIS_ANON_KEY` | AIS(atipsum.lovable.app) 공개 anon 키 |

## 파이프라인

| 단계 | 스크립트 | 산출 |
|---|---|---|
| 1. 농진청 특허 수집 (KIPRIS 웹) | `kipris_web_collect.py` | `rda.json` |
| 1'. 같은 수집 (KIPRIS Plus API) | `kipris_plus_collect.py` | `kp_rda.json` |
| 2. 추천 특허 서지 검증 (단독출원·분할 원출원일·상태) | `verify_biblio.py` | `bib.json` |
| 3. 기업별 추천 선정·문구 작성 | (로컬 전용 — 기업 정보 포함) | `packets/`, `content/` |
| 4. AIS 특허 요약·사업화 점수 수집 (429 대기·재시도) | `ais.py <출원번호…>` | `ais/*.json` |
| 5. HWPX 생성 (제안서 1쪽 + 붙임 요약서, 꼬리말·줄간격 후처리) | `build_all.py [기업ID…]` | `TT_OUT/*.hwpx` |
| 6. 짧은 줄넘김 자간 정리 (한글에서 측정 → 자간/장평 조정 → 실패 시 원복) | `fitline.py <hwpx…>` | `fitline.json` |
| 7. 쪽수 확인·PDF 내보내기 | `pagecheck.py <hwpx…>` | `pages.json`, `*.pdf` |
| 일괄 | `finalize.py`(요약서 분량) → `finalize2.py`(1쪽 줄간격) → `finalize3.py`(재생성·검증) | 로그 JSON |

`build_all.py` 옵션: `CAP`(요약서 항목당 글자 수), `LS1`(1쪽 줄간격 %), `ATT_LS`(요약서 줄간격 %).
