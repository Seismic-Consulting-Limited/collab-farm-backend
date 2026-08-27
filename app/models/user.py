# app/models/user.py
from enum import Enum
import uuid
from typing import TYPE_CHECKING, Optional
from fastapi_users.db import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
)
from sqlalchemy import Enum as SQLEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
if TYPE_CHECKING:
    from app.models.profile import GroupProfile, IndividualProfile


class InvestorType(str, Enum):
    INDIVIDUAL = "individual"
    GROUP = "group_investment"

class VerificationStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    __tablename__ = "oauth_account"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )


class User(SQLAlchemyBaseUserTableUUID, Base, TimestampMixin):
    __tablename__ = "users"

    first_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True)

    investor_type: Mapped[Optional[InvestorType]] = mapped_column(
        SQLEnum(InvestorType, native_enum=False), nullable=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus, native_enum=False),
        default=VerificationStatus.NOT_SUBMITTED,
        nullable=False,
    )

    individual_profile: Mapped[Optional["IndividualProfile"]] = relationship(
        "IndividualProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    group_profile: Mapped[Optional["GroupProfile"]] = relationship(
        "GroupProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined", cascade="all, delete-orphan"
    )
