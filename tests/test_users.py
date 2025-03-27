"""Tests for user endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


def test_read_users_admin(client: TestClient, admin_token_headers: dict):
    """Test that admins can read the users list."""
    response = client.get("/api/v1/users", headers=admin_token_headers)

    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1  # At least the test user
    assert "email" in users[0]


def test_read_users_normal_user(client: TestClient, normal_user_token_headers: dict):
    """Test that normal users cannot read the users list."""
    response = client.get("/api/v1/users", headers=normal_user_token_headers)

    assert response.status_code == 401
    assert "detail" in response.json()


def test_read_user_me(client: TestClient, normal_user_token_headers: dict):
    """Test that users can read their own data."""
    response = client.get("/api/v1/users/me", headers=normal_user_token_headers)

    assert response.status_code == 200
    user = response.json()
    assert user["email"] == "user@example.com"
    assert user["full_name"] == "Test User"


def test_update_user_me(client: TestClient, normal_user_token_headers: dict):
    """Test that users can update their own data."""
    update_data = {
        "full_name": "Updated User Name"
    }
    response = client.put(
        "/api/v1/users/me",
        headers=normal_user_token_headers,
        json=update_data
    )

    assert response.status_code == 200
    user = response.json()
    assert user["full_name"] == "Updated User Name"


def test_read_user_by_id_admin(
        client: TestClient, admin_token_headers: dict, normal_user: User
):
    """Test that admins can read user data by ID."""
    response = client.get(
        f"/api/v1/users/{normal_user.id}",
        headers=admin_token_headers
    )

    assert response.status_code == 200
    user = response.json()
    assert user["email"] == "user@example.com"
    assert user["id"] == normal_user.id


def test_read_user_by_id_normal_self(
        client: TestClient, normal_user_token_headers: dict, normal_user: User
):
    """Test that users can read their own data by ID."""
    response = client.get(
        f"/api/v1/users/{normal_user.id}",
        headers=normal_user_token_headers
    )

    assert response.status_code == 200
    user = response.json()
    assert user["email"] == "user@example.com"
    assert user["id"] == normal_user.id


def test_read_user_by_id_normal_other(
        client: TestClient, normal_user_token_headers: dict
):
    """Test that users cannot read other user data by ID."""
    other_user_id = 9999  # Assuming this ID doesn't exist or belongs to another user
    response = client.get(
        f"/api/v1/users/{other_user_id}",
        headers=normal_user_token_headers
    )

    assert response.status_code == 403  # Forbidden
    assert "detail" in response.json()


def test_update_user_admin(
        client: TestClient, admin_token_headers: dict, normal_user: User
):
    """Test that admins can update user data."""
    update_data = {
        "full_name": "Admin Updated Name",
        "is_active": True
    }
    response = client.put(
        f"/api/v1/users/{normal_user.id}",
        headers=admin_token_headers,
        json=update_data
    )

    assert response.status_code == 200
    user = response.json()
    assert user["full_name"] == "Admin Updated Name"
    assert user["is_active"] is True