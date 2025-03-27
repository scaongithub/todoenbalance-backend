"""Time slot schemas for request and response validation."""

from datetime import datetime, time, date
from typing import Optional

from pydantic import BaseModel, Field, validator

from app.models.timeslot import DayOfWeek


class TimeSlotBase(BaseModel):
    """Base schema for time slot data."""

    start_time: datetime
    end_time: datetime
    duration: int = Field(30, description="Duration in minutes")
    is_available: bool = True


class TimeSlotCreate(TimeSlotBase):
    """Schema for creating a new time slot."""

    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        """Validate that end time is after start time."""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("End time must be after start time")
        return v


class TimeSlotUpdate(BaseModel):
    """Schema for updating a time slot."""

    is_available: Optional[bool] = None
    is_booked: Optional[bool] = None


class TimeSlotInDB(TimeSlotBase):
    """Schema for time slot data from database."""

    id: int
    is_booked: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TimeSlotOut(TimeSlotBase):
    """Schema for time slot data in responses."""

    id: int
    is_booked: bool

    class Config:
        orm_mode = True


class RecurringTimeSlotBase(BaseModel):
    """Base schema for recurring time slot data."""

    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    duration: int = Field(30, ge=15, le=120, description="Duration in minutes")
    valid_from: date
    valid_until: Optional[date] = None
    is_active: bool = True


class RecurringTimeSlotCreate(RecurringTimeSlotBase):
    """Schema for creating a new recurring time slot."""

    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        """Validate that end time is after start time."""
        if 'start_time' in values and v <= values['start_time']:
            raise ValueError("End time must be after start time")
        return v

    @validator('valid_until')
    def valid_until_must_be_after_valid_from(cls, v, values):
        """Validate that valid_until is after valid_from if provided."""
        if v is not None and 'valid_from' in values and v <= values['valid_from']:
            raise ValueError("Valid until date must be after valid from date")
        return v


class RecurringTimeSlotUpdate(BaseModel):
    """Schema for updating a recurring time slot."""

    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration: Optional[int] = Field(None, ge=15, le=120, description="Duration in minutes")
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    is_active: Optional[bool] = None


class RecurringTimeSlotInDB(RecurringTimeSlotBase):
    """Schema for recurring time slot data from database."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class RecurringTimeSlotOut(RecurringTimeSlotBase):
    """Schema for recurring time slot data in responses."""

    id: int

    class Config:
        orm_mode = True


class BlockedTimeSlotBase(BaseModel):
    """Base schema for blocked time slot data."""

    start_datetime: datetime
    end_datetime: datetime
    reason: Optional[str] = None


class BlockedTimeSlotCreate(BlockedTimeSlotBase):
    """Schema for creating a new blocked time slot."""

    @validator('end_datetime')
    def end_time_must_be_after_start_time(cls, v, values):
        """Validate that end time is after start time."""
        if 'start_datetime' in values and v <= values['start_datetime']:
            raise ValueError("End datetime must be after start datetime")
        return v


class BlockedTimeSlotUpdate(BaseModel):
    """Schema for updating a blocked time slot."""

    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    reason: Optional[str] = None


class BlockedTimeSlotInDB(BlockedTimeSlotBase):
    """Schema for blocked time slot data from database."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class BlockedTimeSlotOut(BlockedTimeSlotBase):
    """Schema for blocked time slot data in responses."""

    id: int

    class Config:
        orm_mode = True