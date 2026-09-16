"""Auth endpoints: login, signup, and refresh via Amazon Cognito."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.auth import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthSessionResponse,
    AuthSignupRequest,
)
from app.services.auth_service import auth_service

router = APIRouter()


@router.post('/login', response_model=AuthSessionResponse)
def login(
    payload: AuthLoginRequest,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    """Log in with email and password via Cognito.

    Args:
        payload: Login request containing email and password.
        db: Database session (injected dependency).

    Returns:
        Session tokens and user identity.

    Raises:
        HTTPException: 400 if login fails; 503 if Cognito is not configured.
    """
    return auth_service.login(db, payload)


@router.post('/signup', response_model=AuthSessionResponse)
def signup(
    payload: AuthSignupRequest,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    """Sign up with email and optional username via Cognito.

    Args:
        payload: Signup request containing email, password, and optional username.
        db: Database session (injected dependency).

    Returns:
        Session tokens and user identity.

    Raises:
        HTTPException: 400 if signup fails; 503 if Cognito is not configured.
    """
    return auth_service.signup(db, payload)


@router.post('/refresh', response_model=AuthSessionResponse)
def refresh(
    payload: AuthRefreshRequest,
    db: Session = Depends(get_db),
) -> AuthSessionResponse:
    """Refresh an access token using a Cognito refresh token.

    Args:
        payload: Refresh request.
        db: Database session (injected dependency).

    Returns:
        New session tokens.

    Raises:
        HTTPException: 400 if refresh fails; 503 if Cognito is not configured.
    """
    return auth_service.refresh(db, payload)
