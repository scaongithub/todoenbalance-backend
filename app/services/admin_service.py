"""Admin service for administrative operations."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import BackgroundTasks
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.core.security import get_password_hash
from app.models.admin import Admin
from app.models.appointment import Appointment, AppointmentStatus
from app.models.payment import Payment, PaymentStatus
from app.models.timeslot import BlockedTimeSlot, RecurringTimeSlot, TimeSlot
from app.schemas.admin import AdminCreate, AdminUpdate
from app.schemas.timeslot import (
    BlockedTimeSlotCreate,
    RecurringTimeSlotCreate,
    TimeSlotCreate,
)

logger = logging.getLogger(__name__)


class AdminService:
    """Service for administrative operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the admin service.

        Args:
            db: Database session.
        """
        self.db = db

    # Admin user management

    async def create_admin(self, data: AdminCreate) -> Admin:
        """
        Create a new admin user.

        Args:
            data: Admin user data.

        Returns:
            Created admin user.

        Raises:
            ConflictException: If an admin with the same email already exists.
        """
        # Check if admin with the same email already exists
        stmt = select(Admin).where(Admin.email == data.email)
        result = await self.db.execute(stmt)
        existing_admin = result.scalar_one_or_none()

        if existing_admin:
            raise ConflictException(f"Admin with email {data.email} already exists")

        # Create new admin
        hashed_password = get_password_hash(data.password)
        new_admin = Admin(
            email=data.email,
            full_name=data.full_name,
            hashed_password=hashed_password,
            is_active=data.is_active,
            is_superuser=data.is_superuser,
        )

        self.db.add(new_admin)
        await self.db.commit()
        await self.db.refresh(new_admin)

        return new_admin

    async def get_admin_by_email(self, email: str) -> Optional[Admin]:
        """
        Get admin by email.

        Args:
            email: Admin email.

        Returns:
            Admin if found, None otherwise.
        """
        stmt = select(Admin).where(Admin.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_admin_by_id(self, admin_id: int) -> Optional[Admin]:
        """
        Get admin by ID.

        Args:
            admin_id: Admin ID.

        Returns:
            Admin if found, None otherwise.
        """
        stmt = select(Admin).where(Admin.id == admin_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_admin(
            self, admin_id: int, data: AdminUpdate, current_admin_id: int
    ) -> Admin:
        """
        Update an admin user.

        Args:
            admin_id: Admin ID to update.
            data: Updated admin data.
            current_admin_id: ID of the admin making the request.

        Returns:
            Updated admin user.

        Raises:
            NotFoundException: If the admin is not found.
            ConflictException: If trying to remove the last superuser.
        """
        # Get the admin to update
        admin = await self.get_admin_by_id(admin_id)
        if not admin:
            raise NotFoundException(f"Admin with ID {admin_id} not found")

        # Check if we're removing superuser status from the last superuser
        if admin.is_superuser and data.is_superuser is False:
            # Count how many superusers we have
            stmt = select(func.count(Admin.id)).where(
                and_(Admin.is_superuser == True, Admin.is_active == True)
            )
            result = await self.db.execute(stmt)
            superuser_count = result.scalar_one()

            if superuser_count <= 1:
                raise ConflictException(
                    "Cannot remove superuser status from the last superuser"
                )

        # Update admin fields
        if data.email is not None:
            admin.email = data.email

        if data.full_name is not None:
            admin.full_name = data.full_name

        if data.password is not None:
            admin.hashed_password = get_password_hash(data.password)

        if data.is_active is not None:
            admin.is_active = data.is_active

        if data.is_superuser is not None:
            admin.is_superuser = data.is_superuser

        admin.updated_at = datetime.utcnow()

        # Save the updated admin
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)

        return admin

    async def delete_admin(self, admin_id: int, current_admin_id: int) -> bool:
        """
        Delete an admin user.

        Args:
            admin_id: Admin ID to delete.
            current_admin_id: ID of the admin making the request.

        Returns:
            True if deleted, False otherwise.

        Raises:
            NotFoundException: If the admin is not found.
            ConflictException: If trying to delete the last superuser or yourself.
        """
        # Get the admin to delete
        admin = await self.get_admin_by_id(admin_id)
        if not admin:
            raise NotFoundException(f"Admin with ID {admin_id} not found")

        # Cannot delete yourself
        if admin_id == current_admin_id:
            raise ConflictException("Cannot delete your own admin account")

        # Check if we're deleting the last superuser
        if admin.is_superuser:
            # Count how many superusers we have
            stmt = select(func.count(Admin.id)).where(
                and_(Admin.is_superuser == True, Admin.is_active == True)
            )
            result = await self.db.execute(stmt)
            superuser_count = result.scalar_one()

            if superuser_count <= 1:
                raise ConflictException("Cannot delete the last superuser")

        # Delete the admin
        await self.db.delete(admin)
        await self.db.commit()

        return True

    # Time slot management

    async def create_time_slots(self, data_list: List[TimeSlotCreate]) -> List[TimeSlot]:
        """
        Create multiple time slots.

        Args:
            data_list: List of time slot data.

        Returns:
            List of created time slots.
        """
        created_slots = []

        for data in data_list:
            # Check for existing time slot
            stmt = select(TimeSlot).where(
                and_(
                    TimeSlot.start_time == data.start_time,
                    TimeSlot.end_time == data.end_time
                )
            )
            result = await self.db.execute(stmt)
            existing_slot = result.scalar_one_or_none()

            if existing_slot:
                # Update existing slot
                existing_slot.is_available = data.is_available
                self.db.add(existing_slot)
                created_slots.append(existing_slot)
            else:
                # Create new slot
                new_slot = TimeSlot(
                    start_time=data.start_time,
                    end_time=data.end_time,
                    duration=data.duration,
                    is_available=data.is_available,
                    is_booked=False,
                )
                self.db.add(new_slot)
                created_slots.append(new_slot)

        await self.db.commit()

        # Refresh all created slots
        for slot in created_slots:
            await self.db.refresh(slot)

        return created_slots

    async def create_recurring_time_slot(
            self, data: RecurringTimeSlotCreate
    ) -> RecurringTimeSlot:
        """
        Create a recurring time slot.

        Args:
            data: Recurring time slot data.

        Returns:
            Created recurring time slot.
        """
        new_recurring_slot = RecurringTimeSlot(
            day_of_week=data.day_of_week,
            start_time=data.start_time,
            end_time=data.end_time,
            duration=data.duration,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            is_active=True,
        )

        self.db.add(new_recurring_slot)
        await self.db.commit()
        await self.db.refresh(new_recurring_slot)

        return new_recurring_slot

    async def create_blocked_time_slot(
            self, data: BlockedTimeSlotCreate
    ) -> BlockedTimeSlot:
        """
        Create a blocked time slot.

        Args:
            data: Blocked time slot data.

        Returns:
            Created blocked time slot.
        """
        new_blocked_slot = BlockedTimeSlot(
            start_datetime=data.start_datetime,
            end_datetime=data.end_datetime,
            reason=data.reason,
        )

        self.db.add(new_blocked_slot)
        await self.db.commit()
        await self.db.refresh(new_blocked_slot)

        return new_blocked_slot

    async def generate_time_slots_from_recurring(
            self, start_date: datetime, end_date: datetime
    ) -> List[TimeSlot]:
        """
        Generate time slots from recurring patterns for a date range.

        Args:
            start_date: Start date of the range.
            end_date: End date of the range.

        Returns:
            List of created time slots.
        """
        # Get active recurring slots
        stmt = select(RecurringTimeSlot).where(
            and_(
                RecurringTimeSlot.is_active == True,
                RecurringTimeSlot.valid_from <= end_date,
                or_(
                    RecurringTimeSlot.valid_until.is_(None),
                    RecurringTimeSlot.valid_until >= start_date
                )
            )
        )
        result = await self.db.execute(stmt)
        recurring_slots = result.scalars().all()

        created_slots = []
        current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Generate time slots for each day in the range
        while current_date <= end_date:
            # Get the day of week (1-7, where 1 is Monday)
            day_of_week = current_date.isoweekday()

            # Find recurring slots for this day
            for recurring_slot in recurring_slots:
                if recurring_slot.day_of_week.value == day_of_week:
                    # Skip if outside the validity period
                    if current_date < recurring_slot.valid_from:
                        continue
                    if recurring_slot.valid_until and current_date > recurring_slot.valid_until:
                        continue

                    # Calculate actual date and time
                    start_datetime = datetime.combine(
                        current_date.date(),
                        recurring_slot.start_time
                    )
                    end_datetime = datetime.combine(
                        current_date.date(),
                        recurring_slot.end_time
                    )

                    # If the start time is in the past, skip
                    if start_datetime < datetime.utcnow():
                        continue

                    # Create slots with the configured duration
                    current_start = start_datetime
                    while current_start + timedelta(minutes=recurring_slot.duration) <= end_datetime:
                        slot_end = current_start + timedelta(minutes=recurring_slot.duration)

                        # Check if this slot already exists
                        stmt = select(TimeSlot).where(
                            and_(
                                TimeSlot.start_time == current_start,
                                TimeSlot.end_time == slot_end
                            )
                        )
                        existing_result = await self.db.execute(stmt)
                        existing_slot = existing_result.scalar_one_or_none()

                        if not existing_slot:
                            # Check if this time is blocked
                            blocked_stmt = select(BlockedTimeSlot).where(
                                and_(
                                    BlockedTimeSlot.start_datetime <= current_start,
                                    BlockedTimeSlot.end_datetime >= slot_end
                                )
                            )
                            blocked_result = await self.db.execute(blocked_stmt)
                            blocked = blocked_result.scalar_one_or_none()

                            if not blocked:
                                # Create the slot
                                new_slot = TimeSlot(
                                    start_time=current_start,
                                    end_time=slot_end,
                                    duration=recurring_slot.duration,
                                    is_available=True,
                                    is_booked=False,
                                )
                                self.db.add(new_slot)
                                created_slots.append(new_slot)

                        # Move to the next slot
                        current_start = slot_end

            # Move to the next day
            current_date += timedelta(days=1)

        if created_slots:
            await self.db.commit()

            # Refresh all created slots
            for slot in created_slots:
                await self.db.refresh(slot)

        return created_slots

    # Dashboard data

    async def get_dashboard_data(self) -> Dict:
        """
        Get data for the admin dashboard.

        Returns:
            Dictionary with dashboard data.
        """
        # Calculate date ranges
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=7)
        month_start = today.replace(day=1)
        next_month = month_start.replace(
            month=month_start.month + 1 if month_start.month < 12 else 1,
            year=month_start.year if month_start.month < 12 else month_start.year + 1
        )

        # Get today's appointments
        today_appointments_stmt = select(func.count(Appointment.id)).where(
            and_(
                Appointment.start_time >= today,
                Appointment.start_time < tomorrow,
                Appointment.status.in_([
                    AppointmentStatus.PENDING,
                    AppointmentStatus.CONFIRMED
                ])
            )
        )
        today_appointments_result = await self.db.execute(today_appointments_stmt)
        today_appointments_count = today_appointments_result.scalar_one()

        # Get this week's appointments
        week_appointments_stmt = select(func.count(Appointment.id)).where(
            and_(
                Appointment.start_time >= week_start,
                Appointment.start_time < week_end,
                Appointment.status.in_([
                    AppointmentStatus.PENDING,
                    AppointmentStatus.CONFIRMED
                ])
            )
        )
        week_appointments_result = await self.db.execute(week_appointments_stmt)
        week_appointments_count = week_appointments_result.scalar_one()

        # Get this month's appointments
        month_appointments_stmt = select(func.count(Appointment.id)).where(
            and_(
                Appointment.start_time >= month_start,
                Appointment.start_time < next_month,
                Appointment.status.in_([
                    AppointmentStatus.PENDING,
                    AppointmentStatus.CONFIRMED
                ])
            )
        )
        month_appointments_result = await self.db.execute(month_appointments_stmt)
        month_appointments_count = month_appointments_result.scalar_one()

        # Get pending payments
        pending_payments_stmt = select(func.count(Payment.id)).where(
            Payment.status == PaymentStatus.PENDING
        )
        pending_payments_result = await self.db.execute(pending_payments_stmt)
        pending_payments_count = pending_payments_result.scalar_one()

        # Get monthly revenue
        monthly_revenue_stmt = select(func.sum(Payment.amount)).where(
            and_(
                Payment.status == PaymentStatus.COMPLETED,
                Payment.completed_at >= month_start,
                Payment.completed_at < next_month
            )
        )
        monthly_revenue_result = await self.db.execute(monthly_revenue_stmt)
        monthly_revenue = monthly_revenue_result.scalar_one() or 0

        # Get upcoming overdue
        next_hour = datetime.utcnow() + timedelta(hours=1)
        overdue_stmt = select(func.count(Appointment.id)).where(
            and_(
                Appointment.start_time < next_hour,
                Appointment.status == AppointmentStatus.PENDING,
                Appointment.is_paid == False
            )
        )
        overdue_result = await self.db.execute(overdue_stmt)
        overdue_count = overdue_result.scalar_one()

        return {
            "today_appointments": today_appointments_count,
            "weekly_appointments": week_appointments_count,
            "monthly_appointments": month_appointments_count,
            "pending_payments": pending_payments_count,
            "monthly_revenue": monthly_revenue,
            "overdue_appointments": overdue_count,
            "current_date": datetime.utcnow(),
        }