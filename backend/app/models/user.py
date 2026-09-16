"""User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.game import GameSession


class User(Base):
    """Application-level user profile.

    Cognito holds authentication; we mirror the user id (UUID `sub`) here
    and attach profile / game data (e.g. game_sessions).

    Attributes:
        id: Primary key, UUID (matches Cognito `sub`).
        email: Unique email address.
        created_at: Timestamp when the record was created.
        game_sessions: Related GameSession records (cascade delete).
    """

    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    game_sessions: Mapped[list[GameSession]] = relationship(
        'GameSession', back_populates='user', cascade='all, delete-orphan'
    )
