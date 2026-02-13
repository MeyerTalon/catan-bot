"""Auth API request schemas (login/signup via backend proxy to Supabase)."""

from pydantic import BaseModel, EmailStr


class AuthLoginRequest(BaseModel):
    """Request body for POST /auth/login.

    Attributes:
        email: User email address.
        password: User password.
    """

    email: EmailStr
    password: str


class AuthSignupRequest(BaseModel):
    """Request body for POST /auth/signup.

    Attributes:
        email: User email address.
        password: User password.
        username: Optional username for the user profile.
    """

    email: EmailStr
    password: str
    username: str | None = None
