import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# Load .env file
load_dotenv()

# Fetch DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "")

# 1. Format URL for asyncpg compatibility
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Strip unsupported parameters if present in Neon URL
if "&channel_binding=" in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.split("&channel_binding=")[0]

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in environment variables.")

# 2. Create the Async Engine
# pool_pre_ping=True tests connections before using them (essential for Neon idle timeouts)
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# 3. Create the Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 4. Declarative Base Class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# 5. Dependency injection generator for FastAPI endpoints
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()