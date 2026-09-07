import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional, Any, List
from sqlalchemy import Enum as SQLEnum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin
from app.schemas.applicationSchema import ApplicationStatus

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
        Numeric(12, 2), nullable=False)
    target_farmer_ids: Mapped[List[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False
    )
    disbursement_plan: Mapped[Any] = mapped_column(JSONB, nullable=False)

    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False),
        default=ApplicationStatus.PENDING_ADMIN,
        nullable=False,
    )
    rejection_reason: Mapped[Optional[str]
                             ] = mapped_column(String, nullable=True)
    revision_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    package: Mapped["InvestmentPackage"] = relationship("InvestmentPackage")
    cooperative: Mapped["User"] = relationship("User")
