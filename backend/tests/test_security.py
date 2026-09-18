"""Tests for JWT user-id extraction."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.core import config, security


def test_get_user_id_from_token_reads_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, 'decode_jwt', lambda token: {'sub': 'abc-123'})
    assert security.get_user_id_from_token('token') == 'abc-123'


def test_get_user_id_from_token_requires_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, 'decode_jwt', lambda token: {})
    with pytest.raises(HTTPException) as exc_info:
        security.get_user_id_from_token('token')
    assert exc_info.value.status_code == 401


def _decode_with_payload(
    monkeypatch: pytest.MonkeyPatch, payload: dict[str, Any]
) -> dict[str, Any]:
    """Run decode_jwt with the signature/JWKS layer stubbed to return `payload`.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        payload: Claims jwt.decode should return.

    Returns:
        The payload decode_jwt accepted.
    """
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'us-west-2_abc')
    monkeypatch.setenv('COGNITO_CLIENT_ID', 'clientid')
    config.get_settings.cache_clear()
    monkeypatch.setattr(security, '_jwks_client', lambda: MagicMock())
    monkeypatch.setattr(security.jwt, 'decode', lambda *args, **kwargs: payload)
    try:
        return security.decode_jwt('token')
    finally:
        config.get_settings.cache_clear()


def test_decode_jwt_accepts_access_token_for_this_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {'sub': 'abc', 'token_use': 'access', 'client_id': 'clientid'}
    assert _decode_with_payload(monkeypatch, payload) == payload


def test_decode_jwt_rejects_id_token(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _decode_with_payload(
            monkeypatch, {'sub': 'abc', 'token_use': 'id', 'aud': 'clientid'}
        )
    assert exc_info.value.status_code == 401


def test_decode_jwt_rejects_other_client(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(HTTPException) as exc_info:
        _decode_with_payload(
            monkeypatch, {'sub': 'abc', 'token_use': 'access', 'client_id': 'other'}
        )
    assert exc_info.value.status_code == 401


def test_decode_jwt_requires_exp_iat_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'us-west-2_abc')
    monkeypatch.setenv('COGNITO_CLIENT_ID', 'clientid')
    config.get_settings.cache_clear()
    monkeypatch.setattr(security, '_jwks_client', lambda: MagicMock())
    seen: list[dict[str, Any]] = []

    def fake_decode(*args: Any, **kwargs: Any) -> dict[str, Any]:
        seen.append(kwargs['options'])
        return {'sub': 'abc', 'token_use': 'access', 'client_id': 'clientid'}

    monkeypatch.setattr(security.jwt, 'decode', fake_decode)
    security.decode_jwt('token')
    config.get_settings.cache_clear()

    assert seen[0]['require'] == ['exp', 'iat', 'sub']


def test_jwks_client_uses_settings_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql://test:test@localhost:5432/test')
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'us-west-2_abc')
    monkeypatch.setenv('COGNITO_CLIENT_ID', 'clientid')
    monkeypatch.setenv(
        'COGNITO_JWKS_URL', 'http://moto:5000/us-west-2_abc/.well-known/jwks.json'
    )
    config.get_settings.cache_clear()
    security._jwks_client.cache_clear()
    seen: list[str] = []
    monkeypatch.setattr(security.jwt, 'PyJWKClient', lambda uri: seen.append(uri))

    security._jwks_client()

    assert seen == ['http://moto:5000/us-west-2_abc/.well-known/jwks.json']
    config.get_settings.cache_clear()
    security._jwks_client.cache_clear()
