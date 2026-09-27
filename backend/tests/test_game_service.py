"""Tests for game service logic that needs no database."""

from __future__ import annotations

import importlib
import random
import uuid
from datetime import datetime

import pytest
from engine import GameEngine, TurnPhase
from pydantic import ValidationError

from app.models.game import Game, GamePlayer, GameStatus
from app.models.user import User
from app.schemas.game import GameCreate

svc = importlib.import_module('app.services.game_service')

HOST = User(id=uuid.uuid4(), email='host@example.com', username=None)
GUEST = User(id=uuid.uuid4(), email='guest@example.com', username='Guest')


def _started_game(first_seat_user: User) -> Game:
    """A two-seat game in its setup phase with a user in seat 1 and a bot in seat 2.

    Args:
        first_seat_user: Who holds seat 1.

    Returns:
        A transient (never persisted) Game.
    """
    now = datetime(2026, 1, 1)
    game = Game(
        id=1,
        host_user_id=HOST.id,
        status=GameStatus.ACTIVE,
        max_players=2,
        version=3,
        created_at=now,
        updated_at=now,
    )
    game.host = HOST
    game.players = [
        GamePlayer(seat=1, name='host', user_id=first_seat_user.id, is_bot=False),
        GamePlayer(seat=2, name='Bot 1', user_id=None, is_bot=True),
    ]
    game.state = GameEngine.new_game(['host', 'Bot 1'], seed=1).state.model_dump(
        mode='json'
    )
    return game


def test_game_create_leaves_a_seat_for_the_host() -> None:
    assert GameCreate(max_players=3, bots=2).bots == 2
    with pytest.raises(ValidationError):
        GameCreate(max_players=2, bots=2)
    with pytest.raises(ValidationError):
        GameCreate(max_players=5)


def test_display_name_falls_back_to_email_local_part() -> None:
    assert HOST.display_name == 'host'
    assert GUEST.display_name == 'Guest'


def test_run_bots_waits_for_the_human() -> None:
    engine = GameEngine.new_game(['human', 'bot'], seed=2)
    rng = random.Random(0)
    assert svc.run_bots(engine, {2}, rng) == 0

    engine.apply(1, engine.legal_actions(1)[0])
    engine.apply(1, engine.legal_actions(1)[0])
    # snake order: the bot places both of its settlements and roads, then hands back
    assert svc.run_bots(engine, {2}, rng) == 4
    assert engine.actors() == [1]
    assert engine.state.phase == TurnPhase.SETUP_SETTLEMENT


def test_detail_shows_own_hand_and_turn() -> None:
    game = _started_game(HOST)
    detail = svc._detail(game, HOST)
    assert detail.your_seat == 1
    assert detail.your_turn is True
    assert detail.is_host is True
    assert detail.current_player_name == 'host'
    assert detail.view is not None
    assert detail.view.viewer_id == 1
    assert detail.view.legal_actions


def test_spectator_sees_no_hands_or_actions() -> None:
    game = _started_game(HOST)
    detail = svc._detail(game, GUEST)
    assert detail.your_seat is None
    assert detail.your_turn is False
    assert detail.view is not None
    assert detail.view.legal_actions == []
    assert all(p.resources is None for p in detail.view.players)


def test_saving_a_finished_game_marks_it_finished() -> None:
    game = _started_game(HOST)
    engine = svc._engine(game)
    engine.state.phase = TurnPhase.GAME_OVER
    svc._save(game, engine)
    assert game.status == GameStatus.FINISHED
    assert game.version == 4
