import uuid
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional, List, Any
from datetime import datetime, date
from enum import Enum

class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_ADMIN = "PENDING_ADMIN"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    PENDING_INVESTOR = "PENDING_INVESTOR"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AGREEMENT_PENDING = "AGREEMENT_PENDING"
    AGREEMENT_ACCEPTED = "AGREEMENT_ACCEPTED"
    FUNDED = "FUNDED"
    DISBURSING = "DISBURSING"
    COMPLETED = "COMPLETED"


class TrancheDisbursementCreate(BaseModel):
    tranche_number: int = Field(gt=0)
    amount: Decimal = Field(gt=0)
    scheduled_date: date
    milestone_description: str

class DisbursementTranchePlan(BaseModel):
    tranche_number: int = Field(..., ge=1)
    percentage: Decimal = Field(..., gt=0, le=100)
    amount: Decimal = Field(..., ge=1)
    description: Optional[str] = None


class ApplicationCreate(BaseModel):
    package_id: uuid.UUID
    requested_amount: Decimal = Field(..., gt=0,
                                      description="Funding By Cooperative in Naira",)
    target_farmer_ids: Optional[List[uuid.UUID]] = None
    notes: Optional[str]
    disbursement_plan: List[TrancheDisbursementCreate]


class ApplicationUpdateSchema(BaseModel):
    requested_amount: Optional[Decimal] = Field(None, gt=0)
    target_farmer_ids: Optional[List[uuid.UUID]] = None
    disbursemnet_plan: Optional[List[DisbursementTranchePlan]] = None
    notes: Optional[str] = None


class ApplicationRead(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    cooperative_id: uuid.UUID
    requested_amount: Decimal
    target_farmer_ids: List[uuid.UUID]
    disbursement_plan: Any
    status: ApplicationStatus
    rejection_reason: Optional[str] = None
    revision_notes: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedAplicationResponse(BaseModel):
    items: List[ApplicationRead]
    total: int
    page_size: int
    total_pages: int

class InvestorApplicationReviewSchema(BaseModel):
    approved: bool
    rejection_reason: Optional[str] = None