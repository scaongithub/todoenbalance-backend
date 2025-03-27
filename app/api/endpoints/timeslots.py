"""Time slot management endpoints."""

from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_pagination_params
from app.core.jwt import get_current_admin, get_current_superuser
from app.models.timeslot import BlockedTimeSlot, RecurringTimeSlot, TimeSlot
from app.schemas.timeslot import (
    BlockedTimeSlotCreate,
    BlockedTimeSlotOut,
    BlockedTimeSlotUpdate,
    RecurringTimeSlotCreate,
    RecurringTimeSlotOut,
    RecurringTimeSlotUpdate,
    TimeSlotCreate,
    TimeSlotOut,
    TimeSlotUpdate,
)
from app.services.admin_service import AdminService

router = APIRouter()


# Individual time slots endpoints

@router.get("/slots", response_model=List[TimeSlotOut])
async def read_time_slots(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        available_only: bool = Query(False, description="Only show available slots"),
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get list of time slots.
    Only accessible by admins.
    """
    skip, limit = skip_limit

    # Build query with filters
    query = select(TimeSlot)

    if start_date:
        query = query.where(TimeSlot.start_time >= start_date)

    if end_date:
        query = query.where(TimeSlot.start_time <= end_date)

    if available_only:
        query = query.where(
            and_(
                TimeSlot.is_available == True,
                TimeSlot.is_booked == False,
            )
        )

    # Apply pagination and execute
    query = query.order_by(TimeSlot.start_time).offset(skip).limit(limit)
    result = await db.execute(query)
    time_slots = result.scalars().all()

    return time_slots


@router.post("/slots", response_model=List[TimeSlotOut])
async def create_time_slots(
        time_slots_in: List[TimeSlotCreate],
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Create new time slots.
    Only accessible by admins.
    """
    admin_service = AdminService(db)
    created_slots = await admin_service.create_time_slots(time_slots_in)
    return created_slots


@router.put("/slots/{slot_id}", response_model=TimeSlotOut)
async def update_time_slot(
        slot_id: int,
        slot_in: TimeSlotUpdate,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Update a time slot.
    Only accessible by admins.
    """
    # Get time slot
    stmt = select(TimeSlot).where(TimeSlot.id == slot_id)
    result = await db.execute(stmt)
    time_slot = result.scalar_one_or_none()

    if not time_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time slot with ID {slot_id} not found",
        )

    # Update fields
    if slot_in.is_available is not None:
        time_slot.is_available = slot_in.is_available

    if slot_in.is_booked is not None:
        time_slot.is_booked = slot_in.is_booked

    # Save changes
    db.add(time_slot)
    await db.commit()
    await db.refresh(time_slot)

    return time_slot


@router.delete("/slots/{slot_id}", response_model=bool)
async def delete_time_slot(
        slot_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Delete a time slot.
    Only accessible by admins.
    """
    # Get time slot
    stmt = select(TimeSlot).where(TimeSlot.id == slot_id)
    result = await db.execute(stmt)
    time_slot = result.scalar_one_or_none()

    if not time_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Time slot with ID {slot_id} not found",
        )

    # Check if slot is already booked
    if time_slot.is_booked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a booked time slot",
        )

    # Delete time slot
    await db.delete(time_slot)
    await db.commit()

    return True


# Recurring time slots endpoints

