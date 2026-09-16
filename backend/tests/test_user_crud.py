"""Tests for user CRUD id handling."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.crud.user import get_by_id
from app.models.user import User

USER_ID = '11111111-1111-1111-1111-111111111111'


def test_get_by_id_coerces_string_to_uuid() -> None:
    db = MagicMock()
    get_by_id(db, USER_ID)
    db.get.assert_called_once_with(User, uuid.UUID(USER_ID))


def test_get_by_id_passes_uuid_through() -> None:
    db = MagicMock()
    ident = uuid.UUID(USER_ID)
    get_by_id(db, ident)
    db.get.assert_called_once_with(User, ident)
