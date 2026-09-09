import enum
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum as SQLEnum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class TrancheType(str, enum.Enum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"


class PackageStatus(str, enum.Enum):
    PENDING_ADMIN_REVIEW = "PENDING_ADMIN_REVIEW"
    PENDING_INVESTOR_CONFIRMATION = "PENDING_INVESTOR_CONFIRMATION"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"


if TYPE_CHECKING:
    from app.models.userModel import User


class InvestmentPackage(Base, TimestampMixin):
    __tablename__ = "investment_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    total_fund_amount: Mapped[float] = mapped_column(Float, nullable=False)
    tenure: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_roi: Mapped[float] = mapped_column(Float, nullable=False)

    tranche_type: Mapped[TrancheType] = mapped_column(
        SQLEnum(TrancheType, native_enum=False),
        default=TrancheType.SINGLE,
        nullable=False,
    )
    status: Mapped[PackageStatus] = mapped_column(
        SQLEnum(PackageStatus, native_enum=False),
        default=PackageStatus.PENDING_ADMIN_REVIEW,
        nullable=False,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    creator: Mapped["User"] = relationship("User")