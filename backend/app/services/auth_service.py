"""Auth service: Amazon Cognito signup, confirmation, login, refresh, and logout."""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
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
    AuthConfirmRequest,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthMessageResponse,
    AuthRefreshRequest,
    AuthResendConfirmationRequest,
    AuthSessionResponse,
    AuthSignupRequest,
    AuthSignupResponse,
    AuthUser,
)

logger = logging.getLogger(__name__)

# cognito error codes with a message that is safe to show. anything else gets the
# caller's fallback so the response cannot leak which accounts exist or why
# cognito rejected a request; the real code is logged server-side.
_SAFE_MESSAGES: dict[str, str] = {
    'NotAuthorizedException': 'Incorrect email or password.',
    # same wording as a bad password so the pair cannot tell accounts apart
    # (cognito masks this itself with prevent_user_existence_errors; the
    # emulator does not)
    'UserNotFoundException': 'Incorrect email or password.',
    'UserNotConfirmedException': 'Confirm your email before logging in.',
    'PasswordResetRequiredException': 'A password reset is required.',
    'InvalidPasswordException': 'Password does not meet the pool requirements.',
    'InvalidParameterException': 'Invalid request.',
    'CodeMismatchException': 'Invalid confirmation code.',
    'ExpiredCodeException': 'Confirmation code expired. Request a new one.',
    'LimitExceededException': 'Too many attempts. Try again later.',
    'TooManyRequestsException': 'Too many attempts. Try again later.',
}

CONFIRMATION_SENT = 'Check your email for a confirmation code.'


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


