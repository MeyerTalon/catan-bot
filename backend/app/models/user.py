"""User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import UUID, DateTime, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Application-level user profile.

    Supabase auth.users holds authentication; we mirror the user id (UUID) here
    and attach profile / game data (e.g. game_sessions).

    Attributes:
        id: Primary key, UUID (matches Supabase auth user id).
        email: Unique email address.
        created_at: Timestamp when the record was created.
        game_sessions: Related GameSession records (cascade delete).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    game_sessions: Mapped[list["GameSession"]] = relationship(
        "GameSession", back_populates="user", cascade="all, delete-orphan"
    )
