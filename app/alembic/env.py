import asyncio
import os
from logging.config import fileConfig

from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Load environment variables from .env
load_dotenv()

# Base metadata
from app.models.base import Base

# IMPORTANT: Import ALL model modules here so Base.metadata is aware of them
import app.models.user_model
import app.models.profile_model
import app.models.farmer_model
import app.models.cooperative_investment_model
import app.models.wallet_model
import app.models.package_model

# Alembic Config object
config = context.config

# Fetch database URL from environment
db_url = os.getenv("MIGRATION_DATABASE_URL") or os.getenv("DATABASE_URL", "")

# 1. Strip '-pooler' to force direct connection for DDL migrations
if "-pooler" in db_url:
    db_url = db_url.replace("-pooler", "")

# 2. Fix query params for asyncpg (asyncpg expects 'ssl=' instead of 'sslmode=')
if "sslmode=" in db_url:
    db_url = db_url.replace("sslmode=", "ssl=")

# Remove channel_binding parameter as asyncpg does not support it
db_url = db_url.replace("&channel_binding=require", "").replace("channel_binding=require&", "").replace("channel_binding=require", "")

# 3. Ensure async SQLAlchemy dialect prefix (postgresql+asyncpg://)
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

# Set sanitized direct URL into Alembic configuration
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Creates an Engine and associates a connection with the context."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()