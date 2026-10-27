import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import DateTime, Enum as SQLEnum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


def _generate_loan_code() -> str:
    return f"FL-{uuid.uuid4().hex.upper()}"


class DisbursementStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    DISBURSED = "DISBURSED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


if TYPE_CHECKING:
    from app.models.package_model import Package
    from app.models.user_model import User
    from app.models.farmer_model import Farmer


class Disbursement(Base, TimestampMixin):
    __tablename__ = "disbursements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    loan_code: Mapped[str] = mapped_column(
        String(40), unique=True, nullable=False, default=_generate_loan_code
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False
    )
    cooperative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False
    )
    recorded_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    disbursement_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    transaction_reference: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    status: Mapped[DisbursementStatus] = mapped_column(
        SQLEnum(DisbursementStatus, native_enum=False),
        default=DisbursementStatus.PENDING,
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    package: Mapped["Package"] = relationship(
        "Package", back_populates="disbursements"
    )
    cooperative: Mapped["User"] = relationship(
        "User", foreign_keys=[cooperative_id]
    )
    farmer: Mapped["Farmer"] = relationship(
        "Farmer", foreign_keys=[farmer_id]
    )
    recorded_by: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[recorded_by_id]
    )
