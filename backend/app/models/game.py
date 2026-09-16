"""GameSession ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


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

    __tablename__ = 'game_sessions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    user: Mapped[User] = relationship('User', back_populates='game_sessions')
