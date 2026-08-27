from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from enum import Enum
import os
import uuid
from dotenv import load_dotenv
from fastapi import Depends
from sqlalchemy import String, ForeignKey, DateTime, Enum as SQLEnum, Integer, LargeBinary, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship, Mapped, mapped_column
from fastapi_users.db import SQLAlchemyUserDatabase, SQLAlchemyBaseUserTableUUID, SQLAlchemyBaseOAuthAccountTableUUID

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


class Base(DeclarativeBase):
    pass


class InvestorType(str, Enum):
    INDIVIDUAL = "individual"
    INVESTMENT_GROUP = "investment_group"


class VerificationStatus(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    __tablename__ = "oauth_account"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"
    
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    investor_type: Mapped[InvestorType | None] = mapped_column(
        SQLEnum(InvestorType, native_enum=False), nullable=True
    )
    verification_status: Mapped[VerificationStatus] = mapped_column(
        SQLEnum(VerificationStatus, native_enum=False), default=VerificationStatus.NOT_SUBMITTED, nullable=False
    )

    individual_profile: Mapped["IndividualProfile"] = relationship(
        "IndividualProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    group_profile: Mapped["GroupProfile"] = relationship(
        "GroupProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined", cascade="all, delete-orphan"
    )


class IndividualProfile(Base):
    __tablename__ = "individual_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
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

    investment_preferences: Mapped[dict |
                                   None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="individual_profile")


class GroupProfile(Base):
    __tablename__ = "group_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False
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
    senior_mgmt_list: Mapped[dict | list] = mapped_column(
        JSONB, nullable=False)
    tax_id: Mapped[str] = mapped_column(String, nullable=False)

    cac_cert_file: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    cac_cert_filename: Mapped[str] = mapped_column(String, nullable=False)
    rep_id_file: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    rep_id_filename: Mapped[str] = mapped_column(String, nullable=False)

    investment_preferences: Mapped[dict |
                                   None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="group_profile")


engine = create_async_engine(DATABASE_URL)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS first_name VARCHAR(100);"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_name VARCHAR(100);"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);"))


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)
    

