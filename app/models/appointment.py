"""Appointment model for booking nutrition consultations."""

import enum
from datetime import datetime, timedelta

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AppointmentStatus(enum.Enum):
    """Enumeration of possible appointment statuses."""

    PENDING = "pending"  # Appointment created but not yet paid
    CONFIRMED = "confirmed"  # Payment successful, appointment confirmed
    CANCELLED = "cancelled"  # Appointment cancelled by user or admin
    COMPLETED = "completed"  # Appointment has been conducted
    NO_SHOW = "no_show"  # User didn't attend the appointment


class AppointmentType(enum.Enum):
    """Enumeration of possible appointment types."""

    INITIAL_CONSULTATION = "initial_consultation"  # First consultation (30 min)
    COMPREHENSIVE_CONSULTATION = "comprehensive_consultation"  # Detailed consultation (60 min)
    FOLLOW_UP = "follow_up"  # Follow-up appointment (30 min)


class Appointment(Base):
    """
    Appointment model for scheduling nutrition consultations.
    """

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    # Appointment details
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # Duration is stored in minutes
    duration = Column(Integer, nullable=False, default=30)

    # Type and status
    appointment_type = Column(
        Enum(AppointmentType),
        nullable=False,
        default=AppointmentType.INITIAL_CONSULTATION,
    )
    status = Column(
        Enum(AppointmentStatus),
        nullable=False,
        default=AppointmentStatus.PENDING,
    )

    # User notes and admin notes
    user_notes = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)

    # Meeting details
    meeting_url = Column(String(255), nullable=True)

    # Reminders
    reminder_sent = Column(Boolean, default=False)

    # Payment information (linked to payment model)
    is_paid = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="appointments")
    payments = relationship("Payment", back_populates="appointment", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of Appointment."""
        return (
            f"<Appointment(id={self.id}, user_id={self.user_id}, "
            f"start_time={self.start_time}, status={self.status})>"
        )

    @property
    def is_upcoming(self) -> bool:
        """Check if the appointment is in the future."""
        return self.start_time > datetime.utcnow()

    @property
    def is_cancellable(self) -> bool:
        """
        Check if the appointment can be cancelled.

        Appointments can be cancelled if:
        1. They are in the future
        2. They are not already cancelled
        3. They are at least 24 hours away
        """
        return (
                self.status not in [AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED]
                and self.start_time > (datetime.utcnow() + timedelta(hours=24))
        )