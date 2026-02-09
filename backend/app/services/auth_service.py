"""Auth service: proxy to Supabase Auth for login/signup."""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.auth import AuthLoginRequest, AuthSignupRequest


def _supabase_auth_url(path: str) -> str:
    """Build Supabase Auth API URL."""
    settings = get_settings()
    if not settings.supabase_project_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth not configured (SUPABASE_URL / SUPABASE_ANON_KEY).",
        )
    return f"{settings.supabase_project_url.rstrip('/')}/auth/v1{path}"


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "apikey": settings.supabase_anon_key or "",
        "Content-Type": "application/json",
    }


def login(payload: AuthLoginRequest) -> dict[str, Any]:
    """Log in with email and password via Supabase Auth. Returns session tokens."""
    url = _supabase_auth_url("/token?grant_type=password")
    body = {"email": payload.email, "password": payload.password}
    with httpx.Client() as client:
        resp = client.post(url, json=body, headers=_headers())
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        msg = data.get("error_description") or data.get("msg") or resp.text or "Login failed"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return data


def signup(payload: AuthSignupRequest) -> dict[str, Any]:
    """Sign up via Supabase Auth. Returns session (or confirmation)."""
    url = _supabase_auth_url("/signup")
    body: dict[str, Any] = {"email": payload.email, "password": payload.password}
    if payload.username:
        body["data"] = {"username": payload.username}
    with httpx.Client() as client:
        resp = client.post(url, json=body, headers=_headers())
    data = resp.json() if resp.content else {}
    if resp.status_code >= 400:
        msg = data.get("error_description") or data.get("msg") or resp.text or "Signup failed"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    return data


class AuthService:
    login = staticmethod(login)
    signup = staticmethod(signup)


auth_service = AuthService()
