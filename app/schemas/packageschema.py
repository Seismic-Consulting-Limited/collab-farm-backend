import uuid
from pydantic import ConfigDict, Field, BaseModel
from datetime import datetime
from app.models.packageModel import TrancheType, PackageStatus

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