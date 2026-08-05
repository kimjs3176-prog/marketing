from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Affiliate:
    corp_no: str
    corp_name: str
    relation: Optional[str] = None


@dataclass
class FinancialSnapshot:
    year: int
    revenue: Optional[float] = None
    operating_profit: Optional[float] = None
    net_income: Optional[float] = None


@dataclass
class CompanyProfile:
    corp_no: str
    corp_name: str
    business_no: Optional[str] = None
    stock_code: Optional[str] = None
    industry: Optional[str] = None
    region: Optional[str] = None
    financials: List[FinancialSnapshot] = field(default_factory=list)
    affiliates: List[Affiliate] = field(default_factory=list)


@dataclass
class CompanySearchResult:
    corp_name: str
    corp_code: str
    stock_code: Optional[str] = None
    modify_date: Optional[str] = None


@dataclass
class PatentSummary:
    corp_no: str
    corp_name: str
    total_patents: int = 0
    active_patents: int = 0
    expired_patents: int = 0
    top_technologies: List[str] = field(default_factory=list)


@dataclass
class CompanyIntelResponse:
    profile: CompanyProfile
    patents: PatentSummary
    metadata: Dict[str, Any] = field(default_factory=dict)
