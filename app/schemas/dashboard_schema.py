import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class KpiCard(BaseModel):
    value: str
    badge_value: Optional[str] = None
    subtext: str


class DashboardKpis(BaseModel):
    total_farmers: KpiCard
    verified_farmers: KpiCard
    total_farm_area: KpiCard
    total_funding_received: KpiCard


class CropTypeBreakdown(BaseModel):
    crop_type: str
    count: int
    percentage: float


class MonthlyRoiPoint(BaseModel):
    month: str
    roi_percentage: float


class RecentFarmerItem(BaseModel):
    id: uuid.UUID
    name: str
    crop_type: str
    added_at: datetime
    status: str


class InvestmentStatusSummary(BaseModel):
    active: int
    repaid: int
    overdue: int
    pending: int


class CooperativeDashboardResponse(BaseModel):
    greeting_name: str
    cooperative_name: str
    kpis: DashboardKpis
    accumulative_roi: List[MonthlyRoiPoint]
    farmers_by_crop_type: List[CropTypeBreakdown]
    recent_farmers: List[RecentFarmerItem]
    investment_summary: InvestmentStatusSummary
    model_config = ConfigDict(from_attributes=True)
