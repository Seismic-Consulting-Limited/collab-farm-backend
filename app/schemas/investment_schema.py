import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class KpiMetricCard(BaseModel):
    value: str
    change_percentage: str
    is_positive: bool
    subtext: str


class InvestmentKpis(BaseModel):
    total_invested: KpiMetricCard
    active_investments: KpiMetricCard
    expected_settlement: KpiMetricCard
    overdue_rate: KpiMetricCard


class InvestmentListItem(BaseModel):
    id: uuid.UUID
    investor_name: str
    investor_location: str
    investor_code: str
    package_title: str
    amount: float
    date_invested: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class PaginatedInvestmentsResponse(BaseModel):
    kpis: InvestmentKpis
    items: List[InvestmentListItem]
    total: int
    page: int
    limit: int
    pages: int