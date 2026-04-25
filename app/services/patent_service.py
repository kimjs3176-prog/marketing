from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


from app.models.schemas import PatentSummary


@dataclass
class KiprisClient:
    api_key: str
    base_url: str = "https://plus.kipris.or.kr/openapi/rest/patUtiModInfoSearchSevice"

    def search_company_patents(self, corp_name: str, page_no: int = 1, num_of_rows: int = 100) -> Dict[str, Any]:
        params = {
            "word": corp_name,
            "accessKey": self.api_key,
            "pageNo": page_no,
            "numOfRows": num_of_rows,
        }
        import requests
        response = requests.get(self.base_url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()


class PatentService:
    def __init__(self, kipris_client: KiprisClient):
        self.kipris_client = kipris_client

    def summarize_company_patents(self, corp_no: str, corp_name: str) -> PatentSummary:
        payload = self.kipris_client.search_company_patents(corp_name)
        items: List[Dict[str, Any]] = payload.get("response", {}).get("body", {}).get("items", [])

        total = len(items)
        active = sum(1 for item in items if item.get("registerStatus", "").startswith("등록"))
        expired = sum(1 for item in items if item.get("registerStatus", "") == "소멸")

        technology_counter: Dict[str, int] = {}
        for item in items:
            tech = item.get("ipcNumber")
            if tech:
                major = tech.split("/")[0]
                technology_counter[major] = technology_counter.get(major, 0) + 1

        top_technologies = [
            tech
            for tech, _ in sorted(technology_counter.items(), key=lambda pair: pair[1], reverse=True)[:5]
        ]

        return PatentSummary(
            corp_no=corp_no,
            corp_name=corp_name,
            total_patents=total,
            active_patents=active,
            expired_patents=expired,
            top_technologies=top_technologies,
        )
