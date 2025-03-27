"""Security utilities for authentication and password handling."""

import secrets
from datetime import datetime, timedelta
from typing import Any, Optional, Union

from passlib.context import CryptContext
from jose import jwt

from app.config import settings
from app.core.exceptions import AuthenticationException

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token settings
ALGORITHM = "HS256"


def create_access_token(
        subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: Subject to encode in the token (usually user ID).
        expires_delta: Token expiration time. Defaults to settings.ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: Encoded JWT token.
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify that a plain password matches a hashed password.

    Args:
        plain_password: The plain text password.
        hashed_password: The hashed password to check against.

    Returns:
        bool: True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: The plain text password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def generate_password_reset_token(email: str) -> str:
    """
    Generate a password reset token.

    Args:
        email: Email address the token is for.

    Returns:
        str: Password reset token.
    """
    expire = datetime.utcnow() + timedelta(
        hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS
    )
    to_encode = {"exp": expire, "sub": email, "type": "password_reset"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_password_reset_token(token: str) -> str:
    """
    Verify a password reset token and return the email address.

    Args:
        token: The password reset token.

    Returns:
        str: The email address associated with the token.

    Raises:
        AuthenticationException: If the token is invalid or expired.
    """
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if decoded_token.get("type") != "password_reset":
            raise AuthenticationException("Invalid token type")
        return decoded_token["sub"]
    except jwt.JWTError:
        raise AuthenticationException("Invalid or expired token")


def generate_verification_token(email: str) -> str:
    """
    Generate an email verification token.

    Args:
        email: Email address to verify.

    Returns:
        str: Email verification token.
    """
    expire = datetime.utcnow() + timedelta(days=7)  # 7 days to verify email
    to_encode = {"exp": expire, "sub": email, "type": "email_verification"}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_email_token(token: str) -> str:
    """
    Verify an email verification token and return the email address.

    Args:
        token: The email verification token.

    Returns:
        str: The email address to verify.

    Raises:
        AuthenticationException: If the token is invalid or expired.
    """
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if decoded_token.get("type") != "email_verification":
            raise AuthenticationException("Invalid token type")
        return decoded_token["sub"]
    except jwt.JWTError:
        raise AuthenticationException("Invalid or expired token")


def generate_secure_random_string(length: int = 32) -> str:
    """
    Generate a cryptographically secure random string.

    Args:
        length: The length of the random string.

    Returns:
        str: A random string of the specified length.
    """
    return secrets.token_urlsafe(length)