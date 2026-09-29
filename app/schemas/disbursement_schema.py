import uuid
from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict
from app.models.package_model import PackageCategory, PackageStatus


class DisbursementMetrics(BaseModel):
    total_disbursed: float
    total_disbursed_change_pct: float = 12.0
    pending_disbursement: float
    pending_count: int
    this_month_disbursed: float
    this_month_change_pct: float = 18.0
    total_disbursements_count: int


class DisbursementListItem(BaseModel):
    id: uuid.UUID
    package_name: str
    category: PackageCategory
    investors_count: int
    farmers_count: int
    amount: float
    date_invested: datetime
    status: PackageStatus

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
    package_name: str
    package_code: str
    category: PackageCategory
    crop_type: str
    total_package_amount: float
    currently_disbursed: float
    remaining_to_disburse: float
    investors_count: int
    farmers_count: int
    status: PackageStatus