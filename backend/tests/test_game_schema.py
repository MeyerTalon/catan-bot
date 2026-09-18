"""Tests for the game state size cap."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.game import MAX_STATE_BYTES, GameSessionCreate


def test_state_within_cap_is_accepted() -> None:
    assert GameSessionCreate(state={'board': 'x' * 100}).state['board'] == 'x' * 100


def test_state_over_cap_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GameSessionCreate(state={'board': 'x' * MAX_STATE_BYTES})
