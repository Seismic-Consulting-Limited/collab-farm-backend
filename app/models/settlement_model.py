import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import String, Numeric, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SettlementStatus(str, enum.Enum):
    ONGOING = "ONGOING"
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    REJECTED = "REJECTED"
    DISBURSED = "DISBURSED"
    OVERDUE = "OVERDUE"
    SETTLED = "SETTLED"


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("packages.id", ondelete="CASCADE"), nullable=False
    )
    disbursement_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("disbursements.id", ondelete="SET NULL"), nullable=True
    )
    recorded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    returned_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    receipt_verified_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    amount_settled: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[SettlementStatus] = mapped_column(
        SQLEnum(SettlementStatus, native_enum=False),
        default=SettlementStatus.ONGOING,
        nullable=False,
    )

    return_reported_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    return_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    date_settled: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    farmer = relationship("Farmer")
    package = relationship("Package")
    disbursement = relationship("Disbursement")
    recorded_by = relationship("User", foreign_keys=[recorded_by_id])
    returned_by = relationship("User", foreign_keys=[returned_by_id])
    receipt_verified_by = relationship("User", foreign_keys=[receipt_verified_by_id])
