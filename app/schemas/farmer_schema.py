import uuid
from datetime import date, datetime
from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"

# Warehouse Receipt System(WRS)
class WRSStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"


class FarmStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class FarmingCategory(str, Enum):
    CROP_FARMING = "crop_farming"
    FISHERY = "fishery"
    MIXED_FARMING = "mixed_farming"
    POULTRY = "poultry"
    LIVESTOCK = "livestock"
    OTHERS = "others"


class CooperativeSummary(BaseModel):
    id: uuid.UUID
    email: str
    cooperative_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_cooperative_name(cls, data: Any) -> Any:
        if hasattr(data, "cooperative_profile") and data.cooperative_profile:
            return {
                "id": data.id,
                "email": data.email,
                "cooperative_name": data.cooperative_profile.cooperative_name,
            }
        if isinstance(data, dict):
            return data
        return {
            "id": getattr(data, "id", None),
            "email": getattr(data, "email", None),
            "cooperative_name": None,
        }


class FarmCreate(BaseModel):
    name: str = Field(..., min_length=2, description="Name of the farm")
    location: str = Field(..., description="Location of the farm")
    size_in_hectares: float = Field(..., gt=0, description="Size of farm in hectares")
    farming_category: Optional[FarmingCategory] = Field(
        None,
        description="Farming category: crop_farming, fishery, mixed_farming, poultry",
    )
    status: FarmStatus = FarmStatus.ACTIVE

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("farming_category", mode="before")
    @classmethod
    def normalize_category(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower().replace(" ", "_")
        return value


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    size_in_hectares: Optional[float] = Field(None, gt=0)
    farming_category: Optional[FarmingCategory] = None
    status: Optional[FarmStatus] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("farming_category", mode="before")
    @classmethod
    def normalize_category(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower().replace(" ", "_")
        return value


class FarmStatusUpdate(BaseModel):
    status: FarmStatus

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class FarmRead(BaseModel):
    id: uuid.UUID
    farmer_id: uuid.UUID
    name: str
    location: str
    size_in_hectares: float
    farming_category: Optional[FarmingCategory] = None
    status: FarmStatus
    created_at: datetime
    updated_at: datetime
    date_added: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


FarmResponse = FarmRead


class FarmerInvestmentStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    DISBURSED = "DISBURSED"
    REPAID = "REPAID"
    OVERDUE = "OVERDUE"


class FarmerInvestmentRead(BaseModel):
    loan_id: str
    package_id: uuid.UUID
    package_title: str
    loan_amount: float
    repayment_amount: float
    loan_date: Optional[datetime] = None
    due_date: date
    status: FarmerInvestmentStatus


class FarmerCreate(BaseModel):
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    date_of_birth: date
    email: EmailStr
    nin: str = Field(..., description="11-digit National Identification Number")
    phone_number: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    bank_name: Optional[str] = None
    gender: Gender
    farming_category: FarmingCategory = Field(..., description="Primary farming category")
    years_of_experience: int = Field(..., ge=0)
    terms_accepted: bool
    wrs_status: WRSStatus = WRSStatus.VERIFIED
    additional_info: Optional[str] = None

    @field_validator("nin")
    @classmethod
    def validate_nin(cls, v: str) -> str:
        if not (v.isascii() and v.isdigit() and len(v) == 11):
            raise ValueError("NIN must consist of exactly 11 digits.")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date) -> date:
        if value >= date.today():
            raise ValueError("Date of birth must be in the past")
        return value

    @field_validator("terms_accepted")
    @classmethod
    def require_terms_acceptance(cls, value: bool) -> bool:
        if not value:
            raise ValueError("The farmer must accept the agreement terms")
        return value

    @field_validator("gender", "wrs_status", mode="before")
    @classmethod
    def normalize_farmer_enums(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("farming_category", mode="before")
    @classmethod
    def normalize_category(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower().replace(" ", "_")
        return value


class FarmerUpdate(BaseModel):
    full_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    nin: Optional[str] = None
    phone_number: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    bank_name: Optional[str] = None
    gender: Optional[Gender] = None
    farming_category: Optional[FarmingCategory] = None
    years_of_experience: Optional[int] = Field(None, ge=0)
    additional_info: Optional[str] = None
    wrs_status: Optional[WRSStatus] = None

    @field_validator("nin")
    @classmethod
    def validate_nin(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not (v.isascii() and v.isdigit() and len(v) == 11):
            raise ValueError("NIN must consist of exactly 11 digits.")
        return v

    @field_validator("gender", "wrs_status", mode="before")
    @classmethod
    def normalize_farmer_enums(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value

    @field_validator("farming_category", mode="before")
    @classmethod
    def normalize_category(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower().replace(" ", "_")
        return value


class FarmerActivityRead(BaseModel):
    activity_type: str
    description: str
    occurred_at: datetime
    status: Optional[str] = None
    amount: Optional[float] = None


class FarmerRead(BaseModel):
    id: uuid.UUID
    cooperative_id: uuid.UUID
    full_name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    email: Optional[EmailStr] = None
    nin: str
    phone_number: Optional[str] = None
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    bank_name: Optional[str] = None
    gender: Gender
    farming_category: Optional[FarmingCategory] = None
    photo: Optional[str] = None
    id_photo: Optional[str] = None
    years_of_experience: int = 0
    terms_accepted: bool = False
    additional_info: Optional[str] = None
    wrs_status: WRSStatus
    cooperative: Optional[CooperativeSummary] = None
    farms: list[FarmRead] = Field(default_factory=list)
    farmer_investments: list[FarmerInvestmentRead] = Field(default_factory=list)
    recent_activities: list[FarmerActivityRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    date_added: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedFarmerResponse(BaseModel):
    items: list[FarmerRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class FarmerDirectoryMetrics(BaseModel):
    total_farmers: int
    verified_farmers: int
    pending_verification: int
    removed_farmers: int = 0


class FarmerDirectoryItem(BaseModel):
    id: uuid.UUID
    full_name: str
    photo: Optional[str] = None
    farming_category: Optional[str] = Field(default="No Farms")
    phone_number: Optional[str] = None
    date_added: Optional[Union[str, datetime]] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class FarmerDirectoryResponse(BaseModel):
    metrics: FarmerDirectoryMetrics
    items: list[FarmerDirectoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int
