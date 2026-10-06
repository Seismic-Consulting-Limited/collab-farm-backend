import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class WRSStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"

class FarmStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


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
    size_in_hectares: float = Field(..., gt=0,
                                    description="Size of farm in hectares")
    farming_category: str = Field(...,
                                  description="e.g. Crop Farming, Livestock, Mixed")
    status: FarmStatus = FarmStatus.ACTIVE

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    size_in_hectares: Optional[float] = Field(None, gt=0)
    farming_category: Optional[str] = None
    status: Optional[FarmStatus] = None

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
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
    farming_category: str
    status: FarmStatus
    created_at: datetime
    updated_at: datetime
    date_added: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


FarmResponse = FarmRead


class FarmerCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    nin: str = Field(...,
                     description="11-digit National Identification Number")
    phone_number: str
    gender: Gender
    farming_category: Optional[str] = Field(
        None, description="e.g. Crop Farming, Livestock, Mixed")
    wrs_status: WRSStatus = WRSStatus.NOT_VERIFIED
    additional_info: Optional[str] = None
    farms: Optional[list[FarmCreate]] = Field(default_factory=list)

    @field_validator("nin")
    @classmethod
    def validate_nin(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 11:
            raise ValueError("NIN must consist of exactly 11 digits.")
        return v

    @field_validator("farms", mode="before")
    @classmethod
    def handle_none_farms(cls, value: Any) -> Any:
        if value is None:
            return []
        return value

    @field_validator("gender", "wrs_status", mode="before")
    @classmethod
    def normalize_farmer_enums(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class FarmerUpdate(BaseModel):
    full_name: Optional[str] = None
    nin: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    farming_category: Optional[str] = None
    additional_info: Optional[str] = None
    wrs_status: Optional[WRSStatus] = None

    @field_validator("nin")
    @classmethod
    def validate_nin(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v.isdigit() or len(v) != 11):
            raise ValueError("NIN must consist of exactly 11 digits.")
        return v

    @field_validator("gender", "wrs_status", mode="before")
    @classmethod
    def normalize_farmer_enums(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class FarmerRead(BaseModel):
    id: uuid.UUID
    cooperative_id: uuid.UUID
    full_name: str
    nin: str
    phone_number: str
    gender: Gender
    farming_category: Optional[str] = None
    photo: Optional[str] = None
    additional_info: Optional[str] = None
    wrs_status: WRSStatus
    cooperative: Optional[CooperativeSummary] = None
    farms: list[FarmRead] = Field(default_factory=list)
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
    crop_type: Optional[str] = Field(default="No Farms")
    phone_number: str
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
