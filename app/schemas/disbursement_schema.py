import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

from app.models.disbursement_model import DisbursementStatus
from app.models.package_model import PackageCategory, PackageType


class DisbursementMetrics(BaseModel):
    total_disbursed: float
    total_disbursed_change_pct: float = 12.0
    pending_disbursement: float
    pending_count: int
    this_month_disbursed: float
    this_month_change_pct: float = 18.0
    total_disbursements_count: int


class DisbursementFarmerSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    farmer_code: Optional[str] = None
    photo_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DisbursementPackageSummary(BaseModel):
    id: uuid.UUID
    title: str
    category: PackageCategory
    package_type: Optional[PackageType] = None

    model_config = ConfigDict(from_attributes=True)


class DisbursementListItem(BaseModel):
    id: uuid.UUID
    farmer: DisbursementFarmerSummary
    package: DisbursementPackageSummary
    amount_disbursed: float
    disbursement_date: datetime
    status: DisbursementStatus

    model_config = ConfigDict(from_attributes=True)


class PaginatedDisbursementResponse(BaseModel):
    metrics: DisbursementMetrics
    items: List[DisbursementListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class DisbursementDetailResponse(BaseModel):
    id: uuid.UUID
    farmer_id_code: str
    farmer_name: str
    photo_url: Optional[str] = None
    status: DisbursementStatus
    amount_disbursed: float
    disbursed_at: Optional[datetime] = None
    recorded_by: Optional[str] = None
    transaction_reference: Optional[str] = None
    package_title: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)