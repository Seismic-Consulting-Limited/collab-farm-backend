import uuid
from fastapi_users import schemas
from app.db import InvestorType, VerificationStatus


class UserRead(schemas.BaseUser[uuid.UUID]):
    investor_type: InvestorType | None=None
    verification_status: VerificationStatus = VerificationStatus.NOT_SUBMITTED

    class Config:
        from_attributes = True


class UserCreate(schemas.BaseUserCreate):
    investor_type: InvestorType | None = None


class UserUpdate(schemas.BaseUserUpdate):
    investor_type: InvestorType | None = None
    verification_status: VerificationStatus | None = None
