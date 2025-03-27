"""Appointment endpoints."""

from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_pagination_params
from app.core.exceptions import (
    ConflictException,
    DoubleBookingException,
    ForbiddenException,
    NotFoundException,
    SchedulingException,
)
from app.core.jwt import get_current_admin, get_current_user
from app.models.appointment import Appointment, AppointmentStatus, AppointmentType
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentUpdate
from app.services.appointment_service import AppointmentService
from app.services.email_service import EmailService

router = APIRouter()


@router.get("", response_model=List[AppointmentOut])
async def read_appointments(
        status: Optional[AppointmentStatus] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get list of appointments.
    Only accessible by admins.
    """
    skip, limit = skip_limit

    # Build query with filters
    query = select(Appointment)

    if status:
        query = query.where(Appointment.status == status)

    if from_date:
        query = query.where(Appointment.start_time >= from_date)

    if to_date:
        query = query.where(Appointment.start_time <= to_date)

    # Apply pagination and execute
    query = query.order_by(Appointment.start_time.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    appointments = result.scalars().all()

    return appointments


@router.post("", response_model=AppointmentOut)
async def create_appointment(
        appointment_in: AppointmentCreate,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Create a new appointment.
    """
    appointment_service = AppointmentService(db, EmailService())

    try:
        appointment = await appointment_service.create_appointment(
            appointment_in,
            current_user.id,
            background_tasks,
        )
        return appointment
    except SchedulingException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except DoubleBookingException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("/me", response_model=List[AppointmentOut])
async def read_my_appointments(
        status: Optional[AppointmentStatus] = None,
        upcoming_only: bool = Query(False, description="Only show upcoming appointments"),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get current user's appointments.
    """
    skip, limit = skip_limit

    # Build query
    query = select(Appointment).where(Appointment.user_id == current_user.id)

    if status:
        query = query.where(Appointment.status == status)

    if upcoming_only:
        query = query.where(
            and_(
                Appointment.start_time >= datetime.utcnow(),
                Appointment.status.in_([
                    AppointmentStatus.PENDING,
                    AppointmentStatus.CONFIRMED,
                ]),
            )
        )

    # Apply pagination and execute
    query = query.order_by(Appointment.start_time.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    appointments = result.scalars().all()

    return appointments


@router.get("/{appointment_id}", response_model=AppointmentOut)
async def read_appointment(
        appointment_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Get an appointment by ID.
    Regular users can only access their own appointments.
    """
    # Get appointment
    appointment_service = AppointmentService(db)
    appointment = await appointment_service.get_appointment_by_id(appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found",
        )

    # Check access permissions
    is_admin = hasattr(current_user, "is_superuser")
    if not is_admin and appointment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return appointment


@router.put("/{appointment_id}", response_model=AppointmentOut)
async def update_appointment(
        appointment_id: int,
        appointment_in: AppointmentUpdate,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Update an appointment.
    Regular users can only update their own appointments.
    """
    # Check if appointment exists
    appointment_service = AppointmentService(db, EmailService())
    appointment = await appointment_service.get_appointment_by_id(appointment_id)

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found",
        )

    # Check if user is admin
    is_admin = hasattr(current_user, "is_superuser")

    try:
        updated_appointment = await appointment_service.update_appointment(
            appointment_id,
            appointment_in,
            current_user.id,
            is_admin,
            background_tasks,
        )
        return updated_appointment
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except SchedulingException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except DoubleBookingException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post("/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(
        appointment_id: int,
        admin_notes: Optional[str] = None,
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: AsyncSession = Depends(get_async_db),
        current_user: User = Depends(get_current_user),
) -> Any:
    """
    Cancel an appointment.
    Regular users can only cancel their own appointments.
    """
    # Check if user is admin
    is_admin = hasattr(current_user, "is_superuser")

    # Cancel appointment
    appointment_service = AppointmentService(db, EmailService())

    try:
        cancelled_appointment = await appointment_service.cancel_appointment(
            appointment_id,
            current_user.id,
            is_admin,
            admin_notes,
            background_tasks,
        )
        return cancelled_appointment
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ForbiddenException as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except SchedulingException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/available", response_model=List[dict])
async def get_available_slots(
        start_date: datetime = Query(..., description="Start date for available slots"),
        end_date: datetime = Query(..., description="End date for available slots"),
        duration: int = Query(30, description="Duration in minutes"),
        db: AsyncSession = Depends(get_async_db),
) -> Any:
    """
    Get available appointment slots.
    """
    # Validate date range
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Limit range to 30 days
    if (end_date - start_date).days > 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 30 days",
        )

    # Get available slots
    appointment_service = AppointmentService(db)
    available_slots = await appointment_service.get_available_time_slots(
        start_date,
        end_date,
        duration,
    )

    return available_slots