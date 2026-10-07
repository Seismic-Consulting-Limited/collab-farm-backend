import enum
import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Float, ForeignKey, String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from app.models.base import Base, TimestampMixin


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class WRSStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"


class FarmStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class FarmingCategory(str, enum.Enum):
    CROP_FARMING = "crop_farming"
    FISHERY = "fishery"
    MIXED_FARMING = "mixed_farming"
    POULTRY = "poultry"


class FlexibleEnum(TypeDecorator):
    """
    Stores Enum values in the DB as VARCHAR and reads them back case-insensitively.
    Prevents LookupError when DB rows contain mixed casing (e.g., 'Fishery' vs 'fishery').
    """
    impl = String
    cache_ok = True

    def __init__(self, enum_cls: type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_cls = enum_cls

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_cls):
            return value.value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        
        val_str = str(value).strip()
        # 1. Match against Enum values (case-insensitive)
        for item in self.enum_cls:
            if item.value.lower() == val_str.lower():
                return item

        # 2. Match against Enum keys/names (case-insensitive)
        for item in self.enum_cls:
            if item.name.lower() == val_str.lower():
                return item

        # 3. Fallback attempt
        try:
            return self.enum_cls(val_str)
        except ValueError:
            return None


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
        FlexibleEnum(Gender), nullable=False
    )
    farming_category: Mapped[Optional[FarmingCategory]] = mapped_column(
        FlexibleEnum(FarmingCategory), nullable=True
    )
    photo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    additional_info: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    wrs_status: Mapped[WRSStatus] = mapped_column(
        FlexibleEnum(WRSStatus),
        default=WRSStatus.NOT_VERIFIED,
        nullable=False,
    )

    cooperative: Mapped["User"] = relationship("User", back_populates="farmers")
    farms: Mapped[List["Farm"]] = relationship(
        "Farm", back_populates="farmer", cascade="all, delete-orphan"
    )

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
    farming_category: Mapped[FarmingCategory] = mapped_column(
        FlexibleEnum(FarmingCategory), nullable=False
    )
    status: Mapped[FarmStatus] = mapped_column(
        FlexibleEnum(FarmStatus),
        default=FarmStatus.ACTIVE,
        nullable=False,
    )

    farmer: Mapped["Farmer"] = relationship("Farmer", back_populates="farms")

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