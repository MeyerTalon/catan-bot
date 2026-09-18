"""Auth endpoints: signup, confirmation, login, refresh, and logout via Amazon Cognito."""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import bearer_token, get_db
from app.core.rate_limit import rate_limited
from app.schemas.auth import (
    AuthConfirmRequest,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthMessageResponse,
    AuthRefreshRequest,
    AuthResendConfirmationRequest,
    AuthSessionResponse,
    AuthSignupRequest,
    AuthSignupResponse,
)
from app.services.auth_service import auth_service

# per client ip per minute; cognito has its own lockout, this keeps floods off it
credential_limit = rate_limited(limit=10)
refresh_limit = rate_limited(limit=30)

router = APIRouter()


@router.post(
    '/login',
    response_model=AuthSessionResponse,
    dependencies=[Depends(credential_limit)],
)
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
        HTTPException: 400 if login fails; 429 when rate limited; 503 if Cognito is not configured.
    """
    return auth_service.login(db, payload)


@router.post(
    '/signup',
    response_model=AuthSignupResponse,
    dependencies=[Depends(credential_limit)],
)
def signup(
    payload: AuthSignupRequest,
    db: Session = Depends(get_db),
) -> AuthSignupResponse:
    """Sign up with email and optional username via Cognito.

    Args:
        payload: Signup request containing email, password, and optional username.
        db: Database session (injected dependency).

    Returns:
        Whether email confirmation is pending, plus a session when it is not.

    Raises:
        HTTPException: 400 if signup fails; 429 when rate limited; 503 if Cognito is not configured.
    """
    return auth_service.signup(db, payload)


@router.post(
    '/confirm',
    response_model=AuthMessageResponse,
    dependencies=[Depends(credential_limit)],
)
def confirm(payload: AuthConfirmRequest) -> AuthMessageResponse:
    """Confirm a signup with the code Cognito emailed.

    Args:
        payload: Email and confirmation code.

    Returns:
        Acknowledgement; log in afterwards.

    Raises:
        HTTPException: 400 if the code is wrong or expired; 429 when rate limited.
    """
    return auth_service.confirm(payload)


@router.post(
    '/resend-confirmation',
    response_model=AuthMessageResponse,
    dependencies=[Depends(credential_limit)],
)
def resend_confirmation(
    payload: AuthResendConfirmationRequest,
) -> AuthMessageResponse:
    """Email a fresh confirmation code.

    Args:
        payload: Email used at signup.

    Returns:
        Acknowledgement, identical whether or not the account exists.

    Raises:
        HTTPException: 400 on a Cognito error; 429 when rate limited.
    """
    return auth_service.resend_confirmation(payload)


@router.post(
    '/refresh',
    response_model=AuthSessionResponse,
    dependencies=[Depends(refresh_limit)],
)
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
        HTTPException: 400 if refresh fails; 429 when rate limited; 503 if Cognito is not configured.
    """
    return auth_service.refresh(db, payload)


@router.post(
    '/logout',
    response_model=AuthMessageResponse,
    dependencies=[Depends(refresh_limit)],
)
def logout(
    payload: AuthLogoutRequest,
    authorization: str | None = Header(default=None, alias='Authorization'),
) -> AuthMessageResponse:
    """Revoke the refresh token and sign out the current session.

    the bearer token is optional and not validated: an expired access token
    must still be able to log out.

    Args:
        payload: Refresh token to revoke.
        authorization: Optional "Bearer <token>" header.

    Returns:
        Acknowledgement.

    Raises:
        HTTPException: 429 when rate limited; 503 if Cognito is not configured.
    """
    return auth_service.logout(payload, bearer_token(authorization))