@router.get("/recurring", response_model=List[RecurringTimeSlotOut])
async def read_recurring_time_slots(
        active_only: bool = Query(False, description="Only show active recurring patterns"),
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get list of recurring time slot patterns.
    Only accessible by admins.
    """
    skip, limit = skip_limit

    # Build query with filters
    query = select(RecurringTimeSlot)

    if active_only:
        query = query.where(RecurringTimeSlot.is_active == True)

    # Apply pagination and execute
    query = query.order_by(RecurringTimeSlot.day_of_week).offset(skip).limit(limit)
    result = await db.execute(query)
    recurring_slots = result.scalars().all()

    return recurring_slots


@router.post("/recurring", response_model=RecurringTimeSlotOut)
async def create_recurring_time_slot(
        recurring_slot_in: RecurringTimeSlotCreate,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Create a new recurring time slot pattern.
    Only accessible by admins.
    """
    admin_service = AdminService(db)
    created_slot = await admin_service.create_recurring_time_slot(recurring_slot_in)
    return created_slot


@router.put("/recurring/{recurring_id}", response_model=RecurringTimeSlotOut)
async def update_recurring_time_slot(
        recurring_id: int,
        recurring_slot_in: RecurringTimeSlotUpdate,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Update a recurring time slot pattern.
    Only accessible by admins.
    """
    # Get recurring time slot
    stmt = select(RecurringTimeSlot).where(RecurringTimeSlot.id == recurring_id)
    result = await db.execute(stmt)
    recurring_slot = result.scalar_one_or_none()

    if not recurring_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring time slot with ID {recurring_id} not found",
        )

    # Update fields
    if recurring_slot_in.start_time is not None:
        recurring_slot.start_time = recurring_slot_in.start_time

    if recurring_slot_in.end_time is not None:
        recurring_slot.end_time = recurring_slot_in.end_time

    if recurring_slot_in.duration is not None:
        recurring_slot.duration = recurring_slot_in.duration

    if recurring_slot_in.valid_from is not None:
        recurring_slot.valid_from = recurring_slot_in.valid_from

    if recurring_slot_in.valid_until is not None:
        recurring_slot.valid_until = recurring_slot_in.valid_until

    if recurring_slot_in.is_active is not None:
        recurring_slot.is_active = recurring_slot_in.is_active

    # Save changes
    db.add(recurring_slot)
    await db.commit()
    await db.refresh(recurring_slot)

    return recurring_slot


@router.delete("/recurring/{recurring_id}", response_model=bool)
async def delete_recurring_time_slot(
        recurring_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Delete a recurring time slot pattern.
    Only accessible by admins.
    """
    # Get recurring time slot
    stmt = select(RecurringTimeSlot).where(RecurringTimeSlot.id == recurring_id)
    result = await db.execute(stmt)
    recurring_slot = result.scalar_one_or_none()

    if not recurring_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring time slot with ID {recurring_id} not found",
        )

    # Delete recurring time slot
    await db.delete(recurring_slot)
    await db.commit()

    return True


# Blocked time slots endpoints

@router.get("/blocked", response_model=List[BlockedTimeSlotOut])
async def read_blocked_time_slots(
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get list of blocked time slots.
    Only accessible by admins.
    """
    skip, limit = skip_limit

    # Build query with filters
    query = select(BlockedTimeSlot)

    if start_date:
        query = query.where(BlockedTimeSlot.end_datetime >= start_date)

    if end_date:
        query = query.where(BlockedTimeSlot.start_datetime <= end_date)

    # Apply pagination and execute
    query = query.order_by(BlockedTimeSlot.start_datetime).offset(skip).limit(limit)
    result = await db.execute(query)
    blocked_slots = result.scalars().all()

    return blocked_slots


@router.post("/blocked", response_model=BlockedTimeSlotOut)
async def create_blocked_time_slot(
        blocked_slot_in: BlockedTimeSlotCreate,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Create a new blocked time slot.
    Only accessible by admins.
    """
    admin_service = AdminService(db)
    created_slot = await admin_service.create_blocked_time_slot(blocked_slot_in)
    return created_slot


@router.put("/blocked/{blocked_id}", response_model=BlockedTimeSlotOut)
async def update_blocked_time_slot(
        blocked_id: int,
        blocked_slot_in: BlockedTimeSlotUpdate,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Update a blocked time slot.
    Only accessible by admins.
    """
    # Get blocked time slot
    stmt = select(BlockedTimeSlot).where(BlockedTimeSlot.id == blocked_id)
    result = await db.execute(stmt)
    blocked_slot = result.scalar_one_or_none()

    if not blocked_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blocked time slot with ID {blocked_id} not found",
        )

    # Update fields
    if blocked_slot_in.start_datetime is not None:
        blocked_slot.start_datetime = blocked_slot_in.start_datetime

    if blocked_slot_in.end_datetime is not None:
        blocked_slot.end_datetime = blocked_slot_in.end_datetime

    if blocked_slot_in.reason is not None:
        blocked_slot.reason = blocked_slot_in.reason

    # Save changes
    db.add(blocked_slot)
    await db.commit()
    await db.refresh(blocked_slot)

    return blocked_slot


@router.delete("/blocked/{blocked_id}", response_model=bool)
async def delete_blocked_time_slot(
        blocked_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Delete a blocked time slot.
    Only accessible by admins.
    """
    # Get blocked time slot
    stmt = select(BlockedTimeSlot).where(BlockedTimeSlot.id == blocked_id)
    result = await db.execute(stmt)
    blocked_slot = result.scalar_one_or_none()

    if not blocked_slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blocked time slot with ID {blocked_id} not found",
        )

    # Delete blocked time slot
    await db.delete(blocked_slot)
    await db.commit()

    return True


# Generation endpoints

@router.post("/generate", response_model=List[TimeSlotOut])
async def generate_time_slots(
        start_date: datetime = Query(..., description="Start date for generating time slots"),
        end_date: datetime = Query(..., description="End date for generating time slots"),
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Generate time slots from recurring patterns for a date range.
    Only accessible by admins.
    """
    # Validate date range
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Limit range to 90 days
    if (end_date - start_date).days > 90:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range cannot exceed 90 days",
        )

    # Generate time slots
    admin_service = AdminService(db)
    generated_slots = await admin_service.generate_time_slots_from_recurring(
        start_date,
        end_date,
    )

    return generated_slots