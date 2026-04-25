from app.services.company_data_service import CompanyDataService


class StubDartClient:
    def fetch_company_overview(self, corp_code):
        return {
            "corp_name": "테스트기업",
            "bizr_no": "123-45-67890",
            "stock_code": "000000",
        }

    def fetch_financials(self, corp_code, bsns_year, reprt_code="11011"):
        return [
            {"account_nm": "매출액", "thstrm_amount": "1,000"},
            {"account_nm": "영업이익", "thstrm_amount": "100"},
            {"account_nm": "당기순이익", "thstrm_amount": "50"},
        ]

    def fetch_corp_code_index(self):
        from app.models.schemas import CompanySearchResult

        return [
            CompanySearchResult(corp_name="테스트기업", corp_code="00126380", stock_code="123456"),
            CompanySearchResult(corp_name="테스트솔루션", corp_code="00999999", stock_code="654321"),
        ]


class StubFscClient:
    def fetch_basic_info(self, corp_no):
        return {
            "corpName": "테스트기업",
            "industry": "소프트웨어",
            "region": "서울",
            "affiliates": [
                {"corpNo": "110111-0000001", "corpName": "테스트홀딩스", "relation": "지배회사"}
            ],
        }


def test_build_profile_joins_financial_and_affiliates(monkeypatch):
    monkeypatch.setenv("BIZRADAR_REFERENCE_YEAR", "2025")
    service = CompanyDataService(dart_client=StubDartClient(), fsc_client=StubFscClient())

    profile = service.build_profile(corp_no="110111-1234567", corp_code="00126380", years=1)

    assert profile.corp_no == "110111-1234567"
    assert profile.corp_name == "테스트기업"
    assert profile.financials[0].revenue == 1000.0
    assert profile.affiliates[0].corp_name == "테스트홀딩스"


def test_search_companies_by_name_returns_matches():
    service = CompanyDataService(dart_client=StubDartClient(), fsc_client=StubFscClient())

    results = service.search_companies("테스트", limit=10)

    assert len(results) == 2
    assert results[0].corp_name == "테스트기업"


def test_resolve_corp_code_by_name_uses_search():
    service = CompanyDataService(dart_client=StubDartClient(), fsc_client=StubFscClient())

    corp_code = service.resolve_corp_code_by_name("테스트기업")

    assert corp_code == "00126380"
