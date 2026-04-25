from __future__ import annotations

import io
import os
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List

from app.models.schemas import Affiliate, CompanyProfile, CompanySearchResult, FinancialSnapshot


class DataSourceError(RuntimeError):
    pass


@dataclass
class OpenDartClient:
    api_key: str
    base_url: str = "https://opendart.fss.or.kr/api"

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        import requests

        response = requests.get(f"{self.base_url}/{path}", params={**params, "crtfc_key": self.api_key}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status")
        if status and status != "000":
            raise DataSourceError(f"Open DART error: {payload.get('message', 'unknown')}")
        return payload

    def fetch_company_overview(self, corp_code: str) -> Dict[str, Any]:
        return self._get("company.json", {"corp_code": corp_code})

    def fetch_financials(self, corp_code: str, bsns_year: int, reprt_code: str = "11011") -> List[Dict[str, Any]]:
        payload = self._get(
            "fnlttSinglAcntAll.json",
            {
                "corp_code": corp_code,
                "bsns_year": bsns_year,
                "reprt_code": reprt_code,
                "fs_div": "CFS",
            },
        )
        return payload.get("list", [])

    def fetch_corp_code_index(self) -> List[CompanySearchResult]:
        import requests

        response = requests.get(
            f"{self.base_url}/corpCode.xml",
            params={"crtfc_key": self.api_key},
            timeout=20,
        )
        response.raise_for_status()

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            xml_name = zf.namelist()[0]
            xml_bytes = zf.read(xml_name)

        root = ET.fromstring(xml_bytes)
        results: List[CompanySearchResult] = []
        for item in root.findall("list"):
            corp_name = (item.findtext("corp_name") or "").strip()
            corp_code = (item.findtext("corp_code") or "").strip()
            stock_code = (item.findtext("stock_code") or "").strip() or None
            modify_date = (item.findtext("modify_date") or "").strip() or None
            if corp_name and corp_code:
                results.append(
                    CompanySearchResult(
                        corp_name=corp_name,
                        corp_code=corp_code,
                        stock_code=stock_code,
                        modify_date=modify_date,
                    )
                )

        return results


@dataclass
class FscBasicInfoClient:
    api_key: str
    base_url: str

    def fetch_basic_info(self, corp_no: str) -> Dict[str, Any]:
        import requests

        response = requests.get(
            self.base_url,
            params={"serviceKey": self.api_key, "corpNo": corp_no},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()


class CompanyDataService:
    def __init__(self, dart_client: OpenDartClient, fsc_client: FscBasicInfoClient):
        self.dart_client = dart_client
        self.fsc_client = fsc_client

    @lru_cache(maxsize=1)
    def _corp_index(self) -> tuple[CompanySearchResult, ...]:
        return tuple(self.dart_client.fetch_corp_code_index())

    def search_companies(self, query: str, limit: int = 20) -> List[CompanySearchResult]:
        keyword = query.strip().lower()
        if not keyword:
            return []

        exact: List[CompanySearchResult] = []
        partial: List[CompanySearchResult] = []
        for company in self._corp_index():
            name = company.corp_name.lower()
            if name == keyword:
                exact.append(company)
            elif keyword in name:
                partial.append(company)
            if len(exact) + len(partial) >= limit:
                break

        return exact + partial

    def resolve_corp_code_by_name(self, company_name: str) -> str:
        matches = self.search_companies(company_name, limit=1)
        if not matches:
            raise DataSourceError(f"No company found for name: {company_name}")
        return matches[0].corp_code

    def _extract_financial_snapshot(self, year: int, account_rows: List[Dict[str, Any]]) -> FinancialSnapshot:
        account_map = {row.get("account_nm"): row.get("thstrm_amount") for row in account_rows}

        def to_float(value: Any):
            if value in (None, "", "-"):
                return None
            return float(str(value).replace(",", ""))

        return FinancialSnapshot(
            year=year,
            revenue=to_float(account_map.get("매출액")),
            operating_profit=to_float(account_map.get("영업이익")),
            net_income=to_float(account_map.get("당기순이익")),
        )

    def build_profile(self, corp_no: str, corp_code: str, years: int = 3) -> CompanyProfile:
        overview = self.dart_client.fetch_company_overview(corp_code)
        basic = self.fsc_client.fetch_basic_info(corp_no)

        current_year = int(os.getenv("BIZRADAR_REFERENCE_YEAR", "2025"))
        financials = []
        for year in range(current_year, current_year - years, -1):
            rows = self.dart_client.fetch_financials(corp_code, year)
            if rows:
                financials.append(self._extract_financial_snapshot(year, rows))

        affiliates = [
            Affiliate(
                corp_no=entity.get("corpNo", ""),
                corp_name=entity.get("corpName", ""),
                relation=entity.get("relation"),
            )
            for entity in basic.get("affiliates", [])
            if entity.get("corpNo")
        ]

        return CompanyProfile(
            corp_no=corp_no,
            corp_name=overview.get("corp_name") or basic.get("corpName", ""),
            business_no=overview.get("bizr_no"),
            stock_code=overview.get("stock_code"),
            industry=basic.get("industry"),
            region=basic.get("region"),
            financials=financials,
            affiliates=affiliates,
        )
