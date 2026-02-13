"""User API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    """Shared user fields (email).

    Attributes:
        email: User email address.
    """

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
    """User as returned by the API (read-only fields).

    Attributes:
        id: User UUID (primary key).
        email: User email address (inherited from UserBase).
        created_at: Timestamp when the user was created.
    """

    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
