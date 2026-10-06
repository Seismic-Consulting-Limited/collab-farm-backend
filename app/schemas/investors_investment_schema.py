import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class InvestmentCreateRequest(BaseModel):
    package_id: uuid.UUID
    amount: float = Field(..., gt=0, description="Amount to invest in Naira")


class InvestmentResponse(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    farming_category: str
    amount: float
    roi_percentage: float
    expected_returns: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
    

class InvestmentSummaryMetrics(BaseModel):
    total_invested: float
    active_investments: float
    packages_funded: float
    pending_settlement: float


class InvestorInvestmentListItem(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    category: str
    package_type: str
    amount_invested: float
    funding_progress_percentage: float
    expected_settlement: float
    date_invested: datetime
    status: str

    model_config = ConfigDict(from_attributes=True)


class InvestorInvestmentsOverviewResponse(BaseModel):
    summary: InvestmentSummaryMetrics
    investments: List[InvestorInvestmentListItem]
    total_count: int


class YourInvestmentDetails(BaseModel):
    amount_invested: float
    investment_id_code: str
    date_invested: datetime
    transaction_reference: str
    status: str


class PackageFundingProgress(BaseModel):
    progress_percentage: float
    amount_raised: float
    target_amount: float
    farmers_supported: int
    total_farm_size_ha: float
    locations_count: int


class SettlementInformation(BaseModel):
    expected_settlement_date: Optional[datetime]
    expected_settlement_amount: float


class InvestorInvestmentDetailResponse(BaseModel):
    investment_id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    package_code: str
    category: str
    invested_date_str: str
    investment_details: YourInvestmentDetails
    package_progress: PackageFundingProgress
    settlement_info: SettlementInformation

    model_config = ConfigDict(from_attributes=True)