import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class InvestorDashboardMetrics(BaseModel):
    available_balance: float
    locked_funds: float
    disbursed_funds: float
    overdue_returns_count: int


class OverdueReturnItem(BaseModel):
    investment_id: uuid.UUID
    package_name: str
    cooperative_name: str
    amount: float
    due_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FarmingCategoryAllocationItem(BaseModel):
    farming_category: str
    amount: float
    percentage: float


class PortfolioAllocation(BaseModel):
    total_portfolio_value: float
    breakdown: List[FarmingCategoryAllocationItem]


class RecentInvestmentItem(BaseModel):
    id: uuid.UUID
    package_name: str
    cooperative_name: str
    farming_category: str
    amount_invested: float
    expected_returns: float
    roi_percentage: float
    due_date: Optional[datetime] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class RecentActivityItem(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    timestamp: datetime
    activity_type: str

    model_config = ConfigDict(from_attributes=True)


class InvestorDashboardResponse(BaseModel):
    investor_name: str
    first_name: str
    metrics: InvestorDashboardMetrics
    overdue_returns: List[OverdueReturnItem]
    portfolio_allocation: PortfolioAllocation
    recent_investments: List[RecentInvestmentItem]
    recent_activities: List[RecentActivityItem]
