import uuid
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class InvestmentCreateRequest(BaseModel):
    pass


class InvestmentResponse(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    farming_category: str
    amount: float
    roi_percentage: float
    expected_returns: float
    due_date: Optional[datetime] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class InvestmentSummaryMetrics(BaseModel):
    total_invested: float
    active_investments: int
    packages_funded: int
    pending_settlement: float


class InvestorInvestmentListItem(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    category: str
    package_type: str
    amount_invested: float
    expected_settlement: float
    expected_settlement_date: Optional[date] = None
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
    farm_locations: List[str] = Field(default_factory=list)


class SettlementInformation(BaseModel):
    expected_settlement_date: Optional[datetime]
    expected_settlement_amount: float


class InvestmentProgressResponse(BaseModel):
    investment_id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    amount_invested: float
    expected_settlement_amount: float
    expected_profit: float
    disbursement_date: Optional[date] = None
    expected_settlement_date: Optional[date] = None
    tenure_days: int
    elapsed_days: int
    remaining_days: int
    daily_expected_payout: float
    daily_expected_profit: float
    expected_payout_to_date: float
    expected_profit_to_date: float
    progress_percentage: float
    status: str


class InvestorInvestmentDetailResponse(BaseModel):
    investment_id: uuid.UUID
    package_id: uuid.UUID
    package_title: str
    package_code: str
    category: str
    invested_date_str: str
    investment_details: YourInvestmentDetails
    investment_progress: Optional[InvestmentProgressResponse] = None
    package_progress: PackageFundingProgress
    settlement_info: SettlementInformation

    model_config = ConfigDict(from_attributes=True)
