import uuid
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.package_model import (
    FarmerPackageStatus,
    PackageCategory,
    PackageStatus,
    PackageType,
)
from app.models.user_model import InvestorType



class WhatsIncludedItem(BaseModel):
    item: str = Field(..., description="Name of item/input, e.g. Fertilizer")
    amount: Optional[float] = Field(default=0.0, description="Cost or allocated amount in Naira")

    model_config = ConfigDict(from_attributes=True)


class PackageCreate(BaseModel):
    title: str
    package_type: PackageType
    category: PackageCategory
    fund_amount: float
    farming_cycle: str
    short_description: str
    tenure_months: int
    expected_payback_date: date
    expected_roi: float = Field(..., description="Percentage ROI e.g. 15.0")
    cooperative_share: float = Field(..., description="Cooperative cut % e.g. 5.0")
    whats_included: Optional[List[WhatsIncludedItem]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_fund_amount_by_type(self):
        min_amounts = {
            PackageType.STARTER: 100.00,
            PackageType.GROWTH: 300.0,
            PackageType.COMMERCIAL: 500.0,
        }
        min_required = min_amounts.get(self.package_type, 0.0)
        if self.fund_amount < min_required:
            raise ValueError(
                f"Fund amount for {self.package_type.value} must be at least ₦{min_required:,.2f}"
            )
        return self


class AssignFarmerSchema(BaseModel):
    farmer_ids: List[uuid.UUID] = Field(
        ...,
        min_length=1,
        description="List of farmer UUIDs to assign to this package",
    )


class PackageFarmerDetail(BaseModel):
    id: uuid.UUID
    package_id: uuid.UUID
    farmer_id: uuid.UUID
    name: str
    location: Optional[str] = None
    allocated_amount: float
    tenure_months: int
    expected_roi: float
    photo: Optional[str] = None
    progress_stage: Optional[str] = None
    progress_percentage: float = 0.0
    payout_date: Optional[date] = None
    payback_date: Optional[date] = None
    status: FarmerPackageStatus

    model_config = ConfigDict(from_attributes=True)


class PackageInvestorDetail(BaseModel):
    id: uuid.UUID
    investor_id: uuid.UUID
    investor_name: Optional[str] = None
    amount: float
    expected_settlement: float = 0.0
    invested_at: datetime = Field(..., alias="created_at")
    payback_due_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PackageFinancialSummary(BaseModel):
    total_money_invested: float
    total_disbursed_to_farmers: float
    remaining_balance: float


class PackageDetailRead(BaseModel):
    id: uuid.UUID
    cooperative_id: uuid.UUID
    cooperative_name: Optional[str] = None
    title: str
    package_type: PackageType
    category: PackageCategory
    farming_cycle: str
    short_description: str
    fund_amount: float
    tenure_months: int
    expected_payback_date: date
    expected_roi: float
    cooperative_share: float
    expected_settlement_amount: float = 0.0
    whats_included: List[WhatsIncludedItem] = []  # <-- Change from List[str] to List[WhatsIncludedItem]
    farmers_count: int = 0
    investors_count: int = 0
    status: PackageStatus
    financial_summary: PackageFinancialSummary
    assigned_farmers: List[PackageFarmerDetail] = []
    investors: List[PackageInvestorDetail] = []

    model_config = ConfigDict(from_attributes=True)


class PackageInvestorResponse(BaseModel):
    id: uuid.UUID
    investor_id: uuid.UUID
    investor_name: str
    email: EmailStr
    investor_type: Optional[InvestorType] = None
    amount: float
    invested_at: datetime
    payback_due_date: date

    model_config = ConfigDict(from_attributes=True)


class PackageRead(BaseModel):
    id: uuid.UUID
    cooperative_id: uuid.UUID
    cooperative_name: Optional[str] = None
    title: str
    package_type: PackageType
    category: PackageCategory
    fund_amount: float
    farming_cycle: str
    short_description: str
    tenure_months: int
    expected_payback_date: date
    expected_roi: float
    cooperative_share: float
    expected_settlement_amount: float = 0.0
    whats_included: List[WhatsIncludedItem] = []  # <-- Change from List[str] to List[WhatsIncludedItem]
    status: PackageStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedPackageResponse(BaseModel):
    items: List[PackageRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class PackageUpdate(BaseModel):
    title: Optional[str] = None
    package_type: Optional[PackageType] = None
    category: Optional[PackageCategory] = None
    fund_amount: Optional[float] = None
    farming_cycle: Optional[str] = None
    short_description: Optional[str] = None
    tenure_months: Optional[int] = None
    expected_payback_date: Optional[date] = None
    expected_roi: Optional[float] = None
    cooperative_share: Optional[float] = None
    status: Optional[PackageStatus] = None