import uuid
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Date, Enum as SQLEnum, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.farmer_model import Farmer
    from app.models.investment_model import Investment
    from app.models.user_model import User


class PackageType(str, Enum):
    STARTER = "STARTER"
    GROWTH = "GROWTH"
    COMMERCIAL = "COMMERCIAL"


class PackageCategory(str, Enum):
    CROP_FARMING = "CROP_FARMING"
    FISHERY = "FISHERY"
    MIXED_FARMING = "MIXED_FARMING"
    LIVESTOCK = "LIVESTOCK"
    POULTRY = "POULTRY"
    CUSTOM = "CUSTOM"


class PackageStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DISBURSED = "REPAID"
    COMPLETED = "OVERDUE"


class FarmerPackageStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DISBURSED = "REPAID"
    COMPLETED = "OVERDUE"


class Package(Base, TimestampMixin):
    __tablename__ = "packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cooperative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    package_type: Mapped[PackageType] = mapped_column(
        SQLEnum(PackageType, native_enum=False), nullable=False
    )
    category: Mapped[PackageCategory] = mapped_column(
        SQLEnum(PackageCategory, native_enum=False), nullable=False
    )

    fund_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    expected_payback_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_roi: Mapped[float] = mapped_column(Float, nullable=False)
    farming_cycle: Mapped[str] = mapped_column(String, nullable=False)
    short_description: Mapped[str] = mapped_column(String, nullable=False)
    cooperative_share: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[PackageStatus] = mapped_column(
        SQLEnum(PackageStatus, native_enum=False),
        default=PackageStatus.PENDING,
        nullable=False,
    )

    cooperative: Mapped["User"] = relationship(
        "User", foreign_keys=[cooperative_id]
    )
    package_farmers: Mapped[List["PackageFarmer"]] = relationship(
        "PackageFarmer", back_populates="package", cascade="all, delete-orphan"
    )
    investments: Mapped[List["Investment"]] = relationship(
        "Investment",
        back_populates="package",
        cascade="all, delete-orphan",
    )


class PackageFarmer(Base, TimestampMixin):
    __tablename__ = "package_farmers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packages.id", ondelete="CASCADE"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False
    )

    allocated_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), default=0.0, nullable=False
    )
    progress_percentage: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    payout_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    payback_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[FarmerPackageStatus] = mapped_column(
        SQLEnum(FarmerPackageStatus, native_enum=False),
        default=FarmerPackageStatus.PENDING,
        nullable=False,
    )

    package: Mapped["Package"] = relationship(
        "Package", back_populates="package_farmers"
    )
    farmer: Mapped["Farmer"] = relationship("Farmer")
