import uuid
from pydantic import ConfigDict, BaseModel, EmailStr, Field
from fastapi_users import schemas
from app.models.userModel import InvestorType, VerificationStatus

class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType | None = None
    # i changed the verification status to approved for testing purposes
    verification_status: VerificationStatus = VerificationStatus.NOT_SUBMITTED

    model_config = ConfigDict(from_attributes=True)


class UserCreate(schemas.BaseUserCreate):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType = InvestorType.INDIVIDUAL


class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus | None = None

class ForgotPasswordSchema(BaseModel):
    email: EmailStr

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, description="Enter New Password")
