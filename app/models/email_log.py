"""Email log model for tracking email communications."""

import enum
from datetime import datetime

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
from sqlalchemy.sql import func

from app.database import Base


class EmailType(enum.Enum):
    """Enumeration of email types sent by the system."""

    BOOKING_CONFIRMATION = "booking_confirmation"
    APPOINTMENT_REMINDER = "appointment_reminder"
    PAYMENT_RECEIPT = "payment_receipt"
    CANCELLATION_NOTICE = "cancellation_notice"
    PASSWORD_RESET = "password_reset"
    ADMIN_NOTIFICATION = "admin_notification"
    WELCOME = "welcome"
    GENERAL = "general"


class EmailStatus(enum.Enum):
    """Enumeration of email delivery statuses."""

    PENDING = "pending"  # Email queued for sending
    SENT = "sent"  # Email successfully sent
    DELIVERED = "delivered"  # Email confirmed delivered (if tracking available)
    FAILED = "failed"  # Email sending failed
    OPENED = "opened"  # Email was opened by recipient (if tracking available)
    CLICKED = "clicked"  # Links in email were clicked (if tracking available)


class EmailLog(Base):
    """
    EmailLog model for tracking all email communications.
    """

    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)

    # Recipient information
    recipient_email = Column(String(255), nullable=False)
    recipient_name = Column(String(255), nullable=True)

    # Optional relation to user (may be null for system emails not tied to users)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Optional relation to appointment (may be null for emails not tied to appointments)
    appointment_id = Column(
        Integer, ForeignKey("appointments.id", ondelete="SET NULL"), nullable=True
    )

    # Email content
    subject = Column(String(255), nullable=False)
    email_type = Column(Enum(EmailType), nullable=False)
    template_name = Column(String(255), nullable=True)
    body_text = Column(Text, nullable=True)  # For logging plain text version

    # Delivery information
    status = Column(
        Enum(EmailStatus),
        nullable=False,
        default=EmailStatus.PENDING,
    )
    provider_message_id = Column(String(255), nullable=True)  # ID from email service provider
    error_message = Column(Text, nullable=True)

    # Delivery tracking (if available from provider)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    sent_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        """String representation of EmailLog."""
        return (
            f"<EmailLog(id={self.id}, recipient={self.recipient_email}, "
            f"type={self.email_type}, status={self.status})>"
        )