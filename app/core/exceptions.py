"""Custom exceptions for the application."""

from fastapi import status


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, detail: str = "An application error occurred"):
        self.detail = detail
        super().__init__(self.detail)


class APIException(AppException):
    """Exception for API errors with status code."""

    def __init__(
            self, detail: str = "An API error occurred",
            status_code: int = status.HTTP_400_BAD_REQUEST
    ):
        self.status_code = status_code
        super().__init__(detail)


class DatabaseException(AppException):
    """Exception for database errors."""

    def __init__(self, detail: str = "A database error occurred"):
        super().__init__(detail)


class AuthenticationException(APIException):
    """Exception for authentication errors."""

    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail, status_code=status.HTTP_401_UNAUTHORIZED)


class ForbiddenException(APIException):
    """Exception for access forbidden errors."""

    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(detail, status_code=status.HTTP_403_FORBIDDEN)


class NotFoundException(APIException):
    """Exception for resource not found errors."""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status_code=status.HTTP_404_NOT_FOUND)


class ConflictException(APIException):
    """Exception for resource conflict errors."""

    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(detail, status_code=status.HTTP_409_CONFLICT)


class ValidationException(APIException):
    """Exception for validation errors."""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class PaymentException(APIException):
    """Exception for payment processing errors."""

    def __init__(self, detail: str = "Payment processing error"):
        super().__init__(detail, status_code=status.HTTP_400_BAD_REQUEST)


class EmailException(AppException):
    """Exception for email sending errors."""

    def __init__(self, detail: str = "Email sending error"):
        super().__init__(detail)


class SchedulingException(APIException):
    """Exception for scheduling conflicts or errors."""

    def __init__(self, detail: str = "Scheduling error"):
        super().__init__(detail, status_code=status.HTTP_400_BAD_REQUEST)


class DoubleBookingException(SchedulingException):
    """Exception for attempted double booking of a time slot."""

    def __init__(self, detail: str = "This time slot is already booked"):
        super().__init__(detail)