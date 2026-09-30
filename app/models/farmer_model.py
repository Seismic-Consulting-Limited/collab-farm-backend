import enum
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Enum as SQLEnum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class WRSStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"


class FarmStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


if TYPE_CHECKING:
    from app.models.user_model import User


class Farmer(Base, TimestampMixin):
    __tablename__ = "farmers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cooperative_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    full_name: Mapped[str] = mapped_column(String, nullable=False)
    nin: Mapped[str] = mapped_column(String(11), nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    gender: Mapped[Gender] = mapped_column(
        SQLEnum(Gender, native_enum=False), nullable=False
    )
    farming_category: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True)
    photo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    additional_info: Mapped[Optional[str]
                            ] = mapped_column(String, nullable=True)

    wrs_status: Mapped[WRSStatus] = mapped_column(
        SQLEnum(WRSStatus, native_enum=False),
        default=WRSStatus.NOT_VERIFIED,
        nullable=False,
    )

    cooperative: Mapped["User"] = relationship(
        "User", back_populates="farmers"
    )
    farms: Mapped[List["Farm"]] = relationship(
        "Farm", back_populates="farmer", cascade="all, delete-orphan"
    )

    # --- Formatting & Aliases ---
    @hybrid_property
    def date_added(self) -> Optional[str]:
        """Returns created_at formatted as MM/DD/YYYY, HH:MM AM/PM"""
        if getattr(self, "created_at", None):
            return self.created_at.strftime("%m/%d/%Y, %I:%M %p")
        return None

    @hybrid_property
    def formatted_created_at(self) -> Optional[str]:
        """Returns created_at formatted as MM/DD/YYYY, HH:MM AM/PM"""
        if getattr(self, "created_at", None):
            return self.created_at.strftime("%m/%d/%Y, %I:%M %p")
        return None

    @hybrid_property
    def formatted_updated_at(self) -> Optional[str]:
        """Returns updated_at formatted as MM/DD/YYYY, HH:MM AM/PM"""
        if getattr(self, "updated_at", None):
            return self.updated_at.strftime("%m/%d/%Y, %I:%M %p")
        return None


class Farm(Base, TimestampMixin):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    size_in_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    farming_category: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[FarmStatus] = mapped_column(
        SQLEnum(FarmStatus, native_enum=False),
        default=FarmStatus.ACTIVE,
        nullable=False,
    )

    farmer: Mapped["Farmer"] = relationship("Farmer", back_populates="farms")

    # --- Formatting Helpers ---
    @hybrid_property
    def date_added(self) -> Optional[str]:
        """Returns created_at formatted as MM/DD/YYYY, HH:MM AM/PM"""
        if getattr(self, "created_at", None):
            return self.created_at.strftime("%m/%d/%Y, %I:%M %p")
        return None

    @hybrid_property
    def formatted_created_at(self) -> Optional[str]:
        """Returns created_at formatted as MM/DD/YYYY, HH:MM AM/PM"""
        if getattr(self, "created_at", None):
            return self.created_at.strftime("%m/%d/%Y, %I:%M %p")
        return None

    @hybrid_property
    def formatted_updated_at(self) -> Optional[str]:
        """Returns updated_at formatted as MM/DD/YYYY, HH:MM AM/PM"""
        if getattr(self, "updated_at", None):
            return self.updated_at.strftime("%m/%d/%Y, %I:%M %p")
        return None
