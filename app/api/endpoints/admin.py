"""Admin endpoints."""

from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_async_db, get_pagination_params
from app.core.exceptions import ConflictException, NotFoundException
from app.core.jwt import get_current_admin, get_current_superuser
from app.models.admin import Admin
from app.schemas.admin import AdminCreate, AdminOut, AdminUpdate
from app.services.admin_service import AdminService
from app.services.appointment_service import AppointmentService
from app.services.email_service import EmailService

router = APIRouter()


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_data(
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Get data for the admin dashboard.
    """
    admin_service = AdminService(db)
    dashboard_data = await admin_service.get_dashboard_data()
    return dashboard_data


@router.get("/admins", response_model=List[AdminOut])
async def read_admins(
        db: AsyncSession = Depends(get_async_db),
        current_superuser: Any = Depends(get_current_superuser),
        skip_limit: tuple = Depends(get_pagination_params),
) -> Any:
    """
    Get list of admin users.
    Only accessible by superusers.
    """
    skip, limit = skip_limit
    stmt = select(Admin).offset(skip).limit(limit)
    result = await db.execute(stmt)
    admins = result.scalars().all()
    return admins


@router.post("/admins", response_model=AdminOut)
async def create_admin(
        admin_in: AdminCreate,
        db: AsyncSession = Depends(get_async_db),
        current_superuser: Any = Depends(get_current_superuser),
) -> Any:
    """
    Create a new admin user.
    Only accessible by superusers.
    """
    admin_service = AdminService(db)

    try:
        new_admin = await admin_service.create_admin(admin_in)
        return new_admin
    except ConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get("/admins/{admin_id}", response_model=AdminOut)
async def read_admin(
        admin_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Get an admin by ID.
    Regular admins can only see their own profile.
    """
    admin_service = AdminService(db)
    admin = await admin_service.get_admin_by_id(admin_id)

    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Admin with ID {admin_id} not found",
        )

    # Check if current admin is allowed to view this admin
    is_superuser = current_admin.is_superuser
    if not is_superuser and current_admin.id != admin_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return admin


@router.put("/admins/{admin_id}", response_model=AdminOut)
async def update_admin(
        admin_id: int,
        admin_in: AdminUpdate,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Update an admin.
    Regular admins can only update their own profile.
    Superusers can update any admin.
    """
    admin_service = AdminService(db)

    # Check if current admin is allowed to update this admin
    is_superuser = current_admin.is_superuser
    if not is_superuser and current_admin.id != admin_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Non-superusers cannot change their superuser status
    if not is_superuser and admin_in.is_superuser is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot change superuser status",
        )

    try:
        updated_admin = await admin_service.update_admin(
            admin_id,
            admin_in,
            current_admin.id,
        )
        return updated_admin
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete("/admins/{admin_id}", response_model=bool)
async def delete_admin(
        admin_id: int,
        db: AsyncSession = Depends(get_async_db),
        current_superuser: Any = Depends(get_current_superuser),
) -> Any:
    """
    Delete an admin user.
    Only accessible by superusers.
    """
    admin_service = AdminService(db)

    try:
        result = await admin_service.delete_admin(
            admin_id,
            current_superuser.id,
        )
        return result
    except NotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ConflictException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post("/send-appointment-reminders", response_model=Dict[str, Any])
async def send_appointment_reminders(
        hours_before: int = 24,
        background_tasks: BackgroundTasks = BackgroundTasks(),
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Manually trigger appointment reminder emails.
    This can also be scheduled to run automatically.
    """
    appointment_service = AppointmentService(db, EmailService())
    reminder_count = await appointment_service.send_appointment_reminders(
        hours_before=hours_before,
        background_tasks=background_tasks,
    )

    return {
        "status": "success",
        "reminders_sent": reminder_count,
        "hours_before": hours_before,
    }


@router.post("/generate-slots", response_model=Dict[str, Any])
async def generate_time_slots(
        start_date: str,
        end_date: str,
        db: AsyncSession = Depends(get_async_db),
        current_admin: Any = Depends(get_current_admin),
) -> Any:
    """
    Generate time slots from recurring patterns.
    This can be scheduled to run periodically.
    """
    from datetime import datetime

    # Parse dates
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)",
        )

    # Generate slots
    admin_service = AdminService(db)
    slots = await admin_service.generate_time_slots_from_recurring(start, end)

    return {
        "status": "success",
        "slots_generated": len(slots),
        "start_date": start_date,
        "end_date": end_date,
    }