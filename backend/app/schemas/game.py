"""Game session API schemas."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

# generous for a serialized board; keeps a single request from filling the table
MAX_STATE_BYTES = 64 * 1024


class GameSessionBase(BaseModel):
    """Shared game session fields (state).

    Attributes:
        state: Serialized Catan game state as dictionary.
    """

    state: dict[str, Any] = Field(
        default_factory=dict,
        description='Serialized Catan game state.',
    )

    @field_validator('state')
    @classmethod
    def _state_fits(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Reject a state whose JSON encoding exceeds MAX_STATE_BYTES.

        Args:
            value: Parsed state dict.

        Returns:
            The same dict when it fits.

        Raises:
            ValueError: If the serialized state is too large.
        """
        size = len(json.dumps(value, separators=(',', ':')).encode('utf-8'))
        if size > MAX_STATE_BYTES:
            raise ValueError(f'state exceeds {MAX_STATE_BYTES} bytes ({size}).')
        return value


class GameSessionCreate(GameSessionBase):
    """Payload to create a game session (optional initial state).

    Attributes:
        state: Serialized Catan game state as dictionary (inherited from GameSessionBase).
    """


class GameSessionRead(GameSessionBase):
    """Game session as returned by the API (read-only fields).

    Attributes:
        id: Game session ID (primary key).
        user_id: User UUID who owns the session.
        state: Serialized Catan game state as dictionary (inherited from GameSessionBase).
        created_at: Timestamp when the session was created.
        updated_at: Timestamp when the session was last updated.
    """

    id: int
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
