"""Admin model for system administrators."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.database import Base


class Admin(Base):
    """
    Admin model for staff who manage the backend system.
    """

    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)

    # Personal information
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)

    # Authentication
    hashed_password = Column(String(255), nullable=False)

    # Admin status and permissions
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        """String representation of Admin."""
        return f"<Admin(id={self.id}, email={self.email}, name={self.full_name})>"