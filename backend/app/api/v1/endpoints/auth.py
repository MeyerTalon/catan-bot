"""Auth endpoints: login and signup (proxy to Supabase)."""

from typing import Any

from fastapi import APIRouter

from app.schemas.auth import AuthLoginRequest, AuthSignupRequest
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/login")
def login(payload: AuthLoginRequest) -> dict[str, Any]:
    """Log in with email and password via Supabase Auth. Returns session tokens."""
    return auth_service.login(payload)


@router.post("/signup")
def signup(payload: AuthSignupRequest) -> dict[str, Any]:
    """Sign up with email and optional username via Supabase Auth. Returns session (or confirmation)."""
    return auth_service.signup(payload)
