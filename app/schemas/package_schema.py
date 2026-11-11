import uuid
from datetime import date, datetime
from typing import List, Optional
from math import isclose
from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    model_validator,
)

from app.models.package_model import (
    FarmerPackageStatus,
    PackageCategory,
    PackageCurrentStatus,
    PackageStatus,
    PackageType,
)
from app.models.user_model import InvestorType



class WhatsIncludedItem(BaseModel):
    item: str = Field(
        ...,
        description="Name of item/input, e.g. Fertilizer",
        validation_alias=AliasChoices("item", "name", "input"),
    )
    amount: Optional[float] = Field(default=0.0, description="Cost or allocated amount in Naira")

    model_config = ConfigDict(from_attributes=True)


class PackageFarmerAllocationCreate(BaseModel):
    farmer_id: uuid.UUID
    allocated_amount: float = Field(..., gt=0)


class FundingPlanTranche(BaseModel):
    tranche: str
    share_percentage: float
    amount: float
    description: str
    released_after: List[str]


class PackageCreate(BaseModel):
    title: str = Field(..., validation_alias=AliasChoices("title", "package_name"))
    package_type: PackageType
    category: PackageCategory
    fund_amount: float
    start_date: date
    end_date: date
    funding_closes_on: date
    minimum_funding_target: float = Field(..., gt=0)
    maximum_investment: float = Field(..., gt=0)
    minimum_investment: float = Field(..., gt=0)
    expected_output: str
    expected_return_min: float = Field(..., ge=0, le=100)
    expected_return_max: float = Field(..., ge=0, le=100)
    farming_cycle: Optional[str] = None
    short_description: str
    tenure_months: int
    expected_roi: float = Field(..., ge=0, description="Percentage ROI e.g. 15.0")
    cooperative_share: float = Field(..., ge=0, le=100, description="Cooperative cut percentage")
    whats_included: List[WhatsIncludedItem] = Field(
        ...,
        min_length=1,
        validation_alias=AliasChoices("whats_included", "whatsIncluded"),
    )
    farmers: List[PackageFarmerAllocationCreate] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_package_dates_and_amounts(self):
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if self.funding_closes_on >= self.start_date:
            raise ValueError("funding_closes_on must be before start_date")
        if self.minimum_investment > self.maximum_investment:
            raise ValueError("minimum_investment cannot exceed maximum_investment")
        if self.maximum_investment > self.fund_amount:
            raise ValueError("maximum_investment cannot exceed total package amount")
        if self.minimum_funding_target > self.fund_amount:
            raise ValueError("minimum_funding_target cannot exceed total package amount")
        if self.expected_return_min > self.expected_return_max:
            raise ValueError("expected_return_min cannot exceed expected_return_max")
        if len({f.farmer_id for f in self.farmers}) != len(self.farmers):
            raise ValueError("Each farmer can only be selected once")
        if not isclose(
            sum(f.allocated_amount for f in self.farmers),
            self.fund_amount,
            rel_tol=0,
            abs_tol=0.01,
        ):
            raise ValueError("Farmer allocations must add up to the total package amount")
        return self

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
    start_date: date
    end_date: date
    funding_closes_on: date
    minimum_funding_target: float
    maximum_investment: float
    minimum_investment: float
    expected_output: str
    expected_return_min: float
    expected_return_max: float
    funding_plan: List[FundingPlanTranche]
    tenure_months: int
    expected_payback_date: date
    expected_roi: float
    cooperative_share: float
    expected_settlement_amount: float = 0.0
    whats_included: List[WhatsIncludedItem] = Field(default_factory=list)
    farmers_count: int = 0
    investors_count: int = 0
    current_status: PackageCurrentStatus
    status: PackageStatus
    financial_summary: PackageFinancialSummary
    farmers: List[PackageFarmerDetail] = Field(default_factory=list)
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
    start_date: date
    end_date: date
    funding_closes_on: date
    minimum_funding_target: float
    maximum_investment: float
    minimum_investment: float
    expected_output: str
    expected_return_min: float
    expected_return_max: float
    funding_plan: List[FundingPlanTranche]
    farming_cycle: str
    short_description: str
    tenure_months: int
    expected_payback_date: date
    expected_roi: float
    cooperative_share: float
    expected_settlement_amount: float = 0.0
    farmers_count: int = 0
    investors_count: int = 0
    current_status: PackageCurrentStatus
    whats_included: List[WhatsIncludedItem] = Field(default_factory=list)
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
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    funding_closes_on: Optional[date] = None
    minimum_funding_target: Optional[float] = None
    maximum_investment: Optional[float] = None
    minimum_investment: Optional[float] = None
    expected_output: Optional[str] = None
    expected_return_min: Optional[float] = None
    expected_return_max: Optional[float] = None
    farming_cycle: Optional[str] = None
    short_description: Optional[str] = None
    tenure_months: Optional[int] = None
    expected_payback_date: Optional[date] = None
    expected_roi: Optional[float] = None
    cooperative_share: Optional[float] = None
    whats_included: Optional[List[WhatsIncludedItem]] = Field(
        default=None,
        validation_alias=AliasChoices("whats_included", "whatsIncluded"),
    )
    status: Optional[PackageStatus] = None
