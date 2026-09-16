import uuid
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
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
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    id_number: Mapped[str] = mapped_column(String, nullable=False)
    id_file: Mapped[str] = mapped_column(String, nullable=False)
    nationality: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped["User"] = relationship(
        "User", back_populates="individual_profile"
    )


class GroupProfile(Base, TimestampMixin):
    __tablename__ = "group_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    company_name: Mapped[str] = mapped_column(String, nullable=False)
    company_address: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    phone_number: Mapped[str] = mapped_column(String, nullable=False)
    year_established: Mapped[int] = mapped_column(Integer, nullable=False)
    company_registration_number: Mapped[str] = mapped_column(
        String, nullable=False
    )
    company_registration_file: Mapped[str] = mapped_column(
        String, nullable=False
    )
    proof_of_address_file: Mapped[str] = mapped_column(String, nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="group_profile")


class CooperativeProfile(Base, TimestampMixin):
    __tablename__ = "cooperative_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    cooperative_name: Mapped[str] = mapped_column(String, nullable=False)
    year_established: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_number: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    lga: Mapped[str] = mapped_column(String, nullable=False)
    state: Mapped[str] = mapped_column(String, nullable=False)
    registration_certificate_file: Mapped[str] = mapped_column(
        String, nullable=False
    )
    proof_of_address_file: Mapped[str] = mapped_column(
        String, nullable=False
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="cooperative_profile"
    )