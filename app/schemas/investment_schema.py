import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict


class InvestmentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REPAID = "repaid"
    OVERDUE = "overdue"


class Metrics(BaseModel):
    value: float
    trend_percentage: float  


class CooperativeInvestmentSummary(BaseModel):
    total_invested: Metrics
    active_investments: Metrics
    expected_settlement: Metrics
    overdue_investments: Metrics


class CooperativeInvestmentList(BaseModel):
    id: uuid.UUID
    investor_id_code: str
    investor_name: str
    investor_avatar: str | None = None
    package_title: str
    package_category: str | None = None
    amount: float
    date_invested: datetime
    status: InvestmentStatus
    model_config = ConfigDict(from_attributes=True)


class CooperativeInvestmentDetail(BaseModel):
    id: uuid.UUID
    investor_id_code: str
    investor_name: str
    investor_avatar: str | None = None
    investor_is_active: bool
    package_title: str
    package_category: str | None = None
    amount_invested: float
    date_invested: datetime
    payment_method: str | None = None
    transaction_reference: str | None = None
    status: InvestmentStatus
    model_config = ConfigDict(from_attributes=True)


class PaginatedCooperativeInvestments(BaseModel):
    total: int
    page: int
    size: int
    items: list[CooperativeInvestmentList]
