import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ComplaintCategory(str, enum.Enum):
    PACKAGE = "PACKAGE"
    INVESTMENT = "INVESTMENT"
    PAYMENT = "PAYMENT"
    DELIVERY = "DELIVERY"
    FARMER = "FARMER"
    OTHER = "OTHER"


class ComplaintStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


def _generate_complaint_reference() -> str:
    year = datetime.now(timezone.utc).year
    return f"CMP-{year}-{uuid.uuid4().hex[:6].upper()}"


class Complaint(Base, TimestampMixin):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    reference: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, default=_generate_complaint_reference
    )
    submitted_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
        index=True,
    )
    package_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.id", ondelete="SET NULL"), nullable=True,
        index=True,
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[ComplaintCategory] = mapped_column(
        SQLEnum(ComplaintCategory, native_enum=False), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[ComplaintStatus] = mapped_column(
        SQLEnum(ComplaintStatus, native_enum=False),
        nullable=False,
        default=ComplaintStatus.OPEN,
    )
    acknowledgment_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    assigned_reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    outcome: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    submitted_by = relationship("User", foreign_keys=[submitted_by_id])
    assigned_reviewer = relationship("User", foreign_keys=[assigned_reviewer_id])
    package = relationship("Package")
    messages = relationship(
        "ComplaintMessage", back_populates="complaint", cascade="all, delete-orphan"
    )
    actions = relationship(
        "ComplaintAction", back_populates="complaint", cascade="all, delete-orphan"
    )


class ComplaintMessage(Base):
    __tablename__ = "complaint_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    complaint = relationship("Complaint", back_populates="messages")
    author = relationship("User")


class ComplaintAction(Base):
    __tablename__ = "complaint_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    complaint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    complaint = relationship("Complaint", back_populates="actions")
    actor = relationship("User")
