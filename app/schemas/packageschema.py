import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TrancheType(str, Enum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"


class PackageStatus(str, Enum):
    PENDING_ADMIN_REVIEW = "PENDING_ADMIN_REVIEW"
    PENDING_INVESTOR_CONFIRMATION = "PENDING_INVESTOR_CONFIRMATION"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"


class PackageCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    total_fund_amount: float = Field(..., gt=0)
    tenure: int = Field(..., gt=0, description="Tenure duration in months")
    expected_roi: float = Field(..., gt=0,
                                description="Expected ROI percentage")
    tranche_type: TrancheType = TrancheType.SINGLE


class PackageUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    total_fund_amount: Optional[float] = Field(None, gt=0)
    tenure: Optional[int] = Field(None, gt=0)
    expected_roi: Optional[float] = Field(None, gt=0)
    tranche_type: Optional[TrancheType] = None


class AdminPackageReview(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=200)
    total_fund_amount: Optional[float] = Field(None, gt=0)
    tenure: Optional[int] = Field(None, gt=0)
    expected_roi: Optional[float] = Field(None, gt=0)
    tranche_type: Optional[TrancheType] = None
    status: PackageStatus = Field(
        ...,
        description="Must be PENDING_INVESTOR_CONFIRMATION or REJECTED",
    )
    rejection_reason: Optional[str] = None


class InvestorConfirmation(BaseModel):
    confirm: bool = Field(
        ..., description="True sets status to ACTIVE, False sets status to REJECTED"
    )
    rejection_reason: Optional[str] = None


class PackageRead(BaseModel):
    id: uuid.UUID
    creator_id: uuid.UUID
    name: str
    total_fund_amount: float
    tenure: int
    expected_roi: float
    tranche_type: TrancheType
    status: PackageStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPackageResponse(BaseModel):
    items: list[PackageRead]
    total: int
    page: int
    page_size: int
    total_pages: int
