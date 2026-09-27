"""User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Application-level user profile.

    Cognito holds authentication; we mirror the user id (UUID `sub`) here
    and attach profile data.

    Attributes:
        id: Primary key, UUID (matches Cognito `sub`).
        email: Unique email address.
        username: Display name chosen at signup, if any.
        created_at: Timestamp when the record was created.
    """

    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    @property
    def display_name(self) -> str:
        """Name shown to other players: the username, else the email's local part."""
        return self.username or self.email.split('@', 1)[0]
