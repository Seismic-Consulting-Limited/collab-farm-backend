import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, Enum as SQLEnum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class InvestmentStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REPAID = "repaid"
    OVERDUE = "overdue"


class Investment(Base):
    __tablename__ = "investments"
    __table_args__ = {"extend_existing": True}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    package_id = Column(
        UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False
    )

    amount = Column(Float, nullable=False)
    expected_farmer_payout = Column(Float, nullable=False, default=0.0)

    status = Column(
        SQLEnum(InvestmentStatus, name="investment_status_enum"),
        default=InvestmentStatus.PENDING,
        nullable=False,
    )

    payment_method = Column(String, nullable=True)
    transaction_reference = Column(
        String, nullable=True, unique=True, index=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    investor = relationship("User", back_populates="investments")
    package = relationship("Package", back_populates="investments")
