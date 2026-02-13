"""Auth endpoints: login and signup (proxy to Supabase)."""

from typing import Any

from fastapi import APIRouter

from app.schemas.auth import AuthLoginRequest, AuthSignupRequest
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/login")
def login(payload: AuthLoginRequest) -> dict[str, Any]:
    """Log in with email and password via Supabase Auth.

    Args:
        payload: Login request containing email and password.

    Returns:
        Dictionary containing session tokens (access_token, refresh_token) and user info.

    Raises:
        HTTPException: 400 if login fails (invalid credentials, etc.).
    """
    return auth_service.login(payload)


@router.post("/signup")
def signup(payload: AuthSignupRequest) -> dict[str, Any]:
    """Sign up with email and optional username via Supabase Auth.

    Args:
        payload: Signup request containing email, password, and optional username.

    Returns:
        Dictionary containing session tokens (access_token, refresh_token) and user info,
        or confirmation message if email verification is required.

    Raises:
        HTTPException: 400 if signup fails (email already exists, weak password, etc.).
    """
    return auth_service.signup(payload)
