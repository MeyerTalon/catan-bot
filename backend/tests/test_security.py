"""Tests for JWT user-id extraction."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.core import security


def test_get_user_id_from_token_reads_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, 'decode_jwt', lambda token: {'sub': 'abc-123'})
    assert security.get_user_id_from_token('token') == 'abc-123'


def test_get_user_id_from_token_requires_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, 'decode_jwt', lambda token: {})
    with pytest.raises(HTTPException) as exc_info:
        security.get_user_id_from_token('token')
    assert exc_info.value.status_code == 401