def _with_secret_hash(username: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Add SecretHash to a non-InitiateAuth call's kwargs when the client has a secret.

    Args:
        username: Cognito username.
        kwargs: Call kwargs (ClientId, Username, ...).

    Returns:
        The same dict, with SecretHash set when applicable.
    """
    secret_hash = _secret_hash(username, get_settings())
    if secret_hash:
        kwargs['SecretHash'] = secret_hash
    return kwargs


def _error_code(exc: ClientError) -> str:
    """Read the Cognito error code from a boto3 ClientError.

    Args:
        exc: boto3 client error.

    Returns:
        Error code string, or '' when absent.
    """
    code: str = exc.response.get('Error', {}).get('Code', '')
    return code


def _raise_cognito_error(exc: ClientError, fallback: str) -> NoReturn:
    """Map a Cognito ClientError to a 400 with a non-revealing message.

    Args:
        exc: boto3 client error.
        fallback: Message used when the error code has no safe message.

    Raises:
        HTTPException: 400 with a safe message; the real code and message are logged.
    """
    code = _error_code(exc)
    logger.warning(
        'cognito %s failed: %s: %s',
        exc.operation_name,
        code,
        exc.response.get('Error', {}).get('Message'),
    )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=_SAFE_MESSAGES.get(code, fallback),
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

    Raises:
        HTTPException: 409 if the email already belongs to a row with a different
            id. silently adopting that row would let its owner be locked out, so
            the mismatch is surfaced instead.
    """
    existing = user_crud.get(db, auth_user.id)
    if existing:
        return existing
    email = auth_user.email or f'{auth_user.id}@users.invalid'
    if user_crud.get_by_email(db, email):
        logger.error('users row for %s exists under a different id', email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='This account is in conflict with an existing profile. Contact support.',
        )
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
        _raise_cognito_error(exc, 'Login failed.')
    return _session_from_auth_result(db, response.get('AuthenticationResult') or {})


def signup(db: Session, payload: AuthSignupRequest) -> AuthSignupResponse:
    """Sign up via Cognito; the account is confirmed by email before it can log in.

    outside production (the local emulator sends no email) the account is
    confirmed with an admin call and logged in at once.

    Args:
        db: Database session.
        payload: Signup request containing email, password, and optional username.

    Returns:
        Whether confirmation is pending, plus a session when it is not.

    Raises:
        HTTPException: 400 if signup fails; 503 if Cognito is not configured.
    """
    settings = get_settings()
    client = _cognito_client()
    attributes = [{'Name': 'email', 'Value': payload.email}]
    if payload.username:
        attributes.append({'Name': 'name', 'Value': payload.username})

    try:
        response = client.sign_up(
            **_with_secret_hash(
                payload.email,
                {
                    'ClientId': settings.cognito_client_id,
                    'Username': payload.email,
                    'Password': payload.password,
                    'UserAttributes': attributes,
                },
            )
        )
    except ClientError as exc:
        # in production an existing account gets the same answer as a new one so
        # signup cannot be used to enumerate emails
        if _error_code(exc) == 'UsernameExistsException' and settings.is_production:
            logger.info('signup for an existing email')
            return AuthSignupResponse(email=payload.email, confirmation_required=True)
        _raise_cognito_error(exc, 'Signup failed.')

    confirmed = bool(response.get('UserConfirmed'))
    if not confirmed and settings.is_production:
        return AuthSignupResponse(email=payload.email, confirmation_required=True)

    if not confirmed:
        client.admin_confirm_sign_up(
            UserPoolId=settings.cognito_user_pool_id,
            Username=payload.email,
        )
    session = login(
        db, AuthLoginRequest(email=payload.email, password=payload.password)
    )
    return AuthSignupResponse(
        email=payload.email, confirmation_required=False, session=session
    )


def confirm(payload: AuthConfirmRequest) -> AuthMessageResponse:
    """Confirm a signup with the code Cognito emailed.

    Args:
        payload: Email and confirmation code.

    Returns:
        Acknowledgement; the client logs in afterwards.

    Raises:
        HTTPException: 400 if the code is wrong or expired; 503 if Cognito is not configured.
    """
    settings = get_settings()
    client = _cognito_client()
    try:
        client.confirm_sign_up(
            **_with_secret_hash(
                payload.email,
                {
                    'ClientId': settings.cognito_client_id,
                    'Username': payload.email,
                    'ConfirmationCode': payload.code,
                },
            )
        )
    except ClientError as exc:
        _raise_cognito_error(exc, 'Confirmation failed.')
    return AuthMessageResponse(message='Email confirmed. You can log in now.')


def resend_confirmation(payload: AuthResendConfirmationRequest) -> AuthMessageResponse:
    """Ask Cognito to email a fresh confirmation code.

    Args:
        payload: Email used at signup.

    Returns:
        Acknowledgement. the wording is the same whether or not the account exists.

    Raises:
        HTTPException: 400 on a Cognito error other than an unknown account;
            503 if Cognito is not configured.
    """
    settings = get_settings()
    client = _cognito_client()
    try:
        client.resend_confirmation_code(
            **_with_secret_hash(
                payload.email,
                {'ClientId': settings.cognito_client_id, 'Username': payload.email},
            )
        )
    except ClientError as exc:
        if _error_code(exc) == 'UserNotFoundException':
            logger.info('resend requested for an unknown email')
            return AuthMessageResponse(message=CONFIRMATION_SENT)
        _raise_cognito_error(exc, 'Could not resend the confirmation code.')
    return AuthMessageResponse(message=CONFIRMATION_SENT)


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
        _raise_cognito_error(exc, 'Session expired. Log in again.')
    result = dict(response.get('AuthenticationResult') or {})
    result.setdefault('RefreshToken', payload.refresh_token)
    return _session_from_auth_result(db, result)


def logout(payload: AuthLogoutRequest, access_token: str | None) -> AuthMessageResponse:
    """Revoke a refresh token (and, when given, sign out the access token's session).

    revocation is best effort: a token that is already invalid still yields a
    successful logout, since the outcome the client wants is the same.

    Args:
        payload: Refresh token to revoke.
        access_token: Bearer token from the request, if any.

    Returns:
        Acknowledgement.

    Raises:
        HTTPException: 503 if Cognito is not configured.
    """
    settings = get_settings()
    client = _cognito_client()
    revoke_kwargs: dict[str, Any] = {
        'Token': payload.refresh_token,
        'ClientId': settings.cognito_client_id,
    }
    if settings.cognito_client_secret:
        revoke_kwargs['ClientSecret'] = settings.cognito_client_secret
    try:
        client.revoke_token(**revoke_kwargs)
    except ClientError as exc:
        logger.info('revoke_token failed: %s', _error_code(exc))
    if access_token:
        try:
            client.global_sign_out(AccessToken=access_token)
        except ClientError as exc:
            logger.info('global_sign_out failed: %s', _error_code(exc))
    return AuthMessageResponse(message='Logged out.')


class AuthService:
    """Authentication service backed by Amazon Cognito."""

    login = staticmethod(login)
    signup = staticmethod(signup)
    confirm = staticmethod(confirm)
    resend_confirmation = staticmethod(resend_confirmation)
    refresh = staticmethod(refresh)
    logout = staticmethod(logout)


auth_service = AuthService()
