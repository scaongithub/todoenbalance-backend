"""Admin schemas for request and response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class AdminBase(BaseModel):
    """Base schema for admin data."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


class AdminCreate(AdminBase):
    """Schema for creating a new admin."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)
    is_superuser: bool = False


class AdminUpdate(AdminBase):
    """Schema for updating an admin."""

    password: Optional[str] = Field(None, min_length=8)


class AdminInDB(AdminBase):
    """Schema for admin data from database."""

    id: int
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True


class AdminOut(AdminBase):
    """Schema for admin data in responses."""

    id: int
    email: EmailStr
    full_name: str
    is_superuser: bool
    created_at: datetime

    class Config:
        orm_mode = True