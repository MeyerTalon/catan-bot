"""Security utilities: JWT validation for Cognito access tokens.

Validates RS256 JWTs issued by Amazon Cognito to protect backend routes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    """Build a cached JWKS client for the configured Cognito user pool.

    Returns:
        PyJWKClient pointed at the pool's JWKS URL.

    Raises:
        HTTPException: 503 if Cognito is not configured.
    """
    settings = get_settings()
    if not settings.cognito_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='JWT validation not configured (missing Cognito settings).',
        )
    return jwt.PyJWKClient(settings.jwks_url)


def decode_jwt(token: str) -> dict[str, Any]:
    """Decode and validate a Cognito access token.

    id tokens are rejected: they are meant for the client, and accepting them
    as bearer credentials would let a leaked id token reach the api.

    Args:
        token: JWT issued by Cognito.

    Returns:
        Decoded token payload.

    Raises:
        HTTPException: 401 if the token is invalid, expired, not an access token,
            or issued to another app client; 503 if Cognito is not configured.
    """
    settings = get_settings()
    if not settings.cognito_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='JWT validation not configured (missing Cognito settings).',
        )

    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        payload: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=['RS256'],
            issuer=settings.cognito_issuer,
            # access tokens carry client_id rather than aud; it is checked below
            options={'verify_aud': False, 'require': ['exp', 'iat', 'sub']},
        )
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token has expired.',
        ) from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token.',
        ) from exc

    if payload.get('token_use') != 'access':
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token use.',
        )

    if payload.get('client_id') != settings.cognito_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token client does not match.',
        )

    return payload


def get_user_id_from_token(token: str) -> str:
    """Extract the Cognito user id (`sub`) from a JWT.

    Args:
        token: JWT access token from Cognito.

    Returns:
        User ID (UUID as string) from the token's 'sub' claim.

    Raises:
        HTTPException: 401 if the token is invalid or missing 'sub'.
    """
    payload = decode_jwt(token)
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token missing user ID (sub claim).',
        )
    return str(user_id)
