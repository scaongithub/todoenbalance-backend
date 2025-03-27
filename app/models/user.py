"""User model for clients."""

import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """
    User model for clients booking nutrition consultations.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Personal information
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)

    # Authentication
    hashed_password = Column(String(255), nullable=True)
    is_social_login = Column(Boolean, default=False)
    social_provider = Column(String(50), nullable=True)  # "google", "facebook", etc.
    social_id = Column(String(255), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Health information (optional fields for better service)
    health_notes = Column(Text, nullable=True)

    # Relationships
    appointments = relationship("Appointment", back_populates="user", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, email={self.email}, name={self.full_name})>"