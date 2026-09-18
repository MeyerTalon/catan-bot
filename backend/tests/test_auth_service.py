"""Tests for Cognito-backed auth_service (boto3 mocked, no network)."""

from __future__ import annotations

import importlib
import uuid
from typing import Any
from unittest.mock import MagicMock

import jwt
import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException

from app.core import config
from app.schemas.auth import (
    AuthConfirmRequest,
    AuthLoginRequest,
    AuthLogoutRequest,
    AuthRefreshRequest,
    AuthResendConfirmationRequest,
    AuthSignupRequest,
    AuthUser,
)

auth_mod = importlib.import_module('app.services.auth_service')


USER_ID = '11111111-1111-1111-1111-111111111111'


def _token(claims: dict[str, Any]) -> str:
    """Build an unsigned JWT for tests that skip signature verification.

    Args:
        claims: Payload claims.

    Returns:
        Encoded JWT string.
    """
    return jwt.encode(claims, 'test', algorithm='HS256')


@pytest.fixture(autouse=True)
def _cognito_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set Cognito env and clear settings cache for each test."""
    monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
    monkeypatch.setenv('COGNITO_REGION', 'us-west-2')
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'us-west-2_pool')
    monkeypatch.setenv('COGNITO_CLIENT_ID', 'clientid')
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def _auth_result() -> dict[str, Any]:
    """Return a Cognito AuthenticationResult with unsigned test JWTs.

    Returns:
        Dict shaped like boto3 initiate_auth AuthenticationResult.
    """
    access = _token({'sub': USER_ID, 'token_use': 'access', 'username': 'a@b.com'})
    ident = _token(
        {
            'sub': USER_ID,
            'token_use': 'id',
            'email': 'a@b.com',
            'name': 'player',
        }
    )
    return {
        'AccessToken': access,
        'IdToken': ident,
        'RefreshToken': 'refresh-token',
        'ExpiresIn': 3600,
        'TokenType': 'Bearer',
    }


def test_cognito_client_forwards_endpoint_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('COGNITO_ENDPOINT_URL', 'http://moto:5000')
    config.get_settings.cache_clear()
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        auth_mod.boto3, 'client', lambda service, **kwargs: calls.append(kwargs)
    )

    auth_mod._cognito_client()

    assert calls == [{'region_name': 'us-west-2', 'endpoint_url': 'http://moto:5000'}]


def test_cognito_client_defaults_to_aws_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv('COGNITO_ENDPOINT_URL', raising=False)
    config.get_settings.cache_clear()
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        auth_mod.boto3, 'client', lambda service, **kwargs: calls.append(kwargs)
    )

    auth_mod._cognito_client()

    assert calls == [{'region_name': 'us-west-2', 'endpoint_url': None}]


def test_login_returns_session(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.initiate_auth.return_value = {'AuthenticationResult': _auth_result()}
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    created = MagicMock()
    monkeypatch.setattr(auth_mod.user_crud, 'get', lambda db, user_id: None)
    monkeypatch.setattr(auth_mod.user_crud, 'get_by_email', lambda db, email: None)
    monkeypatch.setattr(auth_mod.user_crud, 'create', lambda db, **kwargs: created)

    session = auth_mod.login(
        MagicMock(), AuthLoginRequest(email='a@b.com', password='secret')
    )

    assert session.user.id == USER_ID
    assert session.user.email == 'a@b.com'
    assert session.refresh_token == 'refresh-token'
    assert session.expires_in == 3600
    client.initiate_auth.assert_called_once()


def _client_error(code: str, operation: str = 'InitiateAuth') -> ClientError:
    """Build a boto3 ClientError with the given Cognito error code.

    Args:
        code: Cognito error code.
        operation: Operation name.

    Returns:
        ClientError instance.
    """
    return ClientError(
        {'Error': {'Code': code, 'Message': f'{code} raw message'}}, operation
    )


def test_login_maps_known_cognito_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.initiate_auth.side_effect = _client_error('NotAuthorizedException')
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    with pytest.raises(HTTPException) as exc_info:
        auth_mod.login(MagicMock(), AuthLoginRequest(email='a@b.com', password='bad'))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == 'Incorrect email or password.'


def test_unknown_user_and_bad_password_are_indistinguishable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)
    details: list[str] = []
    for code in ('UserNotFoundException', 'NotAuthorizedException'):
        client.initiate_auth.side_effect = _client_error(code)
        with pytest.raises(HTTPException) as exc_info:
            auth_mod.login(
                MagicMock(), AuthLoginRequest(email='a@b.com', password='bad')
            )
        details.append(str(exc_info.value.detail))
    assert details[0] == details[1]


def test_unknown_cognito_error_does_not_leak_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.initiate_auth.side_effect = _client_error('SomethingInternalException')
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    with pytest.raises(HTTPException) as exc_info:
        auth_mod.login(MagicMock(), AuthLoginRequest(email='a@b.com', password='bad'))

    assert exc_info.value.detail == 'Login failed.'
    assert 'raw message' not in str(exc_info.value.detail)


def test_signup_outside_production_confirms_and_logs_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.sign_up.return_value = {'UserConfirmed': False}
    client.initiate_auth.return_value = {'AuthenticationResult': _auth_result()}
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)
    monkeypatch.setattr(auth_mod.user_crud, 'get', lambda db, user_id: MagicMock())

    result = auth_mod.signup(
        MagicMock(),
        AuthSignupRequest(email='a@b.com', password='secret', username='player'),
    )

    assert result.confirmation_required is False
    assert result.session is not None
    assert result.session.user.id == USER_ID
    client.sign_up.assert_called_once()
    client.admin_confirm_sign_up.assert_called_once()


def test_signup_in_production_requires_email_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'production')
    config.get_settings.cache_clear()
    client = MagicMock()
    client.sign_up.return_value = {'UserConfirmed': False}
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    result = auth_mod.signup(
        MagicMock(), AuthSignupRequest(email='a@b.com', password='secret')
    )

    assert result.confirmation_required is True
    assert result.session is None
    client.admin_confirm_sign_up.assert_not_called()
    client.initiate_auth.assert_not_called()


def test_signup_in_production_hides_existing_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv('ENVIRONMENT', 'production')
    config.get_settings.cache_clear()
    client = MagicMock()
    client.sign_up.side_effect = _client_error('UsernameExistsException', 'SignUp')
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    result = auth_mod.signup(
        MagicMock(), AuthSignupRequest(email='a@b.com', password='secret')
    )

    assert result.confirmation_required is True
    assert result.session is None


def test_confirm_maps_bad_code(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.confirm_sign_up.side_effect = _client_error(
        'CodeMismatchException', 'ConfirmSignUp'
    )
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    with pytest.raises(HTTPException) as exc_info:
        auth_mod.confirm(AuthConfirmRequest(email='a@b.com', code='000000'))

    assert exc_info.value.detail == 'Invalid confirmation code.'


def test_resend_confirmation_same_answer_for_unknown_email(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.resend_confirmation_code.side_effect = _client_error(
        'UserNotFoundException', 'ResendConfirmationCode'
    )
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    unknown = auth_mod.resend_confirmation(
        AuthResendConfirmationRequest(email='nobody@b.com')
    )
    client.resend_confirmation_code.side_effect = None
    known = auth_mod.resend_confirmation(AuthResendConfirmationRequest(email='a@b.com'))

    assert unknown == known


def test_ensure_user_rejects_email_owned_by_another_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(auth_mod.user_crud, 'get', lambda db, user_id: None)
    monkeypatch.setattr(
        auth_mod.user_crud, 'get_by_email', lambda db, email: MagicMock()
    )
    created: list[Any] = []
    monkeypatch.setattr(
        auth_mod.user_crud, 'create', lambda db, **kwargs: created.append(kwargs)
    )

    with pytest.raises(HTTPException) as exc_info:
        auth_mod._ensure_user(MagicMock(), AuthUser(id=USER_ID, email='a@b.com'))

    assert exc_info.value.status_code == 409
    assert created == []


def test_logout_revokes_and_signs_out(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    auth_mod.logout(AuthLogoutRequest(refresh_token='rt'), access_token='at')

    client.revoke_token.assert_called_once_with(Token='rt', ClientId='clientid')
    client.global_sign_out.assert_called_once_with(AccessToken='at')


def test_logout_succeeds_when_token_already_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.revoke_token.side_effect = _client_error(
        'UnauthorizedException', 'RevokeToken'
    )
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    result = auth_mod.logout(AuthLogoutRequest(refresh_token='rt'), access_token=None)

    assert result.message == 'Logged out.'
    client.global_sign_out.assert_not_called()


def test_refresh_echoes_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    result = _auth_result()
    del result['RefreshToken']
    client = MagicMock()
    client.initiate_auth.return_value = {'AuthenticationResult': result}
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)
    monkeypatch.setattr(auth_mod.user_crud, 'get', lambda db, user_id: MagicMock())

    session = auth_mod.refresh(
        MagicMock(),
        AuthRefreshRequest(refresh_token='old-refresh', username='a@b.com'),
    )

    assert session.refresh_token == 'old-refresh'
    assert uuid.UUID(session.user.id)
