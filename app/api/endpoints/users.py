"""User endpoints."""

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_pagination_params
from app.core.jwt import get_current_admin, get_current_superuser, get_current_user
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter()


@router.get("", response_model=List[UserOut])
async def read_users(
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get list of users.
    Only accessible by admins.
    """
    skip, limit = skip_limit
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return users


@router.post("", response_model=UserOut)
async def create_user(
        user_in: UserCreate,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Create a new user.
    Only accessible by admins.
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
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        phone=user_in.phone,
        hashed_password=get_password_hash(user_in.password) if user_in.password else None,
        is_social_login=user_in.is_social_login,
        social_provider=user_in.social_provider,
        social_id=user_in.social_id,
        is_active=user_in.is_active,
        is_verified=False,  # Default to false, needs email verification
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.get("/me", response_model=UserOut)
async def read_user_me(
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.put("/me", response_model=UserOut)
async def update_user_me(
        user_in: UserUpdate,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update current user information.
    """
    # Handle password update
    if user_in.password:
        current_user.hashed_password = get_password_hash(user_in.password)

    # Update other fields
    if user_in.full_name is not None:
        current_user.full_name = user_in.full_name

    if user_in.phone is not None:
        current_user.phone = user_in.phone

    if user_in.health_notes is not None:
        current_user.health_notes = user_in.health_notes

    # Save changes
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return current_user


@router.get("/{user_id}", response_model=UserOut)
async def read_user_by_id(
        user_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get user by ID.
    Regular users can only access their own user information.
    Admins can access any user's information.
    """
    # Check if user is requesting their own information or is an admin
    is_admin = hasattr(current_user, "is_superuser")
    if not is_admin and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    return user


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
        user_id: int,
        user_in: UserUpdate,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Update a user.
    Only accessible by admins.
    """
    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Update fields
    if user_in.password:
        user.hashed_password = get_password_hash(user_in.password)

    if user_in.full_name is not None:
        user.full_name = user_in.full_name

    if user_in.email is not None:
        # Check if email is being changed and if it's already in use
        if user_in.email != user.email:
            email_stmt = select(User).where(User.email == user_in.email)
            email_result = await db.execute(email_stmt)
            existing_user = email_result.scalar_one_or_none()

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"User with email {user_in.email} already exists",
                )

            user.email = user_in.email

    if user_in.phone is not None:
        user.phone = user_in.phone

    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    if user_in.health_notes is not None:
        user.health_notes = user_in.health_notes

    # Save changes
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/{user_id}", response_model=bool)
async def delete_user(
        user_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_superuser: Any = Depends(get_current_superuser),
) -> Any:
    """
    Delete a user.
    Only accessible by superadmins.
    """
    # Get user
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Delete user
    await db.delete(user)
    await db.commit()

    return True