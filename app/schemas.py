import uuid
from pydantic import ConfigDict
from fastapi_users import schemas
from app.db import InvestorType, VerificationStatus


class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus = VerificationStatus.NOT_SUBMITTED

    model_config = ConfigDict(from_attributes=True)


class UserCreate(schemas.BaseUserCreate):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType | None = None


class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus | None = None
