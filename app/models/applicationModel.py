import enum
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import Enum as SQLEnum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class ApplicationStatus(str, enum.Enum):
    PENDING_ADMIN_REVIEW = "PENDING_ADMIN_REVIEW"
    PENDING_INVESTOR_REVIEW = "PENDING_INVESTOR_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class TrancheType(str, enum.Enum):
    SINGLE = "SINGLE"
    MULTI = "MULTI"


if TYPE_CHECKING:
    from app.models.packageModel import InvestmentPackage
    from app.models.userModel import User


class FundingApplication(Base, TimestampMixin):
    __tablename__ = "funding_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("investment_packages.id", ondelete="CASCADE"), nullable=False
    )
    cooperative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    requested_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    tranche_type: Mapped[TrancheType] = mapped_column(
        SQLEnum(TrancheType, native_enum=False),
        default=TrancheType.SINGLE,
        nullable=False,
    )
    target_farmer_ids: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )
    disbursement_plan: Mapped[Optional[Any]
                              ] = mapped_column(JSONB, nullable=True)

    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False),
        default=ApplicationStatus.PENDING_ADMIN_REVIEW,
        nullable=False,
    )
    rejection_reason: Mapped[Optional[str]
                             ] = mapped_column(String, nullable=True)
    revision_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    package: Mapped["InvestmentPackage"] = relationship("InvestmentPackage")
    cooperative: Mapped["User"] = relationship("User")

    @property
    def target_farmers_count(self) -> int:
        return len(self.target_farmer_ids) if self.target_farmer_ids else 0
