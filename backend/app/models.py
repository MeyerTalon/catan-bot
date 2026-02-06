"""SQLAlchemy ORM models for users and game sessions.

Aligns with database/migrations schema. User id mirrors Supabase auth.users.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .db import Base


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


class GameSession(Base):
    """A single Catan game instance for a user.

    State is stored as JSONB; the schema can be normalized later if needed.

    Attributes:
        id: Primary key, auto-increment.
        user_id: Foreign key to users.id (CASCADE on delete).
        created_at: When the session was created.
        updated_at: When the session was last updated.
        state: Serialized Catan game state (JSON).
        user: Related User instance.
    """

    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    state: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    user: Mapped[User] = relationship("User", back_populates="game_sessions")

