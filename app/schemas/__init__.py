"""Pydantic schemas for request/response validation."""

from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    UserOut,
)
from app.schemas.admin import (
    AdminBase,
    AdminCreate,
    AdminUpdate,
    AdminInDB,
    AdminOut,
)
from app.schemas.appointment import (
    AppointmentBase,
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentInDB,
    AppointmentOut,
)
from app.schemas.timeslot import (
    TimeSlotBase,
    TimeSlotCreate,
    TimeSlotUpdate,
    TimeSlotInDB,
    TimeSlotOut,
    RecurringTimeSlotBase,
    RecurringTimeSlotCreate,
    RecurringTimeSlotUpdate,
    RecurringTimeSlotInDB,
    RecurringTimeSlotOut,
    BlockedTimeSlotBase,
    BlockedTimeSlotCreate,
    BlockedTimeSlotUpdate,
    BlockedTimeSlotInDB,
    BlockedTimeSlotOut,
)
from app.schemas.payment import (
    PaymentBase,
    PaymentCreate,
    PaymentUpdate,
    PaymentInDB,
    PaymentOut,
)
from app.schemas.email_log import (
    EmailLogBase,
    EmailLogCreate,
    EmailLogUpdate,
    EmailLogInDB,
    EmailLogOut,
)
from app.schemas.token import (
    Token,
    TokenPayload,
)

__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "UserOut",
    "AdminBase",
    "AdminCreate",
    "AdminUpdate",
    "AdminInDB",
    "AdminOut",
    "AppointmentBase",
    "AppointmentCreate",
    "AppointmentUpdate",
    "AppointmentInDB",
    "AppointmentOut",
    "TimeSlotBase",
    "TimeSlotCreate",
    "TimeSlotUpdate",
    "TimeSlotInDB",
    "TimeSlotOut",
    "RecurringTimeSlotBase",
    "RecurringTimeSlotCreate",
    "RecurringTimeSlotUpdate",
    "RecurringTimeSlotInDB",
    "RecurringTimeSlotOut",
    "BlockedTimeSlotBase",
    "BlockedTimeSlotCreate",
    "BlockedTimeSlotUpdate",
    "BlockedTimeSlotInDB",
    "BlockedTimeSlotOut",
    "PaymentBase",
    "PaymentCreate",
    "PaymentUpdate",
    "PaymentInDB",
    "PaymentOut",
    "EmailLogBase",
    "EmailLogCreate",
    "EmailLogUpdate",
    "EmailLogInDB",
    "EmailLogOut",
    "Token",
    "TokenPayload",
]