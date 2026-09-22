import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional
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


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    size_in_hectares: Optional[float] = Field(None, gt=0)
    farming_category: Optional[str] = None
    status: Optional[FarmStatus] = None


class FarmStatusUpdate(BaseModel):
    status: FarmStatus


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

    model_config = ConfigDict(from_attributes=True)


FarmResponse = FarmRead


class FarmerCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    nin: str = Field(...,
                     description="11-digit National Identification Number")
    phone_number: str
    gender: Gender
    additional_info: Optional[str] = None
    wrs_status: WRSStatus = WRSStatus.NOT_VERIFIED
    farms: list[FarmCreate] = []

    @field_validator("nin")
    @classmethod
    def validate_nin(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 11:
            raise ValueError("NIN must consist of exactly 11 digits.")
        return v


class FarmerUpdate(BaseModel):
    full_name: Optional[str] = None
    nin: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    additional_info: Optional[str] = None
    wrs_status: Optional[WRSStatus] = None

    @field_validator("nin")
    @classmethod
    def validate_nin(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and (not v.isdigit() or len(v) != 11):
            raise ValueError("NIN must consist of exactly 11 digits.")
        return v


class FarmerRead(BaseModel):
    id: uuid.UUID
    cooperative_id: uuid.UUID
    full_name: str
    nin: str
    phone_number: str
    gender: Gender
    photo: Optional[str] = None
    additional_info: Optional[str] = None
    wrs_status: WRSStatus
    cooperative: Optional[CooperativeSummary] = None
    farms: list[FarmRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedFarmerResponse(BaseModel):
    items: list[FarmerRead]
    total: int
    page: int
    page_size: int
    total_pages: int
