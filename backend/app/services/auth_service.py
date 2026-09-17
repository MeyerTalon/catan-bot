"""Auth service: Amazon Cognito login, signup, and token refresh."""

from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from typing import Any, NoReturn

import boto3
import jwt
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.crud.user import user_crud
from app.models.user import User
from app.schemas.auth import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthSessionResponse,
    AuthSignupRequest,
    AuthUser,
)


def _cognito_client() -> Any:
    """Return a boto3 Cognito IdP client.

    Returns:
        boto3 Cognito Identity Provider client.

    Raises:
        HTTPException: 503 if Cognito is not configured.
    """
    settings = get_settings()
    if not settings.cognito_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='Auth not configured (COGNITO_USER_POOL_ID / COGNITO_CLIENT_ID).',
        )
    return boto3.client(
        'cognito-idp',
        region_name=settings.cognito_region,
        endpoint_url=settings.cognito_endpoint_url,
    )


def _secret_hash(username: str, settings: Settings) -> str | None:
    """Compute Cognito SECRET_HASH when the app client has a secret.

    Args:
        username: Cognito username (email in this app).
        settings: Application settings.

    Returns:
        Base64 HMAC digest, or None when the client has no secret.
    """
    if not settings.cognito_client_secret or not settings.cognito_client_id:
        return None
    digest = hmac.new(
        settings.cognito_client_secret.encode('utf-8'),
        f'{username}{settings.cognito_client_id}'.encode(),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode('utf-8')


def _auth_parameters(
    username: str, extra: dict[str, str] | None = None
) -> dict[str, str]:
    """Build InitiateAuth AuthParameters, including SECRET_HASH when needed.

    Args:
        username: Cognito username.
        extra: Additional auth parameters (PASSWORD, REFRESH_TOKEN, ...).

    Returns:
        Dict suitable for boto3 initiate_auth AuthParameters.
    """
    params: dict[str, str] = dict(extra or {})
    secret_hash = _secret_hash(username, get_settings())
    if secret_hash:
        params['SECRET_HASH'] = secret_hash
    return params


def _raise_cognito_error(exc: ClientError, fallback: str) -> NoReturn:
    """Map a Cognito ClientError to an HTTPException.

    Args:
        exc: boto3 client error.
        fallback: Message used when Cognito does not provide one.

    Raises:
        HTTPException: 400 with Cognito's error message.
    """
    error = exc.response.get('Error', {})
    message = error.get('Message') or fallback
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, detail=message
    ) from exc


def _claims(token: str) -> dict[str, Any]:
    """Read JWT claims without verifying the signature.

    Used only on tokens Cognito just issued to this process.

    Args:
        token: JWT string.

    Returns:
        Decoded payload dict.
    """
    payload: dict[str, Any] = jwt.decode(token, options={'verify_signature': False})
    return payload


def _user_from_tokens(access_token: str, id_token: str) -> AuthUser:
    """Build AuthUser from Cognito access and id tokens.

    Args:
        access_token: Cognito access token.
        id_token: Cognito id token.

    Returns:
        AuthUser with id, email, and username when present.

    Raises:
        HTTPException: 400 if the tokens lack a `sub` claim.
    """
    access_claims = _claims(access_token)
    id_claims = _claims(id_token) if id_token else {}
    user_id = access_claims.get('sub') or id_claims.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cognito response missing user id.',
        )
    username = (
        id_claims.get('name')
        or id_claims.get('preferred_username')
        or id_claims.get('cognito:username')
    )
    return AuthUser(
        id=str(user_id),
        email=id_claims.get('email') or access_claims.get('username'),
        username=username,
    )


def _ensure_user(db: Session, auth_user: AuthUser) -> User:
    """Create a local user row for the Cognito identity if it does not exist.

    Args:
        db: Database session.
        auth_user: Identity from Cognito tokens.

    Returns:
        Existing or newly created User row.
    """
    existing = user_crud.get(db, auth_user.id)
    if existing:
        return existing
    email = auth_user.email or f'{auth_user.id}@users.invalid'
    by_email = user_crud.get_by_email(db, email)
    if by_email:
        return by_email
    return user_crud.create(db, id=uuid.UUID(auth_user.id), email=email)


