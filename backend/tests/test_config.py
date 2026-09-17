"""Tests for settings loading in app.core.config."""

from __future__ import annotations

import pytest

from app.core import config


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Reset the lru_cache on get_settings so each test sees fresh env vars."""
    config.get_settings.cache_clear()
    yield
    config.get_settings.cache_clear()


def test_get_settings_reads_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pw@localhost:5432/db')
    monkeypatch.setenv('ENVIRONMENT', 'production')
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'us-west-2_abc')
    monkeypatch.setenv('COGNITO_CLIENT_ID', 'clientid')

    settings = config.get_settings()

    assert settings.database_url == 'postgresql://user:pw@localhost:5432/db'
    assert settings.is_production is True
    assert settings.cognito_configured is True
    assert settings.cognito_issuer.endswith('/us-west-2_abc')


def test_get_settings_requires_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with pytest.raises(RuntimeError, match='must be set'):
        config.get_settings()


def test_get_settings_rejects_https_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'https://example.invalid')

    with pytest.raises(RuntimeError, match='Postgres connection string'):
        config.get_settings()


def test_jwks_url_defaults_to_issuer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pw@localhost:5432/db')
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'us-west-2_abc')
    monkeypatch.delenv('COGNITO_ENDPOINT_URL', raising=False)
    monkeypatch.delenv('COGNITO_JWKS_URL', raising=False)

    settings = config.get_settings()

    assert settings.cognito_endpoint_url is None
    assert settings.jwks_url == (
        'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_abc/.well-known/jwks.json'
    )


def test_local_emulator_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pw@localhost:5432/db')
    monkeypatch.setenv('COGNITO_USER_POOL_ID', 'us-west-2_abc')
    monkeypatch.setenv('COGNITO_ENDPOINT_URL', 'http://moto:5000')
    monkeypatch.setenv(
        'COGNITO_JWKS_URL', 'http://moto:5000/us-west-2_abc/.well-known/jwks.json'
    )

    settings = config.get_settings()

    assert settings.cognito_endpoint_url == 'http://moto:5000'
    assert settings.jwks_url == 'http://moto:5000/us-west-2_abc/.well-known/jwks.json'
    # the issuer stays the aws one: emulators mint tokens with the real iss claim
    assert settings.cognito_issuer == (
        'https://cognito-idp.us-west-2.amazonaws.com/us-west-2_abc'
    )
