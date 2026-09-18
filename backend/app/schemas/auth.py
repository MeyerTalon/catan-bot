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


class AuthConfirmRequest(BaseModel):
    """Request body for POST /auth/confirm.

    Attributes:
        email: Email used at signup.
        code: Verification code Cognito emailed to that address.
    """

    email: EmailStr
    code: str = Field(min_length=1, max_length=16)


class AuthResendConfirmationRequest(BaseModel):
    """Request body for POST /auth/resend-confirmation.

    Attributes:
        email: Email used at signup.
    """

    email: EmailStr


class AuthLogoutRequest(BaseModel):
    """Request body for POST /auth/logout.

    Attributes:
        refresh_token: Refresh token to revoke. its access tokens stop working too.
    """

    refresh_token: str


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


class AuthSignupResponse(BaseModel):
    """Payload returned by signup.

    Attributes:
        email: Address the account was created for.
        confirmation_required: True when Cognito emailed a verification code and
            the client must call /auth/confirm before logging in.
        session: Session tokens, only when the account was confirmed at once
            (local development against the emulator).
    """

    email: str
    confirmation_required: bool
    session: AuthSessionResponse | None = None


class AuthMessageResponse(BaseModel):
    """Acknowledgement for auth actions that return no session.

    Attributes:
        message: Human-readable outcome.
    """

    message: str
