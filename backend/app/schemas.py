"""Pydantic schemas for API request/response validation.

Used by FastAPI for body validation, response_model, and OpenAPI docs.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Shared user fields (email)."""

    email: EmailStr


class UserCreate(UserBase):
    """Payload to create a user profile linked to a Supabase auth user.

    Attributes:
        id: Supabase auth user UUID. Backend trusts Supabase for auth.
        email: User email address.
    """

    id: uuid.UUID = Field(
        ...,
        description="Supabase auth user UUID. Backend trusts Supabase for auth.",
    )


class UserRead(UserBase):
    """User as returned by the API (read-only fields)."""

    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


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

