import enum
import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum as SQLEnum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class WRSStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    NOT_VERIFIED = "NOT_VERIFIED"


if TYPE_CHECKING:
    from app.models.userModel import User


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
    crop_type: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    gender: Mapped[Gender] = mapped_column(
        SQLEnum(Gender, native_enum=False), nullable=False
    )
    farm_size_acres: Mapped[float] = mapped_column(Float, nullable=False)
    farm_address: Mapped[str] = mapped_column(String, nullable=False)
    photo: Mapped[str] = mapped_column(String, nullable=False)
    additional_info: Mapped[Optional[str]
                            ] = mapped_column(String, nullable=True)

    wrs_status: Mapped[WRSStatus] = mapped_column(
        SQLEnum(WRSStatus, native_enum=False),
        default=WRSStatus.NOT_VERIFIED,
        nullable=False,
    )

    cooperative: Mapped["User"] = relationship(
        "User", back_populates="farmers")
