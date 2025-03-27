"""User schemas for request and response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class UserBase(BaseModel):
    """Base schema for user data."""

    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = True


class UserCreate(UserBase):
    """Schema for creating a new user."""

    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=8)
    is_social_login: Optional[bool] = False
    social_provider: Optional[str] = None
    social_id: Optional[str] = None

    @validator('password', always=True)
    def password_required_if_not_social(cls, v, values):
        """Validate that password is provided if not using social login."""
        if not values.get('is_social_login', False) and not v:
            raise ValueError('Password is required for non-social login users')
        return v


class UserUpdate(UserBase):
    """Schema for updating a user."""

    password: Optional[str] = Field(None, min_length=8)
    health_notes: Optional[str] = None


class UserInDB(UserBase):
    """Schema for user data from database."""

    id: int
    hashed_password: Optional[str] = None
    is_social_login: bool = False
    social_provider: Optional[str] = None
    social_id: Optional[str] = None
    is_verified: bool = False
    health_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserOut(UserBase):
    """Schema for user data in responses."""

    id: int
    full_name: str
    email: EmailStr
    is_verified: bool
    created_at: datetime

    class Config:
        orm_mode = True