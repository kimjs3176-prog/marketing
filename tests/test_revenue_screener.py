import pytest

from app.services.revenue_screener import (
    BusinessStatus,
    ChainedResolver,
    CorpIdentity,
    CorpOutline,
    CrnoResolver,
    FinancialRecord,
    FscNameCrnoResolver,
    RevenueScreener,
    ScreeningError,
    _iter_items,
    _loads,
    has_valid_checksum,
    load_brn_table,
    normalize_brn_list,
    normalize_corp_name,
    parse_brn,
    select_qualified,
    summarize,
)

# 원본 목록에서 뽑은, 체크섬이 실제로 맞는 번호들.
VALID = ["6138300570", "1388148176", "1248100998", "1308174011", "3168118063"]


class TestChecksum:
    @pytest.mark.parametrize("brn", VALID)
    def test_accepts_real_numbers(self, brn):
        assert has_valid_checksum(brn)

    def test_rejects_wrong_last_digit(self):
        # 124-81-00998 의 검증자리는 8이므로 9는 틀린 값이다.
        assert not has_valid_checksum("1248100999")

    @pytest.mark.parametrize("bad", ["", "12481009", "12481009980", "12481O0998"])
    def test_rejects_malformed(self, bad):
        assert not has_valid_checksum(bad)


class TestParseBrn:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("613-83-00570", "6138300570"),
            ("6138300570", "6138300570"),
            ("  138-81-48176  ", "1388148176"),
            ('"\t130-81-74011"', "1308174011"),
            (" 316-81-18063", "3168118063"),
        ],
    )
    def test_normalizes_valid_forms(self, raw, expected):
        parsed = parse_brn(raw)
        assert parsed.ok
        assert parsed.brn == expected

    def test_formats_with_dashes(self):
        assert parse_brn("6138300570").formatted == "613-83-00570"

    @pytest.mark.parametrize(
        "raw,reason",
        [
            ("", "BLANK"),
            ("   ", "BLANK"),
            ("개인", "NON_BRN_MARKER"),
            ("개인(이름)", "NON_BRN_MARKER"),
            ("확인불가", "NON_BRN_MARKER"),
            ("무상", "NON_BRN_MARKER"),
            ("245-96-0120", "BAD_LENGTH"),
            ("616-81-7013", "BAD_LENGTH"),
            ("5935900", "BAD_LENGTH"),
            ("415-291-11745", "BAD_LENGTH"),
            ("41-636-057-326", "BAD_LENGTH"),
            ("000-00-00000", "ALL_ZERO"),
            ("130-00-00000", "ALL_ZERO"),
            ("124-81-00999", "BAD_CHECKSUM"),
        ],
    )
    def test_rejects_with_reason(self, raw, reason):
        parsed = parse_brn(raw)
        assert not parsed.ok
        assert parsed.reason == reason

    def test_checksum_can_be_disabled(self):
        assert parse_brn("124-81-00999", verify_checksum=False).ok


class TestNormalizeList:
    def test_dedupes_preserving_order(self):
        report = normalize_brn_list(
            ["138-81-48176", "613-83-00570", "1388148176", "138-81-48176", "확인불가", ""]
        )
        assert report.unique == ["1388148176", "6138300570"]
        assert report.duplicate_rows == 2
        assert report.total_rows == 5
        assert report.reason_counts == {"NON_BRN_MARKER": 1}

    def test_blank_rows_are_not_counted(self):
        report = normalize_brn_list(["", "  ", "\n"])
        assert report.total_rows == 0
        assert report.unique == []


# ---------------------------------------------------------------------------
# 응답 봉투 파싱
# ---------------------------------------------------------------------------


class TestIterItems:
    def test_single_item_dict(self):
        payload = {"response": {"header": {"resultCode": "00"}, "body": {"items": {"item": {"crno": "1"}}}}}
        assert list(_iter_items(payload)) == [{"crno": "1"}]

    def test_item_list(self):
        payload = {
            "response": {"header": {"resultCode": "00"}, "body": {"items": {"item": [{"crno": "1"}, {"crno": "2"}]}}}
        }
        assert len(list(_iter_items(payload))) == 2

    def test_empty_body(self):
        assert list(_iter_items({"response": {"header": {"resultCode": "00"}, "body": {}}})) == []

    def test_raises_on_error_code(self):
        payload = {"response": {"header": {"resultCode": "30", "resultMsg": "SERVICE KEY IS NOT REGISTERED"}}}
        with pytest.raises(ScreeningError, match="SERVICE KEY"):
            list(_iter_items(payload))


