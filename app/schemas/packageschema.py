import uuid
from pydantic import ConfigDict, Field, BaseModel
from datetime import datetime
from app.models.packageModel import TrancheType, PackageStatus
from typing import Optional
from decimal import Decimal
from datetime import datetime
from enum import Enum


class PackageCreate(BaseModel):
    title: str
    description: str
    total_fund_amount: float = Field(gt=0)
    tenure_months: int = Field(gt=0)
    expected_roi: float = Field(gt=0)
    tranche_type: TrancheType = TrancheType.SINGLE_TRANCHE


class PackageRead(PackageCreate):
    id: uuid.UUID
    creator_id: uuid.UUID
    status: PackageStatus
    rejection_reason: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPackageResponse(BaseModel):
    items: list[PackageRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class TrancheType(str, Enum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"


class PackageStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    LIVE = "LIVE"
    REJECTED = "REJECTED"
    CLOSED = "CLOSED"


class PackageUpdateSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    total_fund_amount: Optional[Decimal] = Field(None, gt=0)
    tenure_months: Optional[int] = Field(None, gt=0)
    expected_roi: Optional[Decimal] = Field(None, gt=0)
    tranche_type: Optional[TrancheType] = None


class PackageReadSchema(BaseModel):
    id: uuid.UUID
    creator_id: uuid.UUID
    title: str
    description: str
    total_fund_amount: Decimal
    tenure_months: int
    expected_roi: Decimal
    tranche_type: TrancheType
    status: PackageStatus
    rejection_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
