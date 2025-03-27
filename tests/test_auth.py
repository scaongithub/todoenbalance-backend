"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.admin import Admin


def test_login_user(client: TestClient, normal_user: User):
    """Test user login."""
    login_data = {
        "username": "user@example.com",
        "password": "password",
    }
    response = client.post("/api/v1/auth/login", data=login_data)

    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["user_id"] == normal_user.id
    assert tokens["is_admin"] is False


def test_login_admin(client: TestClient, admin_user: Admin):
    """Test admin login."""
    login_data = {
        "username": "admin@example.com",
        "password": "password",
    }
    response = client.post("/api/v1/auth/login", data=login_data)

    assert response.status_code == 200
    tokens = response.json()
    assert "access_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["user_id"] == admin_user.id
    assert tokens["is_admin"] is True


def test_login_wrong_password(client: TestClient, normal_user: User):
    """Test login with wrong password."""
    login_data = {
        "username": "user@example.com",
        "password": "wrong-password",
    }
    response = client.post("/api/v1/auth/login", data=login_data)

    assert response.status_code == 401
    assert "detail" in response.json()


def test_register_user(client: TestClient):
    """Test user registration."""
    user_data = {
        "email": "newuser@example.com",
        "full_name": "New User",
        "password": "newpassword",
    }
    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 200
    user = response.json()
    assert user["email"] == "newuser@example.com"
    assert user["full_name"] == "New User"
    assert "id" in user


def test_register_duplicate_email(client: TestClient, normal_user: User):
    """Test registration with duplicate email."""
    user_data = {
        "email": "user@example.com",  # Same as normal_user
        "full_name": "Another User",
        "password": "password",
    }
    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 409
    assert "detail" in response.json()


def test_get_current_user(client: TestClient, normal_user_token_headers: dict):
    """Test getting current user information."""
    response = client.get("/api/v1/auth/me", headers=normal_user_token_headers)

    assert response.status_code == 200
    user = response.json()
    assert user["email"] == "user@example.com"
    assert user["full_name"] == "Test User"


def test_get_current_user_no_token(client: TestClient):
    """Test getting current user without token."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert "detail" in response.json()