from __future__ import annotations

import os
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query

from app.models.schemas import CompanyIntelResponse
from app.services.company_data_service import CompanyDataService, DataSourceError, FscBasicInfoClient, OpenDartClient
from app.services.patent_service import KiprisClient, PatentService

app = FastAPI(title="BizRadar Intelligence API", version="0.2.0")


def _build_company_data_service() -> CompanyDataService:
    dart_key = os.getenv("OPENDART_API_KEY")
    fsc_key = os.getenv("FSC_BASIC_INFO_API_KEY")
    fsc_url = os.getenv("FSC_BASIC_INFO_API_URL", "https://api.fsc.go.kr/company/basic")
    if not dart_key or not fsc_key:
        raise HTTPException(status_code=500, detail="OpenDART/FSC API key is not configured")

    return CompanyDataService(
        dart_client=OpenDartClient(api_key=dart_key),
        fsc_client=FscBasicInfoClient(api_key=fsc_key, base_url=fsc_url),
    )


def _build_patent_service() -> PatentService:
    kipris_key = os.getenv("KIPRIS_API_KEY")
    if not kipris_key:
        raise HTTPException(status_code=500, detail="KIPRIS API key is not configured")
    return PatentService(kipris_client=KiprisClient(api_key=kipris_key))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/companies/search")
def search_companies(query: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=100)) -> dict:
    company_service = _build_company_data_service()

    try:
        results = company_service.search_companies(query=query, limit=limit)
    except Exception as exc:  # noqa: BLE001 - pass-through for upstream API integration
        raise HTTPException(status_code=502, detail=f"Upstream API failed: {exc}") from exc

    return {
        "query": query,
        "count": len(results),
        "items": [asdict(row) for row in results],
    }


@app.get("/api/v1/companies/{corp_no}/intel", response_model=CompanyIntelResponse)
def get_company_intel(corp_no: str, corp_code: str | None = None, company_name: str | None = None) -> CompanyIntelResponse:
    company_service = _build_company_data_service()
    patent_service = _build_patent_service()

    if not corp_code:
        if not company_name:
            raise HTTPException(status_code=400, detail="corp_code or company_name is required")
        try:
            corp_code = company_service.resolve_corp_code_by_name(company_name)
        except DataSourceError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        profile = company_service.build_profile(corp_no=corp_no, corp_code=corp_code)
        patents = patent_service.summarize_company_patents(corp_no=corp_no, corp_name=profile.corp_name)
    except Exception as exc:  # noqa: BLE001 - pass-through for upstream API integration
        raise HTTPException(status_code=502, detail=f"Upstream API failed: {exc}") from exc

    return CompanyIntelResponse(
        profile=profile,
        patents=patents,
        metadata={
            "join_key": "corp_no",
            "sources": ["OpenDART", "FSC Basic Info", "KIPRIS"],
            "resolved_corp_code": corp_code,
        },
    )
