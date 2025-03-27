"""Token schemas for authentication."""

from typing import Optional

from pydantic import BaseModel


class Token(BaseModel):
    """Schema for access token response."""

    access_token: str
    token_type: str = "bearer"
    user_id: Optional[int] = None
    is_admin: bool = False


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str  # Subject (user ID)
    exp: int  # Expiration time
    is_admin: bool = False  # Whether this is an admin token