import uuid
from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict


class InvestmentStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REPAID = "repaid"
    OVERDUE = "overdue"


class SettlementStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
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
    farming_progress: float
    farming_cycle: str
    farmers_supported: int
    expected_settlement_date: date
    expected_settlement_amount: float
    settlement_status: SettlementStatus
    status: InvestmentStatus
    model_config = ConfigDict(from_attributes=True)


class PaginatedCooperativeInvestments(BaseModel):
    total: int
    page: int
    size: int
    items: list[CooperativeInvestmentList]
