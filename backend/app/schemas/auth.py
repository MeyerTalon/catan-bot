"""Auth API request schemas (login/signup via backend proxy to Supabase)."""

from pydantic import BaseModel, EmailStr


class AuthLoginRequest(BaseModel):
    """Request body for POST /auth/login."""

    email: EmailStr
    password: str


class AuthSignupRequest(BaseModel):
    """Request body for POST /auth/signup."""

    email: EmailStr
    password: str
    username: str | None = None
