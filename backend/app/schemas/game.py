"""Game session API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field


class GameSessionBase(BaseModel):
    """Shared game session fields (state)."""

    state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Serialized Catan game state.",
    )


class GameSessionCreate(GameSessionBase):
    """Payload to create a game session (optional initial state)."""

    pass


class GameSessionRead(GameSessionBase):
    """Game session as returned by the API (read-only fields)."""

    id: int
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
