"""Auth API request and response schemas (Cognito-backed login/signup)."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


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
        username: Optional display name stored on the Cognito user.
    """

    email: EmailStr
    password: str
    username: str | None = None


class AuthRefreshRequest(BaseModel):
    """Request body for POST /auth/refresh.

    Attributes:
        refresh_token: Cognito refresh token from a prior login/signup.
        username: Cognito username (email) required when the app client has a secret.
    """

    refresh_token: str
    username: str | None = None


class AuthUser(BaseModel):
    """Authenticated user identity returned with a session.

    Attributes:
        id: Cognito user UUID (`sub`).
        email: User email if present on the token.
        username: Display name if present on the token.
    """

    id: str
    email: str | None = None
    username: str | None = None


class AuthSessionResponse(BaseModel):
    """Session payload returned by login, signup, and refresh.

    Attributes:
        access_token: Cognito access token (send as Authorization: Bearer).
        refresh_token: Cognito refresh token.
        expires_in: Access token lifetime in seconds.
        token_type: Token type, always Bearer.
        user: Identity claims for the authenticated user.
        message: Optional note (e.g. email confirmation required).
    """

    access_token: str
    refresh_token: str = ''
    expires_in: int
    token_type: str = Field(default='Bearer')
    user: AuthUser
    message: str | None = None
