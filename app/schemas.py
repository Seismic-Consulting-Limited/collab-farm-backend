import uuid
from pydantic import ConfigDict, Field, BaseModel
from datetime import datetime
from fastapi_users import schemas
from app.db import InvestorType, VerificationStatus, TrancheType, PackageStatus


class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus = VerificationStatus.NOT_SUBMITTED

    model_config = ConfigDict(from_attributes=True)


class UserCreate(schemas.BaseUserCreate):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType | None = None


class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus | None = None


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