"""Database connection and session management."""

import contextlib
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

from app.config import settings

# Convert SQLite URL to async version
# For SQLite, use aiosqlite as driver for async operations
# Example: sqlite:///./app.db -> sqlite+aiosqlite:///./app.db
SQLALCHEMY_DATABASE_URL = settings.SQLITE_DATABASE_URI.replace(
    "sqlite:///", "sqlite+aiosqlite:///", 1
)

# For synchronous operations (like migrations)
sync_engine = create_engine(
    settings.SQLITE_DATABASE_URI,
    poolclass=QueuePool,
    pool_size=5,  # Adjust based on expected load
    max_overflow=10,
    pool_timeout=30,  # 30 seconds
    pool_recycle=1800,  # 30 minutes
    connect_args={"check_same_thread": False}  # Required for SQLite
)

# For asynchronous operations (like API requests)
async_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={"check_same_thread": False}
)

# Sync session factory (for migrations and sync operations)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

# Async session factory (for FastAPI endpoints)
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevents detached instance errors in async code
)

# Base class for SQLAlchemy models
Base = declarative_base()


def get_db() -> Generator:
    """
    Get a new database session for synchronous operations.

    Yields:
        Session: A database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextlib.asynccontextmanager
async def get_db_context():
    """
    Context manager for async database sessions.

    Yields:
        AsyncSession: An async database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a new database session for asynchronous operations.

    Dependency function for FastAPI endpoints.

    Yields:
        AsyncSession: An async database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Pre-configure the database
def init_db() -> None:
    """Initialize the database by creating all tables."""
    Base.metadata.create_all(bind=sync_engine)