def _session_from_auth_result(
    db: Session,
    auth_result: dict[str, Any],
    message: str | None = None,
) -> AuthSessionResponse:
    """Turn a Cognito AuthenticationResult into an API session and upsert the user.

    Args:
        db: Database session.
        auth_result: AuthenticationResult dict from Cognito.
        message: Optional note to include on the response.

    Returns:
        AuthSessionResponse for the frontend.

    Raises:
        HTTPException: 400 if Cognito omitted tokens.
    """
    access_token = auth_result.get('AccessToken')
    id_token = auth_result.get('IdToken') or ''
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Cognito response missing access token.',
        )
    auth_user = _user_from_tokens(access_token, id_token)
    _ensure_user(db, auth_user)
    return AuthSessionResponse(
        access_token=access_token,
        refresh_token=auth_result.get('RefreshToken') or '',
        expires_in=int(auth_result.get('ExpiresIn') or 0),
        token_type=auth_result.get('TokenType') or 'Bearer',
        user=auth_user,
        message=message,
    )


def login(db: Session, payload: AuthLoginRequest) -> AuthSessionResponse:
    """Log in with email and password via Cognito.

    Args:
        db: Database session.
        payload: Login request containing email and password.

    Returns:
        Session tokens and user identity.

    Raises:
        HTTPException: 400 if credentials are invalid; 503 if Cognito is not configured.
    """
    settings = get_settings()
    client = _cognito_client()
    try:
        response = client.initiate_auth(
            ClientId=settings.cognito_client_id,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters=_auth_parameters(
                payload.email,
                {'USERNAME': payload.email, 'PASSWORD': payload.password},
            ),
        )
    except ClientError as exc:
        _raise_cognito_error(exc, 'Login failed')
    return _session_from_auth_result(db, response.get('AuthenticationResult') or {})


def signup(db: Session, payload: AuthSignupRequest) -> AuthSessionResponse:
    """Sign up via Cognito, confirm when allowed, then log in.

    Args:
        db: Database session.
        payload: Signup request containing email, password, and optional username.

    Returns:
        Session tokens and user identity.

    Raises:
        HTTPException: 400 if signup fails; 503 if Cognito is not configured.
    """
    settings = get_settings()
    client = _cognito_client()
    attributes = [{'Name': 'email', 'Value': payload.email}]
    if payload.username:
        attributes.append({'Name': 'name', 'Value': payload.username})

    sign_up_kwargs: dict[str, Any] = {
        'ClientId': settings.cognito_client_id,
        'Username': payload.email,
        'Password': payload.password,
        'UserAttributes': attributes,
    }
    secret_hash = _secret_hash(payload.email, settings)
    if secret_hash:
        sign_up_kwargs['SecretHash'] = secret_hash

    try:
        client.sign_up(**sign_up_kwargs)
    except ClientError as exc:
        _raise_cognito_error(exc, 'Signup failed')

    try:
        client.admin_confirm_sign_up(
            UserPoolId=settings.cognito_user_pool_id,
            Username=payload.email,
        )
    except ClientError:
        pass

    try:
        return login(
            db, AuthLoginRequest(email=payload.email, password=payload.password)
        )
    except HTTPException as exc:
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Account created. Confirm your email before logging in.',
            ) from exc
        raise


def refresh(db: Session, payload: AuthRefreshRequest) -> AuthSessionResponse:
    """Exchange a refresh token for a new access token.

    Args:
        db: Database session.
        payload: Refresh request.

    Returns:
        New session tokens. Refresh token is echoed when Cognito omits a rotation.

    Raises:
        HTTPException: 400 if refresh fails; 503 if Cognito is not configured.
    """
    settings = get_settings()
    client = _cognito_client()
    username = payload.username or ''
    extra: dict[str, str] = {'REFRESH_TOKEN': payload.refresh_token}
    if username:
        extra['USERNAME'] = username
    try:
        response = client.initiate_auth(
            ClientId=settings.cognito_client_id,
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters=_auth_parameters(username, extra),
        )
    except ClientError as exc:
        _raise_cognito_error(exc, 'Refresh failed')
    result = dict(response.get('AuthenticationResult') or {})
    result.setdefault('RefreshToken', payload.refresh_token)
    return _session_from_auth_result(db, result)


class AuthService:
    """Authentication service backed by Amazon Cognito."""

    login = staticmethod(login)
    signup = staticmethod(signup)
    refresh = staticmethod(refresh)


auth_service = AuthService()
