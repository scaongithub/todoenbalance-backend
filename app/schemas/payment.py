"""Payment schemas for request and response validation."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator

from app.models.payment import PaymentProvider, PaymentStatus


class PaymentBase(BaseModel):
    """Base schema for payment data."""

    amount: float = Field(..., gt=0)
    currency: str = Field("EUR", min_length=3, max_length=3)
    provider: PaymentProvider


class PaymentCreate(PaymentBase):
    """Schema for creating a new payment."""

    appointment_id: int
    provider: PaymentProvider
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @validator('amount')
    def amount_must_be_positive(cls, v):
        """Validate that amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be greater than 0")
        return v


class PaymentUpdate(BaseModel):
    """Schema for updating a payment."""

    status: Optional[PaymentStatus] = None
    provider_payment_id: Optional[str] = None
    provider_transaction_id: Optional[str] = None
    payment_method: Optional[str] = None
    receipt_url: Optional[str] = None
    error_message: Optional[str] = None


class PaymentInDB(PaymentBase):
    """Schema for payment data from database."""

    id: int
    user_id: int
    appointment_id: int
    status: PaymentStatus
    provider_payment_id: Optional[str] = None
    provider_transaction_id: Optional[str] = None
    payment_method: Optional[str] = None
    payment_details: Optional[str] = None
    receipt_url: Optional[str] = None
    confirmation_sent: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class PaymentOut(PaymentBase):
    """Schema for payment data in responses."""

    id: int
    user_id: int
    appointment_id: int
    status: PaymentStatus
    payment_method: Optional[str] = None
    receipt_url: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        orm_mode = True


class PaymentIntentCreate(BaseModel):
    """Schema for creating a payment intent."""

    appointment_id: int
    provider: PaymentProvider = PaymentProvider.STRIPE
    return_url: Optional[str] = None


class PaymentIntentResponse(BaseModel):
    """Schema for payment intent response."""

    payment_id: int
    provider: PaymentProvider
    client_secret: Optional[str] = None
    payment_url: Optional[str] = None
    provider_payment_id: str
    amount: float
    currency: str
    status: str