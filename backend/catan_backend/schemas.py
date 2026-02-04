from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    """Payload to create a user profile (linked to Supabase auth user)."""

    id: uuid.UUID = Field(
        ...,
        description="Supabase auth user UUID. Backend trusts Supabase for auth.",
    )


class UserRead(UserBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class GameSessionBase(BaseModel):
    state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Serialized Catan game state.",
    )


class GameSessionCreate(GameSessionBase):
    pass


class GameSessionRead(GameSessionBase):
    id: int
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

