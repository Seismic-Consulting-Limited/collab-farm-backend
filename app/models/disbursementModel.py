import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional
from sqlalchemy import Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class DisbursementStatus(str, Enum):
    PENDING = "PENDING"
    MILESTONE_SUBMITTED = "MILESTONE_SUBMITTED"
    DISBURSED = "DISBURSED"
    FAILED = "FAILED"


class DisbursementSchedule(Base, TimestampMixin):
    __tablename__ = "disbursement_schedules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("funding_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    tranche_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    milestone_description: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[DisbursementStatus] = mapped_column(
        SQLEnum(DisbursementStatus, native_enum=False),
        default=DisbursementStatus.PENDING,
        nullable=False
    )

    milestone_proof_url: Mapped[Optional[str]
                                ] = mapped_column(String(500), nullable=True)
    transaction_reference: Mapped[Optional[str]
                                  ] = mapped_column(String(100), nullable=True)
    disbursed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True)

    # Relationships
    application = relationship(
        "FundingApplication", back_populates="disbursements")
