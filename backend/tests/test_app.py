"""Tests for app-level wiring: body size cap and CORS gating."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core import config
from app.main import MAX_BODY_BYTES, create_app


def _client(monkeypatch: pytest.MonkeyPatch, cors: str | None = None) -> TestClient:
    """Build a test client for a freshly created app.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        cors: CORS_ALLOWED_ORIGINS value, or None to leave it unset.

    Returns:
        TestClient bound to the app.
    """
    if cors is None:
        monkeypatch.delenv('CORS_ALLOWED_ORIGINS', raising=False)
    else:
        monkeypatch.setenv('CORS_ALLOWED_ORIGINS', cors)
    config.get_settings.cache_clear()
    client = TestClient(create_app())
    config.get_settings.cache_clear()
    return client


def test_oversized_body_is_rejected_before_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch)
    response = client.post(
        '/auth/login',
        content=b'{}',
        headers={
            'content-type': 'application/json',
            'content-length': str(MAX_BODY_BYTES + 1),
        },
    )
    assert response.status_code == 413


def test_cors_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    response = client.get('/health', headers={'origin': 'https://evil.example'})
    assert 'access-control-allow-origin' not in response.headers


def test_cors_allows_only_configured_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client(monkeypatch, cors='http://localhost:5173')
    allowed = client.get('/health', headers={'origin': 'http://localhost:5173'})
    other = client.get('/health', headers={'origin': 'https://evil.example'})
    assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
    assert 'access-control-allow-origin' not in other.headers


def test_public_user_create_route_is_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client(monkeypatch)
    response = client.post('/users', json={'id': 'x', 'email': 'a@b.com'})
    assert response.status_code in (404, 405)
