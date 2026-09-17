"""Tests for JWT user-id extraction."""

from __future__ import annotations

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
