"""사업자등록번호 목록에서 직전연도 매출액 기준으로 기업을 선별한다.

공공데이터포털 API 두 개를 순차로 사용한다.

1. 국세청_사업자등록정보 진위확인 및 상태조회 (``api.odcloud.kr``)
   사업자등록번호를 그대로 받아 계속사업자/휴업/폐업 상태와 과세유형을 돌려준다.
   한 번에 100건까지 조회할 수 있어 목록 정제 단계에 쓴다.

2. 금융위원회_기업재무정보 (``apis.data.go.kr``)
   ``crno``(법인등록번호)와 ``bizYear``로 요약 재무제표를 돌려준다.
   매출액이 여기서 나온다.

두 API 사이에는 키가 이어지지 않는다. 국세청 API는 사업자등록번호만 알고
법인등록번호를 돌려주지 않고, 금융위 API는 법인등록번호만 받는다.
공공데이터포털에는 사업자등록번호를 법인등록번호로 바꿔주는 무료 API가 없으므로
그 연결은 외부에서 주입해야 한다 (``CrnoResolver`` 참고).

순수 함수(파싱/검증/판정)와 네트워크 클라이언트를 분리해 두었다.
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Sequence

# 직전연도 매출액 50억 원.
DEFAULT_REVENUE_THRESHOLD_KRW = 5_000_000_000

# 사업자등록번호 검증용 가중치 (국세청 체크섬 규칙).
_CHECKSUM_WEIGHTS = (1, 3, 7, 1, 3, 7, 1, 3, 5)

# 원본 목록에 사업자등록번호 대신 들어오는 값들. 조회 대상이 아니다.
_NON_BRN_MARKERS = ("개인", "확인불가", "무상", "미상", "해당없음", "없음")

_DIGITS_ONLY = re.compile(r"\D")


class ScreeningError(RuntimeError):
    """스크리닝 파이프라인에서 복구할 수 없는 오류."""


# ---------------------------------------------------------------------------
# 1단계: 목록 정제 (네트워크 없음)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedBrn:
    """원본 한 줄을 정규화한 결과."""

    raw: str
    brn: Optional[str] = None
    reason: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.brn is not None

    @property
    def formatted(self) -> Optional[str]:
        if self.brn is None:
            return None
        return f"{self.brn[0:3]}-{self.brn[3:5]}-{self.brn[5:10]}"


def has_valid_checksum(brn: str) -> bool:
    """국세청 사업자등록번호 체크섬을 검증한다.

    앞 9자리에 가중치를 곱해 더하고, 9번째 자리에 5를 곱한 값의 십의 자리를
    더한 뒤, 10의 보수의 끝자리가 마지막 자리와 같아야 한다.
    """
    if len(brn) != 10 or not brn.isdigit():
        return False

    total = sum(int(digit) * weight for digit, weight in zip(brn[:9], _CHECKSUM_WEIGHTS))
    total += (int(brn[8]) * 5) // 10
    return (10 - (total % 10)) % 10 == int(brn[9])


def parse_brn(raw: str, *, verify_checksum: bool = True) -> ParsedBrn:
    """원본 문자열 하나를 10자리 사업자등록번호로 정규화한다.

    실제 원본 목록에 섞여 있던 형태를 모두 흡수한다.

    - ``613-83-00570`` / ``6138300570``  → 정상
    - 앞뒤 공백, 탭, 큰따옴표로 감싼 값 (``"\\t130-81-74011"``)
    - ``개인``, ``확인불가``, ``무상``, ``개인(이름)`` → ``NON_BRN_MARKER``
    - ``245-96-0120``, ``616-81-7013`` (9자리) → ``BAD_LENGTH``
    - ``415-291-11745``, ``41-636-057-326`` (11자리 이상) → ``BAD_LENGTH``
    - ``000-00-00000``, ``130-00-00000`` → ``ALL_ZERO`` / ``BAD_CHECKSUM``
    """
    text = (raw or "").replace(" ", " ").strip().strip('"').strip("'").strip()

    if not text:
        return ParsedBrn(raw=raw, reason="BLANK")

    if any(marker in text for marker in _NON_BRN_MARKERS):
        return ParsedBrn(raw=raw, reason="NON_BRN_MARKER")

    digits = _DIGITS_ONLY.sub("", text)

    if not digits:
        return ParsedBrn(raw=raw, reason="NO_DIGITS")

    if len(digits) != 10:
        return ParsedBrn(raw=raw, reason="BAD_LENGTH")

    if set(digits) == {"0"} or digits[3:5] == "00":
        return ParsedBrn(raw=raw, reason="ALL_ZERO")

    if verify_checksum and not has_valid_checksum(digits):
        return ParsedBrn(raw=raw, brn=None, reason="BAD_CHECKSUM")

    return ParsedBrn(raw=raw, brn=digits)


@dataclass
class BrnListReport:
    """정제 결과 요약."""

    unique: List[str] = field(default_factory=list)
    rejected: List[ParsedBrn] = field(default_factory=list)
    total_rows: int = 0
    duplicate_rows: int = 0

    @property
    def reason_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in self.rejected:
            counts[item.reason or "UNKNOWN"] = counts.get(item.reason or "UNKNOWN", 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def normalize_brn_list(rows: Iterable[str], *, verify_checksum: bool = True) -> BrnListReport:
    """원본 줄들을 중복 없는 사업자등록번호 목록으로 만든다. 입력 순서를 유지한다."""
    report = BrnListReport()
    seen: set[str] = set()

    for row in rows:
        if row is None:
            continue
        if not row.strip():
            continue

        report.total_rows += 1
        parsed = parse_brn(row, verify_checksum=verify_checksum)

        if not parsed.ok:
            report.rejected.append(parsed)
            continue

        assert parsed.brn is not None
        if parsed.brn in seen:
            report.duplicate_rows += 1
            continue

        seen.add(parsed.brn)
        report.unique.append(parsed.brn)

    return report


# ---------------------------------------------------------------------------
# 법인등록번호 정제
# ---------------------------------------------------------------------------

# 주민등록번호 검증 가중치. 법인등록번호 칼럼에 개인사업자의 주민등록번호가
# 섞여 들어오는 경우가 있어, 외부 API로 내보내기 전에 걸러내기 위해 쓴다.
_RRN_WEIGHTS = (2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5)

_NON_CRNO_MARKERS = _NON_BRN_MARKERS


def looks_like_personal_id(digits: str) -> bool:
    """13자리 숫자가 법인등록번호가 아니라 주민등록번호로 보이는지 판정한다.

    세 조건을 모두 만족할 때만 참이다.

    1. 앞 6자리가 ``YYMMDD`` 형태의 유효한 날짜
    2. 7번째 자리가 1~4 (주민등록번호의 성별·세기 구분자 범위)
    3. 주민등록번호 검증식을 통과

    법인등록번호의 앞 6자리는 등기소·법인종류 코드라서 ``134111``(월 41)처럼
    날짜가 될 수 없는 값이 많고, 7번째 자리는 보통 0이며, 주민등록번호
    검증식을 우연히 통과할 확률도 낮다. 세 조건을 겹쳐 오탐을 줄였다.
    """
    if len(digits) != 13 or not digits.isdigit():
        return False

    month, day, seventh = digits[2:4], digits[4:6], digits[6]
    if not ("01" <= month <= "12" and "01" <= day <= "31"):
        return False
    if seventh not in "1234":
        return False

    total = sum(int(digit) * weight for digit, weight in zip(digits[:12], _RRN_WEIGHTS))
    return (11 - total % 11) % 10 == int(digits[12])


@dataclass(frozen=True)
class ParsedCrno:
    raw: str
    crno: Optional[str] = None
    reason: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.crno is not None


def parse_crno(raw: str, *, allow_personal_id: bool = False) -> ParsedCrno:
    """법인등록번호 한 칸을 13자리 숫자로 정규화한다.

    - ``110111-0006246`` / ``1101110006246`` → 정상
    - 빈 값 → ``BLANK`` (기업명 조회로 넘어갈 수 있으므로 오류가 아니다)
    - ``무상``, ``확인불가`` → ``NON_CRNO_MARKER``
    - ``141211-014578``(12자리), ``20534372``(8자리) → ``BAD_LENGTH``
    - 주민등록번호로 보이는 값 → ``PERSONAL_ID`` (기본적으로 조회에서 제외)
    """
    text = (raw or "").replace(" ", " ").strip().strip('"').strip("'").strip()

    if not text:
        return ParsedCrno(raw=raw, reason="BLANK")
    if any(marker in text for marker in _NON_CRNO_MARKERS):
        return ParsedCrno(raw=raw, reason="NON_CRNO_MARKER")

    digits = _DIGITS_ONLY.sub("", text)
    if not digits:
        return ParsedCrno(raw=raw, reason="NO_DIGITS")
    if len(digits) != 13:
        return ParsedCrno(raw=raw, reason="BAD_LENGTH")
    if set(digits) == {"0"}:
        return ParsedCrno(raw=raw, reason="ALL_ZERO")
    if looks_like_personal_id(digits) and not allow_personal_id:
        # 개인 식별정보를 외부 API로 전송하지 않는다.
        return ParsedCrno(raw=raw, reason="PERSONAL_ID")

    return ParsedCrno(raw=raw, crno=digits)


# ---------------------------------------------------------------------------
# 표 형태 입력 읽기
# ---------------------------------------------------------------------------

# 헤더 이름은 기관마다 다르므로 부분 일치로 찾는다. 순서가 중요하다:
# "법인등록번호"를 먼저 잡아야 "사업자"에 걸리지 않는다.
_HEADER_ALIASES: Sequence[tuple] = (
    ("crno", ("법인등록번호", "법인번호", "crno", "jurirno", "corpno")),
    ("brn", ("사업자등록번호", "사업자번호", "사업자", "brn", "bizno", "bno", "bizrno")),
    ("corp_name", ("업체명", "기업명", "회사명", "상호", "corpname", "companyname", "company")),
)

_HEADER_NOISE = re.compile(r"[\(（][^)）]*[)）]|[\s_\-.]")


def _normalize_header(cell: str) -> str:
    """헤더 칸에서 괄호 주석과 공백·기호를 떼고 비교용 문자열을 만든다.

    ``업체명(마스터 데이터)`` → ``업체명``, ``법인등록번호(마스터 데이터)`` → ``법인등록번호``
    """
    return _HEADER_NOISE.sub("", (cell or "").strip().strip('"')).lower()


def detect_columns(cells: Sequence[str]) -> Dict[str, int]:
    """헤더 행에서 필드별 컬럼 위치를 찾는다. 못 찾으면 빈 dict."""
    found: Dict[str, int] = {}
    for index, cell in enumerate(cells):
        normalized = _normalize_header(cell)
        if not normalized:
            continue
        for field, aliases in _HEADER_ALIASES:
            if field in found:
                continue
            if any(alias in normalized for alias in aliases):
                found[field] = index
                break
    return found if "brn" in found else {}


@dataclass
class CompanyTable:
    """사업자등록번호·기업명·법인등록번호를 함께 담은 입력 표."""

    report: BrnListReport = field(default_factory=BrnListReport)
    names: Dict[str, str] = field(default_factory=dict)
    crnos: Dict[str, str] = field(default_factory=dict)
    crno_rejected: List[ParsedCrno] = field(default_factory=list)
    columns: Dict[str, int] = field(default_factory=dict)

    @property
    def crno_reason_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for item in self.crno_rejected:
            if item.reason == "BLANK":
                continue  # 빈 칸은 정상. 기업명으로 조회하면 된다.
            counts[item.reason or "UNKNOWN"] = counts.get(item.reason or "UNKNOWN", 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    def to_resolver(self) -> "CrnoResolver":
        mapping = {
            brn: CorpIdentity(
                brn=brn,
                crno=crno,
                corp_name=self.names.get(brn),
                matched_by="csv",
            )
            for brn, crno in self.crnos.items()
        }
        return CrnoResolver(mapping)


def load_company_table(
    path: str,
    *,
    verify_checksum: bool = True,
    allow_personal_id: bool = False,
) -> CompanyTable:
    """CSV/TSV 한 장에서 사업자등록번호·기업명·법인등록번호를 모두 읽는다.

    헤더 이름은 부분 일치로 찾으므로 ``사업자번호``/``사업자등록번호``,
    ``업체명(마스터 데이터)``/``기업명`` 같은 표기 차이를 흡수한다. 헤더를
    찾지 못하면 ``사업자등록번호, 기업명`` 순의 2열 파일로 간주한다.

    같은 사업자등록번호가 여러 번 나올 때 기업명은 처음 나온 값을 쓰고,
    법인등록번호는 값이 채워진 첫 행에서 가져온다. 원본 목록은 같은 기업이
    수십 번 반복되면서 법인등록번호가 일부 행에만 적혀 있는 경우가 있다.

    거절 사유는 행 단위가 아니라 기업 단위로 집계한다. 끝까지 법인등록번호를
    얻지 못한 기업만 남긴다.
    """
    rows: List[List[str]] = []
    with open(path, "r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                rows.append(_split_row(line))

    if not rows:
        return CompanyTable()

    columns = detect_columns(rows[0])
    if columns:
        rows = rows[1:]
    else:
        columns = {"brn": 0, "corp_name": 1}

    def cell(row: Sequence[str], field_name: str) -> str:
        index = columns.get(field_name)
        if index is None or index >= len(row):
            return ""
        return row[index]

    table = CompanyTable(columns=columns)
    table.report = normalize_brn_list([cell(row, "brn") for row in rows], verify_checksum=verify_checksum)

    # 기업 단위 거절 사유. 나중에 법인등록번호를 얻은 기업은 제거한다.
    pending: Dict[str, ParsedCrno] = {}

    for row in rows:
        parsed = parse_brn(cell(row, "brn"), verify_checksum=verify_checksum)
        if not parsed.ok:
            continue
        brn = parsed.brn
        assert brn is not None

        name = cell(row, "corp_name").strip().strip('"')
        if name and brn not in table.names:
            table.names[brn] = name

        if brn in table.crnos:
            continue
        parsed_crno = parse_crno(cell(row, "crno"), allow_personal_id=allow_personal_id)
        if parsed_crno.ok:
            assert parsed_crno.crno is not None
            table.crnos[brn] = parsed_crno.crno
        elif brn not in pending or pending[brn].reason == "BLANK":
            # 빈 칸보다 구체적인 사유(주민등록번호·자리수 오류)를 남긴다.
            pending[brn] = parsed_crno

    table.crno_rejected = [item for brn, item in pending.items() if brn not in table.crnos]
    return table


def _split_row(line: str) -> List[str]:
    """한 줄을 칸으로 나눈다. 탭 우선, 없으면 쉼표.

    ``csv.reader`` 를 쓰므로 인용부호로 감싼 칸 안의 구분자를 살린다. 원본
    목록에 ``"\\t635-86-03151"`` 처럼 탭을 품은 인용 칸이 있어 단순 split 으로는
    컬럼이 밀린다.
    """
    stripped = line.rstrip("\n").rstrip("\r")
    if "\t" in stripped:
        return next(iter(csv.reader([stripped], delimiter="\t")), [stripped])
    if "," in stripped:
        return next(iter(csv.reader([stripped])), [stripped])
    return [stripped]


def load_brn_list(path: str, *, verify_checksum: bool = True) -> BrnListReport:
    """텍스트/CSV 파일에서 사업자등록번호를 읽는다. 첫 컬럼만 본다."""
    with open(path, "r", encoding="utf-8-sig") as handle:
        rows = [_split_row(line)[0] for line in handle]
    return normalize_brn_list(rows, verify_checksum=verify_checksum)


def load_brn_table(path: str, *, verify_checksum: bool = True) -> tuple[BrnListReport, Dict[str, str]]:
    """``사업자등록번호[,기업명]`` 형태의 파일을 읽는다.

    2번째 컬럼이 있으면 기업명으로 쓴다. 헤더 행(첫 컬럼이 사업자등록번호로
    파싱되지 않는 행)은 자동으로 걸러진다.

    같은 사업자등록번호가 여러 번 나오면 처음 나온 기업명을 쓴다.
    """
    raw_rows: List[List[str]] = []
    with open(path, "r", encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                raw_rows.append(_split_row(line))

    report = normalize_brn_list([row[0] for row in raw_rows], verify_checksum=verify_checksum)

    names: Dict[str, str] = {}
    for row in raw_rows:
        if len(row) < 2:
            continue
        parsed = parse_brn(row[0], verify_checksum=verify_checksum)
        name = row[1].strip().strip('"')
        if parsed.ok and name and parsed.brn not in names:
            assert parsed.brn is not None
            names[parsed.brn] = name

    return report, names


# ---------------------------------------------------------------------------
# HTTP 헬퍼
# ---------------------------------------------------------------------------


@dataclass
class HttpTransport:
    """재시도와 호출 간 대기를 붙인 얇은 HTTP 래퍼.

    표준 라이브러리만 쓰므로 ``HTTPS_PROXY``/``SSL_CERT_FILE`` 환경변수를 그대로 따른다.
    """

    timeout: float = 20.0
    max_retries: int = 3
    backoff: float = 2.0
    sleep_between_calls: float = 0.0
    sleeper: Callable[[float], None] = time.sleep

    def request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        body: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            request = urllib.request.Request(url, data=payload, headers=headers, method=method)
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read().decode("utf-8", errors="replace")
                if self.sleep_between_calls:
                    self.sleeper(self.sleep_between_calls)
                return _loads(raw, url)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:400]
                last_error = ScreeningError(f"HTTP {exc.code} from {url}: {detail}")
                # 4xx는 재시도해도 같다. 429는 예외.
                if 400 <= exc.code < 500 and exc.code != 429:
                    raise last_error from exc
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = ScreeningError(f"network error for {url}: {exc}")

            if attempt < self.max_retries - 1:
                self.sleeper(self.backoff * (2**attempt))

        raise last_error or ScreeningError(f"request failed: {url}")


def _loads(raw: str, url: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        # 공공데이터포털은 인증 실패 시 JSON 대신 XML 에러 문서를 돌려준다.
        raise ScreeningError(f"non-JSON response from {url}: {raw[:400]}") from exc
    if not isinstance(parsed, dict):
        raise ScreeningError(f"unexpected JSON shape from {url}: {raw[:200]}")
    return parsed


# ---------------------------------------------------------------------------
# 2단계: 국세청 사업자등록 상태조회
# ---------------------------------------------------------------------------

NTS_STATUS_URL = "https://api.odcloud.kr/api/nts-businessman/v1/status"
NTS_BATCH_SIZE = 100

# 간이과세자는 연 매출 1억 400만 원 미만이라 50억 기준을 넘을 수 없다.
SIMPLIFIED_TAX_MARKER = "간이과세자"


@dataclass(frozen=True)
class BusinessStatus:
    brn: str
    status: Optional[str] = None
    status_code: Optional[str] = None
    tax_type: Optional[str] = None
    closed_at: Optional[str] = None

    @property
    def is_active(self) -> bool:
        # b_stt_cd: 01 계속사업자, 02 휴업자, 03 폐업자
        if self.status_code:
            return self.status_code == "01"
        return self.status == "계속사업자"

    @property
    def is_registered(self) -> bool:
        """국세청에 등록된 번호인지. 미등록이면 status가 비어 온다."""
        return bool(self.status or self.status_code)

    @property
    def cannot_reach_threshold(self) -> bool:
        """과세유형만으로 50억 미달이 확정되는지."""
        return bool(self.tax_type and SIMPLIFIED_TAX_MARKER in self.tax_type)


@dataclass
class NtsBusinessStatusClient:
    """국세청_사업자등록정보 진위확인 및 상태조회."""

    service_key: str
    transport: HttpTransport = field(default_factory=HttpTransport)
    url: str = NTS_STATUS_URL

    def fetch(self, brns: Sequence[str]) -> Dict[str, BusinessStatus]:
        results: Dict[str, BusinessStatus] = {}
        for batch in _chunked(brns, NTS_BATCH_SIZE):
            results.update(self._fetch_batch(batch))
        return results

    def _fetch_batch(self, batch: Sequence[str]) -> Dict[str, BusinessStatus]:
        # serviceKey는 인코딩된 값을 그대로 쓰지 않고 quote 한 번만 적용한다.
        url = f"{self.url}?serviceKey={urllib.parse.quote(self.service_key, safe='')}"
        payload = self.transport.request_json(url, method="POST", body={"b_no": list(batch)})

        out: Dict[str, BusinessStatus] = {}
        for item in payload.get("data") or []:
            brn = _DIGITS_ONLY.sub("", str(item.get("b_no") or ""))
            if not brn:
                continue
            out[brn] = BusinessStatus(
                brn=brn,
                status=(item.get("b_stt") or None),
                status_code=(item.get("b_stt_cd") or None),
                tax_type=(item.get("tax_type") or None),
                closed_at=(item.get("end_dt") or None),
            )
        return out


# ---------------------------------------------------------------------------
# 3단계: 사업자등록번호 → 법인등록번호
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CorpIdentity:
    brn: str
    crno: Optional[str] = None
    corp_name: Optional[str] = None
    #: 해석에 사용한 근거. bizno 교차검증이 되면 "bizno", 기업명 단일 일치면 "name".
    matched_by: Optional[str] = None
    #: 기업명으로 후보가 여러 개 잡혀 자동 확정하지 못한 경우의 후보 목록.
    candidates: tuple = ()

    @property
    def is_ambiguous(self) -> bool:
        return self.crno is None and bool(self.candidates)


class CrnoResolver:
    """사업자등록번호를 법인등록번호로 바꾸는 매핑.

    공공데이터포털만으로는 이 연결을 만들 수 없다. 실무에서 쓸 수 있는 출처는
    다음 정도이며, 어느 쪽이든 CSV 한 장으로 정리해 넣으면 된다.

    - Open DART ``company.json``: ``bizr_no``(사업자등록번호)와
      ``jurir_no``(법인등록번호)를 함께 돌려준다. 다만 ``corp_code`` 단위로만
      조회되므로 전수 색인을 만들려면 10만 건 이상 호출이 필요하다.
    - 기관이 이미 보유한 기업 대장 / 계약 관리 시스템의 법인등록번호 컬럼.
    - NICE·KED 등 유료 기업정보 서비스의 매핑 파일.
    """

    def __init__(self, mapping: Optional[Dict[str, CorpIdentity]] = None):
        self._mapping: Dict[str, CorpIdentity] = dict(mapping or {})

    @classmethod
    def from_csv(cls, path: str) -> "CrnoResolver":
        """``brn,crno[,corp_name]`` 헤더를 가진 CSV를 읽는다."""
        mapping: Dict[str, CorpIdentity] = {}
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                lowered = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
                brn = _DIGITS_ONLY.sub("", lowered.get("brn") or lowered.get("사업자등록번호") or "")
                crno = _DIGITS_ONLY.sub("", lowered.get("crno") or lowered.get("법인등록번호") or "")
                name = lowered.get("corp_name") or lowered.get("기업명") or None
                if len(brn) == 10:
                    mapping[brn] = CorpIdentity(
                        brn=brn,
                        crno=crno or None,
                        corp_name=name or None,
                        matched_by="csv" if crno else None,
                    )
        return cls(mapping)

    def resolve(self, brn: str) -> CorpIdentity:
        return self._mapping.get(brn, CorpIdentity(brn=brn))

    def __len__(self) -> int:
        return len(self._mapping)


# 기업명 비교 시 무시할 법인 형태 표기.
_CORP_FORM_TOKENS = (
    "주식회사",
    "유한회사",
    "유한책임회사",
    "합자회사",
    "합명회사",
    "재단법인",
    "사단법인",
    "농업회사법인",
    "영농조합법인",
    "협동조합",
    "(주)",
    "㈜",
    "(유)",
    "(재)",
    "(사)",
)

_PUNCT = re.compile(r"[\s\-_.,'\"·ㆍ]")


def normalize_corp_name(name: str) -> str:
    """기업명을 비교용으로 정규화한다.

    ``(주)예시테크``, ``주식회사 예시테크``, ``예시 테크`` 를 모두 ``예시테크`` 로 만든다.
    """
    text = (name or "").strip()
    for token in _CORP_FORM_TOKENS:
        text = text.replace(token, "")
    return _PUNCT.sub("", text).lower()


FSC_CORP_OUTLINE_URL = (
    "https://apis.data.go.kr/1160100/service/GetCorpBasicInfoService_V2/getCorpOutline_V2"
)

# 기업개요 응답에서 사업자등록번호가 실려 오는 경우의 필드명 후보.
# 실려 있으면 기업명 대신 이 값으로 교차검증한다(동명이인 법인 오매칭 방지).
BIZNO_FIELD_CANDIDATES = ("bzno", "bizno", "brno", "bizrNo")


@dataclass(frozen=True)
class CorpOutline:
    crno: str
    corp_name: str
    bizno: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FscCorpOutlineClient:
    """금융위원회_기업기본정보 기업개요조회. 기업명으로 법인등록번호를 찾는다."""

    service_key: str
    transport: HttpTransport = field(default_factory=HttpTransport)
    url: str = FSC_CORP_OUTLINE_URL
    num_of_rows: int = 50

    def search(self, corp_name: str) -> List[CorpOutline]:
        query = urllib.parse.urlencode(
            {
                "serviceKey": self.service_key,
                "pageNo": 1,
                "numOfRows": self.num_of_rows,
                "resultType": "json",
                "corpNm": corp_name,
            },
            quote_via=urllib.parse.quote,
        )
        payload = self.transport.request_json(f"{self.url}?{query}")

        outlines: List[CorpOutline] = []
        for item in _iter_items(payload):
            crno = _DIGITS_ONLY.sub("", str(item.get("crno") or ""))
            if not crno:
                continue
            bizno = None
            for key in BIZNO_FIELD_CANDIDATES:
                candidate = _DIGITS_ONLY.sub("", str(item.get(key) or ""))
                if len(candidate) == 10:
                    bizno = candidate
                    break
            outlines.append(
                CorpOutline(
                    crno=crno,
                    corp_name=str(item.get("corpNm") or "").strip(),
                    bizno=bizno,
                    raw=item,
                )
            )
        return outlines


@dataclass
class FscNameCrnoResolver:
    """기업명으로 법인등록번호를 해석한다. ``CrnoResolver`` 와 같은 인터페이스.

    확정 규칙 (엄격한 순서):

    1. 응답에 사업자등록번호가 실려 있고 우리 번호와 일치하면 그 후보로 확정한다.
       가장 신뢰도가 높으며 동명이인 법인 문제를 없앤다.
    2. 정규화된 기업명이 정확히 하나만 일치하면 그 후보로 확정한다.
    3. 그 외(0건, 또는 2건 이상 동명)는 확정하지 않고 후보를 남긴다.
       자동으로 하나를 고르면 다른 법인의 매출을 가져올 위험이 있다.
    """

    client: FscCorpOutlineClient
    names: Dict[str, str] = field(default_factory=dict)
    _cache: Dict[str, CorpIdentity] = field(default_factory=dict, repr=False)

    def resolve(self, brn: str) -> CorpIdentity:
        if brn in self._cache:
            return self._cache[brn]

        name = self.names.get(brn)
        if not name:
            identity = CorpIdentity(brn=brn)
        else:
            identity = self._resolve_by_name(brn, name)

        self._cache[brn] = identity
        return identity

    def _resolve_by_name(self, brn: str, name: str) -> CorpIdentity:
        try:
            candidates = self.client.search(name)
        except ScreeningError:
            return CorpIdentity(brn=brn, corp_name=name)

        if not candidates:
            return CorpIdentity(brn=brn, corp_name=name)

        for candidate in candidates:
            if candidate.bizno and candidate.bizno == brn:
                return CorpIdentity(
                    brn=brn,
                    crno=candidate.crno,
                    corp_name=candidate.corp_name or name,
                    matched_by="bizno",
                )

        target = normalize_corp_name(name)
        exact = [c for c in candidates if normalize_corp_name(c.corp_name) == target]

        if len(exact) == 1:
            return CorpIdentity(
                brn=brn,
                crno=exact[0].crno,
                corp_name=exact[0].corp_name or name,
                matched_by="name",
            )

        pool = exact or candidates
        return CorpIdentity(
            brn=brn,
            corp_name=name,
            candidates=tuple((c.crno, c.corp_name) for c in pool[:10]),
        )

    def __len__(self) -> int:
        return len(self.names)


@dataclass
class ChainedResolver:
    """앞선 리졸버가 확정하지 못하면 다음 리졸버로 넘긴다.

    보유 중인 법인등록번호 CSV를 먼저 쓰고, 빠진 건만 API로 조회해 호출량을 줄인다.
    """

    resolvers: Sequence[Any]

    def resolve(self, brn: str) -> CorpIdentity:
        fallback = CorpIdentity(brn=brn)
        for resolver in self.resolvers:
            identity = resolver.resolve(brn)
            if identity.crno:
                return identity
            # 기업명이나 후보 정보가 있으면 보존해 둔다.
            if identity.corp_name or identity.candidates:
                fallback = identity
        return fallback

    def __len__(self) -> int:
        return sum(len(resolver) for resolver in self.resolvers)


# ---------------------------------------------------------------------------
# 4단계: 금융위원회 기업재무정보
# ---------------------------------------------------------------------------

FSC_SUMM_FINA_STAT_URL = (
    "https://apis.data.go.kr/1160100/service/GetFinaStatInfoService_V2/getSummFinaStat_V2"
)

# 금융위 요약재무제표의 매출액 필드. 서비스 버전에 따라 이름이 달라 후보를 순서대로 본다.
REVENUE_FIELD_CANDIDATES = ("enpSaleAmt", "saleAmt", "revenue", "enpSalesAmt")


@dataclass(frozen=True)
class FinancialRecord:
    crno: str
    biz_year: Optional[str] = None
    revenue_krw: Optional[float] = None
    statement_kind: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FscFinancialClient:
    """금융위원회_기업재무정보 요약재무제표 조회."""

    service_key: str
    transport: HttpTransport = field(default_factory=HttpTransport)
    url: str = FSC_SUMM_FINA_STAT_URL
    num_of_rows: int = 20

    def fetch(self, crno: str, biz_year: int) -> List[FinancialRecord]:
        query = urllib.parse.urlencode(
            {
                "serviceKey": self.service_key,
                "pageNo": 1,
                "numOfRows": self.num_of_rows,
                "resultType": "json",
                "crno": crno,
                "bizYear": str(biz_year),
            },
            quote_via=urllib.parse.quote,
        )
        payload = self.transport.request_json(f"{self.url}?{query}")
        return [_to_financial_record(item, crno) for item in _iter_items(payload)]


def _iter_items(payload: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
    """공공데이터포털 표준 응답 봉투에서 item 목록을 꺼낸다."""
    response = payload.get("response") or {}
    header = response.get("header") or {}
    code = str(header.get("resultCode") or "").strip()
    if code and code not in {"00", "0"}:
        raise ScreeningError(f"FSC error {code}: {header.get('resultMsg')}")

    items = ((response.get("body") or {}).get("items") or {})
    if isinstance(items, dict):
        item = items.get("item")
    else:
        item = items

    if item is None:
        return
    if isinstance(item, dict):
        yield item
    elif isinstance(item, list):
        for entry in item:
            if isinstance(entry, dict):
                yield entry


def _to_financial_record(item: Dict[str, Any], crno: str) -> FinancialRecord:
    return FinancialRecord(
        crno=str(item.get("crno") or crno),
        biz_year=(str(item.get("bizYear")) if item.get("bizYear") else None),
        revenue_krw=_first_amount(item, REVENUE_FIELD_CANDIDATES),
        statement_kind=(item.get("fnclDcdNm") or item.get("fnclDcd") or None),
        raw=item,
    )


def _first_amount(item: Dict[str, Any], keys: Sequence[str]) -> Optional[float]:
    for key in keys:
        value = _to_amount(item.get(key))
        if value is not None:
            return value
    return None


def _to_amount(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text or text in {"-", "null", "None"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _chunked(items: Sequence[str], size: int) -> Iterator[Sequence[str]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


# ---------------------------------------------------------------------------
# 5단계: 선별
# ---------------------------------------------------------------------------


@dataclass
class ScreeningRow:
    """사업자등록번호 한 건의 최종 판정."""

    brn: str
    formatted: str
    corp_name: Optional[str] = None
    crno: Optional[str] = None
    matched_by: Optional[str] = None
    nts_status: Optional[str] = None
    tax_type: Optional[str] = None
    biz_year: Optional[str] = None
    revenue_krw: Optional[float] = None
    meets_threshold: Optional[bool] = None
    note: str = ""

    @property
    def revenue_eok(self) -> Optional[float]:
        if self.revenue_krw is None:
            return None
        return round(self.revenue_krw / 100_000_000, 2)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "brn": self.brn,
            "formatted": self.formatted,
            "corp_name": self.corp_name or "",
            "crno": self.crno or "",
            "matched_by": self.matched_by or "",
            "nts_status": self.nts_status or "",
            "tax_type": self.tax_type or "",
            "biz_year": self.biz_year or "",
            "revenue_krw": "" if self.revenue_krw is None else int(self.revenue_krw),
            "revenue_eok": "" if self.revenue_eok is None else self.revenue_eok,
            "meets_threshold": "" if self.meets_threshold is None else int(self.meets_threshold),
            "note": self.note,
        }


CSV_COLUMNS = (
    "brn",
    "formatted",
    "corp_name",
    "crno",
    "matched_by",
    "nts_status",
    "tax_type",
    "biz_year",
    "revenue_krw",
    "revenue_eok",
    "meets_threshold",
    "note",
)


@dataclass
class RevenueScreener:
    """상태조회 → 법인등록번호 매핑 → 재무조회 순으로 목록을 좁힌다."""

    financial_client: FscFinancialClient
    status_client: Optional[NtsBusinessStatusClient] = None
    resolver: CrnoResolver = field(default_factory=CrnoResolver)
    threshold_krw: float = DEFAULT_REVENUE_THRESHOLD_KRW
    biz_year: int = 2025
    fallback_biz_year: Optional[int] = 2024
    skip_inactive: bool = True

    def screen(self, brns: Sequence[str]) -> List[ScreeningRow]:
        statuses: Dict[str, BusinessStatus] = {}
        if self.status_client is not None:
            statuses = self.status_client.fetch(brns)

        rows: List[ScreeningRow] = []
        for brn in brns:
            rows.append(self._screen_one(brn, statuses.get(brn)))
        return rows

    def _screen_one(self, brn: str, status: Optional[BusinessStatus]) -> ScreeningRow:
        identity = self.resolver.resolve(brn)
        row = ScreeningRow(
            brn=brn,
            formatted=f"{brn[0:3]}-{brn[3:5]}-{brn[5:10]}",
            corp_name=identity.corp_name,
            crno=identity.crno,
            matched_by=identity.matched_by,
            nts_status=status.status if status else None,
            tax_type=status.tax_type if status else None,
        )

        if status is not None:
            if not status.is_registered:
                row.meets_threshold = False
                row.note = "국세청 미등록 번호"
                return row
            if self.skip_inactive and not status.is_active:
                row.meets_threshold = False
                row.note = f"비영업 상태({status.status or status.status_code})"
                return row
            if status.cannot_reach_threshold:
                row.meets_threshold = False
                row.note = "간이과세자 — 매출 기준 미달 확정"
                return row

        if not identity.crno:
            if identity.is_ambiguous:
                names = ", ".join(f"{name}({crno})" for crno, name in identity.candidates[:3])
                row.note = f"기업명 후보 {len(identity.candidates)}건 — 수동 확인 필요: {names}"
            elif identity.corp_name:
                row.note = "기업명으로 법인등록번호를 찾지 못함(비공시 법인 등)"
            else:
                row.note = "법인등록번호 미확보 — 재무조회 불가"
            return row

        record = self._fetch_best_record(identity.crno)
        if record is None:
            row.note = "재무 데이터 없음(비공시 법인 등)"
            return row

        row.biz_year = record.biz_year
        row.revenue_krw = record.revenue_krw

        if record.revenue_krw is None:
            row.note = "매출액 항목 없음"
            return row

        row.meets_threshold = record.revenue_krw >= self.threshold_krw
        return row

    def _fetch_best_record(self, crno: str) -> Optional[FinancialRecord]:
        years = [self.biz_year]
        if self.fallback_biz_year and self.fallback_biz_year != self.biz_year:
            years.append(self.fallback_biz_year)

        for year in years:
            records = [r for r in self.financial_client.fetch(crno, year) if r.revenue_krw is not None]
            if records:
                # 연결재무제표가 있으면 그쪽 매출이 크므로 최대값을 취한다.
                return max(records, key=lambda r: r.revenue_krw or 0)
        return None


def select_qualified(rows: Iterable[ScreeningRow]) -> List[ScreeningRow]:
    """기준을 충족한 행만 매출 내림차순으로 돌려준다."""
    qualified = [row for row in rows if row.meets_threshold]
    return sorted(qualified, key=lambda row: row.revenue_krw or 0, reverse=True)


def summarize(rows: Sequence[ScreeningRow]) -> Dict[str, int]:
    """판정 결과 집계."""
    summary = {
        "total": len(rows),
        "qualified": 0,
        "below_threshold": 0,
        "undetermined": 0,
    }
    for row in rows:
        if row.meets_threshold is True:
            summary["qualified"] += 1
        elif row.meets_threshold is False:
            summary["below_threshold"] += 1
        else:
            summary["undetermined"] += 1
    return summary
