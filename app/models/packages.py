# app/models/package.py
from enum import Enum
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
if TYPE_CHECKING:
    from app.models.user import User


class TrancheType(str, Enum):
    SINGLE_TRANCHE = "single_tranche"
    MULTI_TRANCHE = "multi_tranche"


class PackageStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    REJECTED = "rejected"
    COMPLETED = "completed"


class InvestmentPackage(Base, TimestampMixin):
    __tablename__ = "investment_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    total_fund_amount: Mapped[float] = mapped_column(nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_roi: Mapped[float] = mapped_column(nullable=False)

    tranche_type: Mapped[TrancheType] = mapped_column(
        SQLEnum(TrancheType, native_enum=False),
        default=TrancheType.SINGLE_TRANCHE,
        nullable=False,
    )
    status: Mapped[PackageStatus] = mapped_column(
        SQLEnum(PackageStatus, native_enum=False),
        default=PackageStatus.PENDING,
        nullable=False,
    )
    rejection_reason: Mapped[Optional[str]
                             ] = mapped_column(String, nullable=True)

    creator: Mapped["User"] = relationship("User")
