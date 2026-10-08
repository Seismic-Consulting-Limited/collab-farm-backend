import uuid
from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.user_model import InvestorType, UserRole, VerificationStatus


class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    role: UserRole
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus = VerificationStatus.NOT_SUBMITTED

    model_config = ConfigDict(from_attributes=True)


class UserCreate(schemas.BaseUserCreate):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    role: UserRole
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus = VerificationStatus.NOT_SUBMITTED
    confirm_password: str = Field(..., description="Confirm Password")

    @model_validator(mode="after")
    def validate_user_create(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")

        if self.role == UserRole.ADMIN:
            self.verification_status = VerificationStatus.APPROVED
        else:
            self.verification_status = VerificationStatus.NOT_SUBMITTED

        if self.role != UserRole.INVESTOR:
            self.investor_type = None

        return self

    def create_update_dict(self):
        data = super().create_update_dict()
        data.pop("confirm_password", None)
        return data

    def create_update_dict_superuser(self):
        data = super().create_update_dict_superuser()
        data.pop("confirm_password", None)
        return data


class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    role: UserRole | None = None
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus | None = None

    @model_validator(mode="after")
    def validate_investor_type(self):
        if self.role is not None and self.role != UserRole.INVESTOR:
            self.investor_type = None
        return self


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str = Field(
        ..., min_length=8, description="Enter New Password"
    )
    confirm_password: str = Field(
        ..., min_length=8, description="Confirm New Password"
    )

    @model_validator(mode="after")
    def validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match.")
        return self


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(
        ..., min_length=8, description="Enter New Password"
    )
    confirm_password: str = Field(
        ..., min_length=8, description="Confirm New Password"
    )

    @model_validator(mode="after")
    def validate_passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match.")
        return self


class VerifyOTPSchema(BaseModel):
    email: EmailStr
    otp: str