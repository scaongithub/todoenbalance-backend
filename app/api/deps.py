"""Dependencies for API endpoints."""

from fastapi import Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.database import get_async_db
from app.models.appointment import Appointment
from app.models.user import User


async def get_user_by_id(
        user_id: int,
        db: AsyncSession = Depends(get_async_db),
) -> User:
    """
    Get a user by ID.

    Args:
        user_id: The user ID.
        db: Database session.

    Returns:
        User: The user.

    Raises:
        NotFoundException: If the user is not found.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise NotFoundException(f"User with ID {user_id} not found")

    return user


async def get_appointment_by_id(
        appointment_id: int,
        db: AsyncSession = Depends(get_async_db),
) -> Appointment:
    """
    Get an appointment by ID.

    Args:
        appointment_id: The appointment ID.
        db: Database session.

    Returns:
        Appointment: The appointment.

    Raises:
        NotFoundException: If the appointment is not found.
    """
    result = await db.execute(select(Appointment).where(Appointment.id == appointment_id))
    appointment = result.scalar_one_or_none()

    if not appointment:
        raise NotFoundException(f"Appointment with ID {appointment_id} not found")

    return appointment


def get_pagination_params(
        skip: int = Query(0, ge=0, description="Number of items to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
) -> tuple[int, int]:
    """
    Get pagination parameters.

    Args:
        skip: Number of items to skip.
        limit: Maximum number of items to return.

    Returns:
        tuple: Tuple of (skip, limit).
    """
    return skip, limit


# Re-export database dependency for convenience
__all__ = ["get_async_db", "get_user_by_id", "get_appointment_by_id", "get_pagination_params"]