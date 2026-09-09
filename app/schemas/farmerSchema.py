import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class WRSStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"


class CooperativeSummary(BaseModel):
    id: uuid.UUID
    email: str
    cooperative_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def extract_cooperative_name(cls, data: any) -> any:
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


class FarmerCreate(BaseModel):
    full_name: str = Field(..., min_length=2)
    nin: str = Field(...,
                     description="11-digit National Identification Number")
    crop_type: str
    phone_number: str
    gender: Gender
    farm_size_acres: float = Field(..., gt=0)
    farm_address: str
    additional_info: Optional[str] = None
    wrs_status: WRSStatus = WRSStatus.NOT_VERIFIED

    @field_validator("nin")
    @classmethod
    def validate_nin(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 11:
            raise ValueError("NIN must consist of exactly 11 digits.")
        return v


class FarmerUpdate(BaseModel):
    full_name: Optional[str] = None
    nin: Optional[str] = None
    crop_type: Optional[str] = None
    phone_number: Optional[str] = None
    gender: Optional[Gender] = None
    farm_size_acres: Optional[float] = Field(None, gt=0)
    farm_address: Optional[str] = None
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
    crop_type: str
    phone_number: str
    gender: Gender
    farm_size_acres: float
    farm_address: str
    photo: str
    additional_info: Optional[str] = None
    wrs_status: WRSStatus
    cooperative: Optional[CooperativeSummary] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedFarmerResponse(BaseModel):
    items: list[FarmerRead]
    total: int
    page: int
    page_size: int
    total_pages: int
