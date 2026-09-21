import uuid
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, ConfigDict, EmailStr
from app.schemas.user_schema import UserRole, InvestorType, VerificationStatus


class IndividualProfileBase(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str
    id_number: str
    id_file: str
    nationality: str


class IndividualProfileCreate(IndividualProfileBase):
    pass


class IndividualProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    id_number: Optional[str] = None
    id_file: Optional[str] = None
    nationality: Optional[str] = None


class IndividualProfileRead(IndividualProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupProfileBase(BaseModel):
    company_name: str
    company_address: str
    email: EmailStr
    phone_number: str
    year_established: int
    company_registration_number: str
    company_registration_file: str
    proof_of_address_file: str


class GroupProfileCreate(GroupProfileBase):
    pass


class GroupProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    company_address: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    year_established: Optional[int] = None
    company_registration_number: Optional[str] = None
    company_registration_file: Optional[str] = None
    proof_of_address_file: Optional[str] = None


class GroupProfileRead(GroupProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CooperativeProfileBase(BaseModel):
    cooperative_name: str
    year_established: int
    registration_number: str
    email: EmailStr
    address: str
    lga: str
    state: str
    registration_certificate_file: str
    proof_of_address_file: str


class CooperativeProfileCreate(CooperativeProfileBase):
    pass


class CooperativeProfileUpdate(BaseModel):
    cooperative_name: Optional[str] = None
    year_established: Optional[int] = None
    registration_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    lga: Optional[str] = None
    state: Optional[str] = None
    registration_certificate_file: Optional[str] = None
    proof_of_address_file: Optional[str] = None


class CooperativeProfileRead(CooperativeProfileBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserProfile(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: UserRole
    investor_type: Optional[InvestorType]
    verification_status: VerificationStatus
    profile: Optional[Union[IndividualProfileRead, GroupProfileRead, CooperativeProfileRead]] = None
    model_config = ConfigDict(from_attributes=True)
