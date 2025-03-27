"""Authentication endpoints."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db
from app.core.exceptions import AuthenticationException
from app.core.jwt import get_current_user
from app.core.security import create_access_token, verify_password
from app.models.admin import Admin
from app.models.user import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserOut

router = APIRouter()


@router.post("/login", response_model=Token)
async def login_access_token(
        db: AsyncSession = Depends(get_async_db),
        form_data: OAuth2PasswordRequestForm = Depends(),
) -> Any:
    """
    Get an access token for future requests using username/password authentication.
    """
    # Check if this is a user login
    user_stmt = select(User).where(
        User.email == form_data.username,
        User.is_active == True
    )
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    if user and user.hashed_password and verify_password(form_data.password, user.hashed_password):
        # Update last login time
        user.last_login = datetime.utcnow()
        db.add(user)
        await db.commit()

        # Create access token
        access_token_expires = timedelta(minutes=60 * 24 * 8)  # 8 days
        return {
            "access_token": create_access_token(
                user.id, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
            "user_id": user.id,
            "is_admin": False
        }

    # Check if this is an admin login
    admin_stmt = select(Admin).where(
        Admin.email == form_data.username,
        Admin.is_active == True
    )
    admin_result = await db.execute(admin_stmt)
    admin = admin_result.scalar_one_or_none()

    if admin and verify_password(form_data.password, admin.hashed_password):
        # Update last login time
        admin.last_login = datetime.utcnow()
        db.add(admin)
        await db.commit()

        # Create access token with admin flag
        access_token_expires = timedelta(minutes=60 * 24 * 1)  # 1 day for admins
        return {
            "access_token": create_access_token(
                admin.id, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
            "user_id": admin.id,
            "is_admin": True
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/register", response_model=UserOut)
async def register_user(
        user_in: UserCreate,
        db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Register a new user.
    """
    # Check if user already exists
    user_stmt = select(User).where(User.email == user_in.email)
    user_result = await db.execute(user_stmt)
    existing_user = user_result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    # Create new user
    from app.core.security import get_password_hash

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        phone=user_in.phone,
        hashed_password=get_password_hash(user_in.password) if user_in.password else None,
        is_social_login=user_in.is_social_login,
        social_provider=user_in.social_provider,
        social_id=user_in.social_id,
        is_active=True,
        is_verified=False,  # Will be verified via email
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # TODO: Send verification email

    return user


@router.post("/social-login", response_model=Token)
async def social_login(
        provider: str,
        token: str,
        email: str,
        name: str,
        social_id: str,
        db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Login or register via social provider.
    """
    # Validate provider
    if provider not in ["google", "facebook", "apple"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid social provider",
        )

    # Check if user exists by social ID
    user_stmt = select(User).where(
        User.social_provider == provider,
        User.social_id == social_id,
        User.is_active == True
    )
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()

    # If not found by social ID, try by email
    if not user:
        email_stmt = select(User).where(
            User.email == email,
            User.is_active == True
        )
        email_result = await db.execute(email_stmt)
        user = email_result.scalar_one_or_none()

    # If still not found, create a new user
    if not user:
        user = User(
            email=email,
            full_name=name,
            is_social_login=True,
            social_provider=provider,
            social_id=social_id,
            is_active=True,
            is_verified=True,  # Social logins are considered verified
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        # Update existing user with social info if needed
        update_needed = False

        if not user.social_id or not user.social_provider:
            user.is_social_login = True
            user.social_provider = provider
            user.social_id = social_id
            update_needed = True

        if not user.is_verified:
            user.is_verified = True
            update_needed = True

        if update_needed:
            user.last_login = datetime.utcnow()
            db.add(user)
            await db.commit()

    # Create access token
    access_token_expires = timedelta(minutes=60 * 24 * 8)  # 8 days
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
        "user_id": user.id,
        "is_admin": False
    }


@router.get("/me", response_model=UserOut)
async def read_users_me(
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user information.
    """
    return current_user