"""JWT token handling for authentication."""

from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db
from app.config import settings
from app.core.exceptions import AuthenticationException
from app.core.security import ALGORITHM
from app.models.admin import Admin
from app.models.user import User
from app.schemas.token import TokenPayload

# OAuth2 scheme for token-based authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


async def get_current_user(
        db: AsyncSession = Depends(get_async_db),
        token: str = Depends(oauth2_scheme),
) -> User:
    """
    Validate access token and return current user.

    Args:
        db: Database session.
        token: JWT token from Authorization header.

    Returns:
        User: The authenticated user.

    Raises:
        AuthenticationException: If token is invalid or user not found.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        # Check if token has expired
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise AuthenticationException("Token expired")

    except (JWTError, ValidationError):
        raise AuthenticationException("Could not validate credentials")

    # Get user from database
    stmt = select(User).where(User.id == int(token_data.sub), User.is_active == True)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationException("User not found")

    return user


async def get_current_admin(
        db: AsyncSession = Depends(get_async_db),
        token: str = Depends(oauth2_scheme),
) -> Admin:
    """
    Validate access token and return current admin user.

    Args:
        db: Database session.
        token: JWT token from Authorization header.

    Returns:
        Admin: The authenticated admin.

    Raises:
        AuthenticationException: If token is invalid or admin not found.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        token_data = TokenPayload(**payload)

        # Check if token has expired
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise AuthenticationException("Token expired")

        # Check if this is an admin token
        if not payload.get("is_admin"):
            raise AuthenticationException("Not an admin token")

    except (JWTError, ValidationError):
        raise AuthenticationException("Could not validate credentials")

    # Get admin from database
    stmt = select(Admin).where(Admin.id == int(token_data.sub), Admin.is_active == True)
    result = await db.execute(stmt)
    admin = result.scalar_one_or_none()

    if not admin:
        raise AuthenticationException("Admin not found")

    return admin


async def get_current_superuser(
        current_admin: Admin = Depends(get_current_admin),
) -> Admin:
    """
    Check if current admin has superuser privileges.

    Args:
        current_admin: The current authenticated admin.

    Returns:
        Admin: The authenticated superuser.

    Raises:
        AuthenticationException: If admin is not a superuser.
    """
    if not current_admin.is_superuser:
        raise AuthenticationException("Insufficient privileges")

    return current_admin