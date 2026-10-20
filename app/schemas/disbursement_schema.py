import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.disbursement_model import DisbursementStatus


class FarmerSummarySchema(BaseModel):
    id: uuid.UUID
    full_name: str
    farmer_code: Optional[str] = None
    avatar_url: Optional[str] = Field(None, validation_alias="photo")

    model_config = ConfigDict(from_attributes=True)


class PackageSummarySchema(BaseModel):
    id: uuid.UUID
    title: str
    category: str

    model_config = ConfigDict(from_attributes=True)


class DisbursementMetricsResponse(BaseModel):
    total_disbursed: float
    total_disbursed_growth_pct: float
    pending_disbursement_amount: float
    pending_disbursement_count: int
    this_month_amount: float
    this_month_growth_pct: float
    total_disbursements_count: int


class DisbursementListItemResponse(BaseModel):
    id: uuid.UUID
    farmer: FarmerSummarySchema
    package: PackageSummarySchema
    amount: float
    disbursement_date: datetime
    status: DisbursementStatus
    transaction_reference: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DisbursementDetailResponse(BaseModel):
    id: uuid.UUID
    farmer: FarmerSummarySchema
    package: PackageSummarySchema
    amount: float
    disbursement_date: datetime
    status: DisbursementStatus
    recorded_by_name: str
    transaction_reference: str
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DisbursementPaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[DisbursementListItemResponse]


class DisbursementStatusUpdateSchema(BaseModel):
    status: DisbursementStatus
    notes: Optional[str] = None