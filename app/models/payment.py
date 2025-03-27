"""Payment model for tracking payment transactions."""

import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class PaymentProvider(enum.Enum):
    """Enumeration of supported payment providers."""

    STRIPE = "stripe"
    PAYPAL = "paypal"


class PaymentStatus(enum.Enum):
    """Enumeration of possible payment statuses."""

    PENDING = "pending"  # Payment initiated but not completed
    COMPLETED = "completed"  # Payment successfully processed
    FAILED = "failed"  # Payment processing failed
    REFUNDED = "refunded"  # Payment was refunded
    CANCELLED = "cancelled"  # Payment was cancelled


class Payment(Base):
    """
    Payment model for tracking payment transactions.
    """

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # Relationship to user and appointment
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)

    # Payment details
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")

    # Payment processing details
    provider = Column(Enum(PaymentProvider), nullable=False)
    provider_payment_id = Column(String(255), nullable=True)  # ID from payment provider
    provider_transaction_id = Column(String(255), nullable=True)  # Transaction ID from provider

    # Status
    status = Column(
        Enum(PaymentStatus),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    # Additional payment information
    payment_method = Column(String(50), nullable=True)  # e.g., "credit_card", "paypal"
    payment_details = Column(Text, nullable=True)  # JSON-encoded payment details

    # Receipt and confirmation details
    receipt_url = Column(String(255), nullable=True)
    confirmation_sent = Column(DateTime, nullable=True)

    # Error details (if payment failed)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="payments")
    appointment = relationship("Appointment", back_populates="payments")

    def __repr__(self) -> str:
        """String representation of Payment."""
        return (
            f"<Payment(id={self.id}, user_id={self.user_id}, "
            f"appointment_id={self.appointment_id}, "
            f"amount={self.amount}, status={self.status})>"
        )