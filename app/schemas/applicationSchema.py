import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ApplicationStatus(str, Enum):
    PENDING_ADMIN_REVIEW = "PENDING_ADMIN_REVIEW"
    PENDING_INVESTOR_REVIEW = "PENDING_INVESTOR_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class TrancheType(str, Enum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"


class TrancheDisbursementCreate(BaseModel):
    tranche_number: int = Field(..., gt=0)
    amount: Decimal = Field(..., gt=0)
    scheduled_date: date
    milestone_description: str


class ApplicationCreate(BaseModel):
    package_id: uuid.UUID
    requested_amount: Decimal = Field(..., gt=0,
                                      description="Requested funding amount in Naira")
    tranche_type: TrancheType = TrancheType.SINGLE
    target_farmer_ids: List[uuid.UUID] = Field(
        ..., min_length=1, description="List of farmer IDs under the cooperative")
    disbursement_plan: Optional[List[TrancheDisbursementCreate]] = None
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    requested_amount: Optional[Decimal] = Field(None, gt=0)
    tranche_type: Optional[TrancheType] = None
    target_farmer_ids: Optional[List[uuid.UUID]] = Field(None, min_length=1)
    disbursement_plan: Optional[List[TrancheDisbursementCreate]] = None
    notes: Optional[str] = None


class AdminApplicationReview(BaseModel):
    approved: bool = Field(
        ..., description="True forwards application to investor review; False rejects it")
    rejection_reason: Optional[str] = None


class InvestorApplicationReview(BaseModel):
    approved: bool = Field(
        ..., description="True marks application as ACCEPTED; False sets to REJECTED")
    rejection_reason: Optional[str] = None


class ApplicationRead(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    cooperative_id: uuid.UUID
    requested_amount: Decimal
    tranche_type: TrancheType
    target_farmer_ids: List[uuid.UUID]
    target_farmers_count: int
    disbursement_plan: Optional[Any] = None
    status: ApplicationStatus
    rejection_reason: Optional[str] = None
    revision_note: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedApplicationResponse(BaseModel):
    items: List[ApplicationRead]
    total: int
    page: int
    page_size: int
    total_pages: int
