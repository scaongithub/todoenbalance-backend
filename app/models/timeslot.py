"""TimeSlot models for managing availability."""

import enum
from datetime import datetime, time

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Integer,
    String,
    Time,
)
from sqlalchemy.sql import func

from app.database import Base


class DayOfWeek(enum.IntEnum):
    """Enumeration for days of the week (ISO format: 1=Monday, 7=Sunday)."""

    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class TimeSlot(Base):
    """
    TimeSlot model for specific available time slots.

    This model represents individual available time slots
    that can be booked for appointments.
    """

    __tablename__ = "timeslots"

    id = Column(Integer, primary_key=True, index=True)

    # Time slot details
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    duration = Column(Integer, nullable=False, default=30)  # in minutes

    # Status
    is_available = Column(Boolean, default=True)
    is_booked = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of TimeSlot."""
        return (
            f"<TimeSlot(id={self.id}, start={self.start_time}, "
            f"available={self.is_available}, booked={self.is_booked})>"
        )


class RecurringTimeSlot(Base):
    """
    RecurringTimeSlot model for defining recurring availability patterns.

    This model defines patterns like "every Monday from 9:00 to 12:00"
    which can be used to automatically generate TimeSlot instances.
    """

    __tablename__ = "recurring_timeslots"

    id = Column(Integer, primary_key=True, index=True)

    # Recurring pattern
    day_of_week = Column(Enum(DayOfWeek), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)

    # Slot duration in minutes
    duration = Column(Integer, nullable=False, default=30)

    # Validity period
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date, nullable=True)  # Null means indefinitely

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of RecurringTimeSlot."""
        return (
            f"<RecurringTimeSlot(id={self.id}, day={self.day_of_week.name}, "
            f"start={self.start_time}, end={self.end_time}, active={self.is_active})>"
        )


class BlockedTimeSlot(Base):
    """
    BlockedTimeSlot model for defining periods when no appointments are available.

    This can be used for vacations, holidays, or other unavailable periods.
    """

    __tablename__ = "blocked_timeslots"

    id = Column(Integer, primary_key=True, index=True)

    # Blocked period
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)

    # Reason for blocking (e.g., "Vacation", "Holiday", etc.)
    reason = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        """String representation of BlockedTimeSlot."""
        return (
            f"<BlockedTimeSlot(id={self.id}, start={self.start_datetime}, "
            f"end={self.end_datetime}, reason={self.reason})>"
        )