class TestResponseDecoding:
    def test_rejects_non_json_body(self):
        # 인증키가 등록되지 않으면 공공데이터포털은 XML 에러 문서를 돌려준다.
        with pytest.raises(ScreeningError, match="non-JSON"):
            _loads("<OpenAPI_ServiceResponse><cmmMsgHeader/></OpenAPI_ServiceResponse>", "http://x")

    def test_rejects_non_object_json(self):
        with pytest.raises(ScreeningError, match="unexpected JSON shape"):
            _loads("[1, 2, 3]", "http://x")


# ---------------------------------------------------------------------------
# 선별 로직
# ---------------------------------------------------------------------------


class FakeFinancialClient:
    """crno -> {year: 매출액} 형태로 응답을 흉내낸다."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def fetch(self, crno, biz_year):
        self.calls.append((crno, biz_year))
        amount = self.table.get(crno, {}).get(biz_year)
        if amount is None:
            return []
        return [FinancialRecord(crno=crno, biz_year=str(biz_year), revenue_krw=amount)]


class FakeStatusClient:
    def __init__(self, table):
        self.table = table

    def fetch(self, brns):
        return {brn: self.table[brn] for brn in brns if brn in self.table}


def _screener(**kwargs):
    defaults = dict(
        financial_client=FakeFinancialClient({}),
        resolver=CrnoResolver(),
        biz_year=2025,
        fallback_biz_year=2024,
    )
    defaults.update(kwargs)
    return RevenueScreener(**defaults)


class TestRevenueScreener:
    def test_flags_company_at_or_above_threshold(self):
        screener = _screener(
            financial_client=FakeFinancialClient({"1101110043221": {2025: 7_200_000_000}}),
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "1101110043221", "예시테크")}),
        )
        rows = screener.screen(["6138300570"])

        assert rows[0].meets_threshold is True
        assert rows[0].revenue_eok == 72.0
        assert rows[0].corp_name == "예시테크"
        assert rows[0].biz_year == "2025"

    def test_exactly_at_threshold_qualifies(self):
        screener = _screener(
            financial_client=FakeFinancialClient({"C": {2025: 5_000_000_000}}),
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "C")}),
        )
        assert screener.screen(["6138300570"])[0].meets_threshold is True

    def test_just_below_threshold_fails(self):
        screener = _screener(
            financial_client=FakeFinancialClient({"C": {2025: 4_999_999_999}}),
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "C")}),
        )
        assert screener.screen(["6138300570"])[0].meets_threshold is False

    def test_falls_back_to_previous_year(self):
        client = FakeFinancialClient({"C": {2024: 9_000_000_000}})
        screener = _screener(
            financial_client=client,
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "C")}),
        )
        row = screener.screen(["6138300570"])[0]

        assert client.calls == [("C", 2025), ("C", 2024)]
        assert row.biz_year == "2024"
        assert row.meets_threshold is True

    def test_no_fallback_when_disabled(self):
        client = FakeFinancialClient({"C": {2024: 9_000_000_000}})
        screener = _screener(
            financial_client=client,
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "C")}),
            fallback_biz_year=None,
        )
        row = screener.screen(["6138300570"])[0]

        assert client.calls == [("C", 2025)]
        assert row.meets_threshold is None
        assert "재무 데이터 없음" in row.note

    def test_missing_crno_is_undetermined_not_rejected(self):
        screener = _screener()
        row = screener.screen(["6138300570"])[0]

        assert row.meets_threshold is None
        assert "법인등록번호 미확보" in row.note

    def test_closed_business_is_rejected_without_financial_call(self):
        client = FakeFinancialClient({"C": {2025: 9_000_000_000}})
        screener = _screener(
            financial_client=client,
            status_client=FakeStatusClient(
                {"6138300570": BusinessStatus("6138300570", status="폐업자", status_code="03")}
            ),
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "C")}),
        )
        row = screener.screen(["6138300570"])[0]

        assert row.meets_threshold is False
        assert "비영업 상태" in row.note
        assert client.calls == []

    def test_simplified_taxpayer_is_rejected_early(self):
        client = FakeFinancialClient({"C": {2025: 9_000_000_000}})
        screener = _screener(
            financial_client=client,
            status_client=FakeStatusClient(
                {
                    "6138300570": BusinessStatus(
                        "6138300570", status="계속사업자", status_code="01", tax_type="부가가치세 간이과세자"
                    )
                }
            ),
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "C")}),
        )
        row = screener.screen(["6138300570"])[0]

        assert row.meets_threshold is False
        assert "간이과세자" in row.note
        assert client.calls == []

    def test_unregistered_brn_is_rejected(self):
        screener = _screener(
            status_client=FakeStatusClient({"6138300570": BusinessStatus("6138300570")}),
        )
        row = screener.screen(["6138300570"])[0]

        assert row.meets_threshold is False
        assert "미등록" in row.note

    def test_picks_largest_statement_when_multiple(self):
        class MultiClient:
            def fetch(self, crno, biz_year):
                return [
                    FinancialRecord(crno=crno, biz_year=str(biz_year), revenue_krw=3_000_000_000),
                    FinancialRecord(crno=crno, biz_year=str(biz_year), revenue_krw=8_000_000_000),
                ]

        screener = _screener(
            financial_client=MultiClient(),
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "C")}),
        )
        assert screener.screen(["6138300570"])[0].revenue_krw == 8_000_000_000


class TestSelectionAndSummary:
    def test_select_qualified_sorts_descending(self):
        client = FakeFinancialClient(
            {"A": {2025: 6_000_000_000}, "B": {2025: 20_000_000_000}, "C": {2025: 1_000_000_000}}
        )
        screener = _screener(
            financial_client=client,
            resolver=CrnoResolver(
                {
                    "6138300570": CorpIdentity("6138300570", "A"),
                    "1388148176": CorpIdentity("1388148176", "B"),
                    "1248100998": CorpIdentity("1248100998", "C"),
                }
            ),
        )
        rows = screener.screen(["6138300570", "1388148176", "1248100998"])
        qualified = select_qualified(rows)

        assert [row.crno for row in qualified] == ["B", "A"]
        assert summarize(rows) == {"total": 3, "qualified": 2, "below_threshold": 1, "undetermined": 0}

    def test_csv_row_shape(self):
        screener = _screener(
            financial_client=FakeFinancialClient({"C": {2025: 6_500_000_000}}),
            resolver=CrnoResolver({"6138300570": CorpIdentity("6138300570", "C", "예시")}),
        )
        payload = screener.screen(["6138300570"])[0].as_dict()

        assert payload["formatted"] == "613-83-00570"
        assert payload["revenue_krw"] == 6_500_000_000
        assert payload["revenue_eok"] == 65.0
        assert payload["meets_threshold"] == 1


class TestNormalizeCorpName:
    @pytest.mark.parametrize(
        "raw",
        ["예시테크", "(주)예시테크", "㈜예시테크", "주식회사 예시테크", "예시 테크", "예시-테크", "예시테크 주식회사"],
    )
    def test_strips_corp_forms_and_punctuation(self, raw):
        assert normalize_corp_name(raw) == "예시테크"

    def test_distinguishes_different_names(self):
        assert normalize_corp_name("예시테크") != normalize_corp_name("예시테크놀로지")


class FakeOutlineClient:
    """기업명 -> 후보 목록."""

    def __init__(self, table):
        self.table = table
        self.calls = []

    def search(self, corp_name):
        self.calls.append(corp_name)
        return self.table.get(corp_name, [])


class TestFscNameCrnoResolver:
    def test_single_exact_name_match_resolves(self):
        resolver = FscNameCrnoResolver(
            client=FakeOutlineClient({"예시테크": [CorpOutline(crno="C1", corp_name="(주)예시테크")]}),
            names={"6138300570": "예시테크"},
        )
        identity = resolver.resolve("6138300570")

        assert identity.crno == "C1"
        assert identity.matched_by == "name"
        assert identity.corp_name == "(주)예시테크"

    def test_bizno_cross_check_wins_over_name(self):
        # 동명이인 법인 둘 중 사업자등록번호가 일치하는 쪽을 고른다.
        resolver = FscNameCrnoResolver(
            client=FakeOutlineClient(
                {
                    "예시테크": [
                        CorpOutline(crno="C1", corp_name="예시테크", bizno="9999999999"),
                        CorpOutline(crno="C2", corp_name="예시테크", bizno="6138300570"),
                    ]
                }
            ),
            names={"6138300570": "예시테크"},
        )
        identity = resolver.resolve("6138300570")

        assert identity.crno == "C2"
        assert identity.matched_by == "bizno"

    def test_duplicate_names_are_left_ambiguous(self):
        resolver = FscNameCrnoResolver(
            client=FakeOutlineClient(
                {
                    "예시테크": [
                        CorpOutline(crno="C1", corp_name="예시테크"),
                        CorpOutline(crno="C2", corp_name="(주)예시테크"),
                    ]
                }
            ),
            names={"6138300570": "예시테크"},
        )
        identity = resolver.resolve("6138300570")

        assert identity.crno is None
        assert identity.is_ambiguous
        assert len(identity.candidates) == 2

    def test_partial_matches_only_are_ambiguous(self):
        # 부분일치만 잡히면 확정하지 않는다. 다른 법인의 매출을 가져올 위험이 있다.
        resolver = FscNameCrnoResolver(
            client=FakeOutlineClient({"예시테크": [CorpOutline(crno="C9", corp_name="예시테크놀로지")]}),
            names={"6138300570": "예시테크"},
        )
        identity = resolver.resolve("6138300570")

        assert identity.crno is None
        assert identity.is_ambiguous

    def test_no_candidates_is_not_ambiguous(self):
        resolver = FscNameCrnoResolver(
            client=FakeOutlineClient({}), names={"6138300570": "예시테크"}
        )
        identity = resolver.resolve("6138300570")

        assert identity.crno is None
        assert not identity.is_ambiguous
        assert identity.corp_name == "예시테크"

    def test_missing_name_skips_api_call(self):
        client = FakeOutlineClient({})
        resolver = FscNameCrnoResolver(client=client, names={})

        assert resolver.resolve("6138300570").crno is None
        assert client.calls == []

    def test_result_is_cached(self):
        client = FakeOutlineClient({"예시테크": [CorpOutline(crno="C1", corp_name="예시테크")]})
        resolver = FscNameCrnoResolver(client=client, names={"6138300570": "예시테크"})

        resolver.resolve("6138300570")
        resolver.resolve("6138300570")

        assert client.calls == ["예시테크"]

    def test_api_failure_degrades_to_unresolved(self):
        class FailingClient:
            def search(self, corp_name):
                raise ScreeningError("boom")

        resolver = FscNameCrnoResolver(client=FailingClient(), names={"6138300570": "예시테크"})
        identity = resolver.resolve("6138300570")

        assert identity.crno is None
        assert identity.corp_name == "예시테크"


class TestChainedResolver:
    def test_csv_hit_skips_name_lookup(self):
        client = FakeOutlineClient({"예시테크": [CorpOutline(crno="FROM_API", corp_name="예시테크")]})
        chained = ChainedResolver(
            [
                CrnoResolver({"6138300570": CorpIdentity("6138300570", "FROM_CSV", matched_by="csv")}),
                FscNameCrnoResolver(client=client, names={"6138300570": "예시테크"}),
            ]
        )
        identity = chained.resolve("6138300570")

        assert identity.crno == "FROM_CSV"
        assert client.calls == []

    def test_falls_through_to_name_lookup(self):
        client = FakeOutlineClient({"예시테크": [CorpOutline(crno="FROM_API", corp_name="예시테크")]})
        chained = ChainedResolver(
            [CrnoResolver(), FscNameCrnoResolver(client=client, names={"6138300570": "예시테크"})]
        )
        identity = chained.resolve("6138300570")

        assert identity.crno == "FROM_API"
        assert client.calls == ["예시테크"]

    def test_preserves_candidates_when_nothing_resolves(self):
        client = FakeOutlineClient(
            {
                "예시테크": [
                    CorpOutline(crno="C1", corp_name="예시테크"),
                    CorpOutline(crno="C2", corp_name="예시테크"),
                ]
            }
        )
        chained = ChainedResolver(
            [CrnoResolver(), FscNameCrnoResolver(client=client, names={"6138300570": "예시테크"})]
        )
        identity = chained.resolve("6138300570")

        assert identity.is_ambiguous
        assert len(identity.candidates) == 2

    def test_empty_chain_returns_bare_identity(self):
        assert ChainedResolver([]).resolve("6138300570").crno is None


class TestAmbiguityReporting:
    def test_screening_row_notes_candidates_for_manual_review(self):
        client = FakeOutlineClient(
            {
                "예시테크": [
                    CorpOutline(crno="C1", corp_name="예시테크"),
                    CorpOutline(crno="C2", corp_name="예시테크"),
                ]
            }
        )
        financial = FakeFinancialClient({"C1": {2025: 9_000_000_000}})
        screener = _screener(
            financial_client=financial,
            resolver=FscNameCrnoResolver(client=client, names={"6138300570": "예시테크"}),
        )
        row = screener.screen(["6138300570"])[0]

        # 후보를 임의로 고르지 않고 판정 불가로 남긴다.
        assert row.meets_threshold is None
        assert "수동 확인 필요" in row.note
        assert financial.calls == []

    def test_name_not_found_is_distinct_from_missing_crno(self):
        screener = _screener(
            resolver=FscNameCrnoResolver(client=FakeOutlineClient({}), names={"6138300570": "예시테크"})
        )
        row = screener.screen(["6138300570"])[0]

        assert row.meets_threshold is None
        assert "찾지 못함" in row.note

    def test_matched_by_reaches_csv_output(self):
        screener = _screener(
            financial_client=FakeFinancialClient({"C1": {2025: 9_000_000_000}}),
            resolver=FscNameCrnoResolver(
                client=FakeOutlineClient({"예시테크": [CorpOutline(crno="C1", corp_name="예시테크")]}),
                names={"6138300570": "예시테크"},
            ),
        )
        payload = screener.screen(["6138300570"])[0].as_dict()

        assert payload["matched_by"] == "name"
        assert payload["meets_threshold"] == 1


class TestLoadBrnTable:
    def test_reads_brn_and_name_columns(self, tmp_path):
        path = tmp_path / "list.csv"
        path.write_text(
            "사업자등록번호,기업명\n"
            "613-83-00570,(주)예시테크\n"
            "138-81-48176,예시산업\n"
            "확인불가,알수없음\n"
            "613-83-00570,중복행\n",
            encoding="utf-8",
        )
        report, names = load_brn_table(str(path))

        assert report.unique == ["6138300570", "1388148176"]
        assert names == {"6138300570": "(주)예시테크", "1388148176": "예시산업"}

    def test_header_row_is_rejected_not_treated_as_data(self, tmp_path):
        path = tmp_path / "list.csv"
        path.write_text("사업자등록번호,기업명\n613-83-00570,예시\n", encoding="utf-8")
        report, _ = load_brn_table(str(path))

        assert report.unique == ["6138300570"]
        assert any(item.reason == "NO_DIGITS" for item in report.rejected)

    def test_single_column_file_has_no_names(self, tmp_path):
        path = tmp_path / "list.txt"
        path.write_text("613-83-00570\n138-81-48176\n", encoding="utf-8")
        report, names = load_brn_table(str(path))

        assert len(report.unique) == 2
        assert names == {}

    def test_quoted_name_with_comma(self, tmp_path):
        path = tmp_path / "list.csv"
        path.write_text('613-83-00570,"예시테크, 주식회사"\n', encoding="utf-8")
        _, names = load_brn_table(str(path))

        assert names == {"6138300570": "예시테크, 주식회사"}

    def test_tab_separated(self, tmp_path):
        path = tmp_path / "list.tsv"
        path.write_text("613-83-00570\t예시테크\n", encoding="utf-8")
        _, names = load_brn_table(str(path))

        assert names == {"6138300570": "예시테크"}


class TestCrnoResolver:
    def test_from_csv_reads_korean_or_english_headers(self, tmp_path):
        path = tmp_path / "map.csv"
        path.write_text(
            "사업자등록번호,법인등록번호,기업명\n613-83-00570,110111-0043221,예시테크\n",
            encoding="utf-8",
        )
        resolver = CrnoResolver.from_csv(str(path))
        identity = resolver.resolve("6138300570")

        assert len(resolver) == 1
        assert identity.crno == "1101110043221"
        assert identity.corp_name == "예시테크"

    def test_unknown_brn_returns_empty_identity(self):
        identity = CrnoResolver().resolve("6138300570")
        assert identity.crno is None
