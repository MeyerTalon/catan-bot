"""Security utilities: JWT validation for Supabase tokens.

Validates JWTs issued by Supabase Auth to protect backend routes.
"""

from __future__ import annotations

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


def decode_jwt(token: str) -> dict:
    """Decode and validate a Supabase JWT token.

    Args:
        token: JWT access token from Supabase Auth.

    Returns:
        Decoded token payload with user info.

    Raises:
        HTTPException: 401 if token is invalid, expired, or missing required claims.
    """
    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JWT validation not configured (missing SUPABASE_JWT_SECRET).",
        )

    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Supabase doesn't use aud claim by default
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
        )


def get_user_id_from_token(token: str) -> str:
    """Extract user ID from a Supabase JWT token.

    Args:
        token: JWT access token from Supabase Auth.

    Returns:
        User ID (UUID as string) from the token's 'sub' claim.

    Raises:
        HTTPException: 401 if token is invalid or missing 'sub' claim.
    """
    payload = decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user ID (sub claim).",
        )
    return user_id
