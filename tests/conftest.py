"""Test fixtures for the application."""

import asyncio
from typing import Dict, Generator

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_async_db
from app.main import app
from app.models.admin import Admin
from app.models.user import User
from app.core.security import create_access_token, get_password_hash

# Set up test database
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_URL = "sqlite:///:memory:"

# Sync engine for setup
test_sync_engine = create_engine(
    TEST_SYNC_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Async engine for tests
test_async_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_sync_engine,
)

AsyncTestSessionLocal = sessionmaker(
    bind=test_async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# Dependency override
async def override_get_async_db():
    """Override the get_async_db dependency for testing."""
    async with AsyncTestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Test client
@pytest.fixture
def client() -> Generator:
    """Create a test client."""
    # Use sync engine to create all tables
    Base.metadata.create_all(bind=test_sync_engine)

    # Override dependencies
    app.dependency_overrides[get_async_db] = override_get_async_db

    with TestClient(app) as test_client:
        yield test_client

    # Clean up
    Base.metadata.drop_all(bind=test_sync_engine)


# Test database session
@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Create a test database session."""
    async with AsyncTestSessionLocal() as session:
        yield session


# User fixtures
@pytest_asyncio.fixture
async def normal_user(db_session: AsyncSession) -> User:
    """Create a normal user for testing."""
    user = User(
        email="user@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("password"),
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> Admin:
    """Create an admin user for testing."""
    admin = Admin(
        email="admin@example.com",
        full_name="Admin User",
        hashed_password=get_password_hash("password"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


# Authentication fixtures
@pytest.fixture
def normal_user_token_headers(normal_user: User) -> Dict[str, str]:
    """Create authentication headers for a normal user."""
    token = create_access_token(normal_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_token_headers(admin_user: Admin) -> Dict[str, str]:
    """Create authentication headers for an admin user."""
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}