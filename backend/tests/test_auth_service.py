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
from app.schemas.auth import AuthLoginRequest, AuthRefreshRequest, AuthSignupRequest

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


def test_login_maps_cognito_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.initiate_auth.side_effect = ClientError(
        {
            'Error': {
                'Code': 'NotAuthorizedException',
                'Message': 'Incorrect username or password.',
            }
        },
        'InitiateAuth',
    )
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)

    with pytest.raises(HTTPException) as exc_info:
        auth_mod.login(MagicMock(), AuthLoginRequest(email='a@b.com', password='bad'))

    assert exc_info.value.status_code == 400
    assert 'Incorrect username or password' in str(exc_info.value.detail)


def test_signup_confirms_and_logs_in(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.initiate_auth.return_value = {'AuthenticationResult': _auth_result()}
    monkeypatch.setattr(auth_mod, '_cognito_client', lambda: client)
    monkeypatch.setattr(auth_mod.user_crud, 'get', lambda db, user_id: MagicMock())

    session = auth_mod.signup(
        MagicMock(),
        AuthSignupRequest(email='a@b.com', password='secret', username='player'),
    )

    assert session.user.id == USER_ID
    client.sign_up.assert_called_once()
    client.admin_confirm_sign_up.assert_called_once()


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
