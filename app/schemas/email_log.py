"""Email log schemas for request and response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.email_log import EmailStatus, EmailType


class EmailLogBase(BaseModel):
    """Base schema for email log data."""

    recipient_email: EmailStr
    subject: str
    email_type: EmailType


class EmailLogCreate(EmailLogBase):
    """Schema for creating a new email log."""

    recipient_name: Optional[str] = None
    user_id: Optional[int] = None
    appointment_id: Optional[int] = None
    template_name: Optional[str] = None
    body_text: Optional[str] = None


class EmailLogUpdate(BaseModel):
    """Schema for updating an email log."""

    status: Optional[EmailStatus] = None
    provider_message_id: Optional[str] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


class EmailLogInDB(EmailLogBase):
    """Schema for email log data from database."""

    id: int
    recipient_name: Optional[str] = None
    user_id: Optional[int] = None
    appointment_id: Optional[int] = None
    template_name: Optional[str] = None
    status: EmailStatus
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class EmailLogOut(EmailLogBase):
    """Schema for email log data in responses."""

    id: int
    recipient_name: Optional[str] = None
    status: EmailStatus
    created_at: datetime
    sent_at: Optional[datetime] = None

    class Config:
        orm_mode = True