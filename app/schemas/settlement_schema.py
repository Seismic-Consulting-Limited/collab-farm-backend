import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.models.settlement_model import SettlementStatus


class SettlementMetricsResponse(BaseModel):
    total_settled: Decimal
    total_settled_growth_pct: float
    pending_settlement_amount: Decimal
    pending_settlement_count: int
    this_month_amount: Decimal
    this_month_growth_pct: float
    total_settlements_count: int


class FarmerSummarySchema(BaseModel):
    id: uuid.UUID
    full_name: str
    farmer_code: str
    avatar_url: Optional[str] = Field(None, validation_alias="photo")

    model_config = ConfigDict(from_attributes=True)


class PackageSummarySchema(BaseModel):
    id: uuid.UUID
    title: str
    category: str
    package_total_amount: float

    model_config = ConfigDict(from_attributes=True)


class SettlementListItemResponse(BaseModel):
    id: uuid.UUID
    farmer: FarmerSummarySchema
    package: PackageSummarySchema
    amount_to_be_settled: Decimal
    category: str
    settlement_due_date: Optional[date]
    status: SettlementStatus
    reference: str

    model_config = ConfigDict(from_attributes=True)


class InvestorSettlementSchema(BaseModel):
    investor_id: uuid.UUID
    investor_name: str
    amount_to_be_settled: Decimal


class SettlementDetailResponse(BaseModel):
    id: uuid.UUID
    farmer: FarmerSummarySchema
    package: PackageSummarySchema
    amount_to_be_settled: Decimal
    settlement_percentage: float
    return_amount: Decimal
    settlement_due_date: Optional[date]
    date_settled: Optional[datetime]
    status: SettlementStatus
    reference: str
    transaction_reference: str
    investors: List[InvestorSettlementSchema]
    return_reported_at: Optional[datetime] = None
    return_note: Optional[str] = None
    review_note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SettlementPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[SettlementListItemResponse]


class InvestorToSettleSchema(BaseModel):
    investor_id: uuid.UUID
    investor_name: str
    amount_invested: float
    expected_return_amount: float
    expected_settlement_amount: float
    status: str


class PackageSettlementSummarySchema(BaseModel):
    package_id: uuid.UUID
    package_name: str
    package_category: str
    package_total_amount: float
    expected_return_percentage: float
    expected_return_amount: float
    expected_settlement_amount: float
    investors_to_be_settled: int
    status: str
    investors: List[InvestorToSettleSchema]


class PackageSettlementPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[PackageSettlementSummarySchema]


class SettlementReceiptReviewSchema(BaseModel):
    received: bool
    note: Optional[str] = None

    @model_validator(mode="after")
    def require_note_when_receipt_not_confirmed(self):
        if not self.received and not (self.note and self.note.strip()):
            raise ValueError("A note is required when receipt is not confirmed.")
        return self


class SettlementReturnReportSchema(BaseModel):
    note: Optional[str] = None


class LegacySettlementStatusUpdateSchema(BaseModel):
    status: SettlementStatus
    note: Optional[str] = None
