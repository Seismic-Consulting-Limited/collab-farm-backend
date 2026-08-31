import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Numeric, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class TransactionType(str, enum.Enum):
    DEPOSIT = "Deposit"
    ALLOCATION = "Allocation"
    DISBURSEMENT = "Disbursement"
    RETURN = "Return"
    WITHDRAWAL = "Withdrawal"


class TransactionStatus(str, enum.Enum):
    PENDING = "Pending"
    COMPLETED = "Completed"
    ACTIVE = "Active"
    FAILED = "Failed"


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(
        "users.id", ondelete="CASCADE"), unique=True, nullable=False)

    available_balance: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0.00, nullable=False)
    locked_funds: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0.00, nullable=False)
    actively_distributed: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0.00, nullable=False)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="wallet", cascade="all, delete-orphan")
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="wallet", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    wallet_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("wallets.id", ondelete="CASCADE"), nullable=False)

    reference: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)

    type: Mapped[TransactionType] = mapped_column(
        SQLEnum(TransactionType, native_enum=False),
        nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        SQLEnum(TransactionStatus, native_enum=False),
        default=TransactionStatus.PENDING,
        nullable=False
    )

    wallet: Mapped["Wallet"] = relationship(
        "Wallet", back_populates="transactions")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
