import uuid
from typing import TYPE_CHECKING, Optional, Union
from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.userModel import User


class IndividualProfile(Base, TimestampMixin):
    __tablename__ = "individual_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    full_name: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    dob: Mapped[str] = mapped_column(String, nullable=False)
    nationality: Mapped[str] = mapped_column(String, nullable=False)
    residential_address: Mapped[str] = mapped_column(String, nullable=False)

    id_type: Mapped[str] = mapped_column(String, nullable=False)
    id_number: Mapped[str] = mapped_column(String, nullable=False)

    id_doc_file: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    id_doc_filename: Mapped[str] = mapped_column(String, nullable=False)

    investment_preferences: Mapped[Optional[str]
                                   ] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(
        "User", back_populates="individual_profile")


class GroupProfile(Base, TimestampMixin):
    __tablename__ = "group_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    cooperative_name: Mapped[str] = mapped_column(String, nullable=False)
    cooperative_type: Mapped[str] = mapped_column(String, nullable=False)
    registration_number: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    year_established: Mapped[int] = mapped_column(Integer, nullable=False)

    rep_name: Mapped[str] = mapped_column(String, nullable=False)
    rep_contact: Mapped[str] = mapped_column(String, nullable=False)
    senior_mgmt_list: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=None)
    investment_preferences: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=None)
    tax_id: Mapped[str] = mapped_column(String, nullable=False)

    cac_cert_file: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    cac_cert_filename: Mapped[str] = mapped_column(String, nullable=False)
    rep_id_file: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    rep_id_filename: Mapped[str] = mapped_column(String, nullable=False)


    user: Mapped["User"] = relationship("User", back_populates="group_profile")
