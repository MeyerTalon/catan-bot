"""Game service: lobbies, seating, starting games, and applying moves.

every change to a game happens under a row lock on it, so two players moving
at once apply one after the other. after each human move the random bots play
until the game is waiting on a human again (or is over).
"""

from __future__ import annotations

import logging
import random

from engine import (
    Action,
    GameEngine,
    GameState,
    IllegalActionError,
    TurnPhase,
    choose_action,
    game_view,
)
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.game import game_crud
from app.models.game import Game, GamePlayer, GameStatus
from app.models.user import User
from app.schemas.game import (
    GameCreate,
    GameDetail,
    GameList,
    GameSeat,
    GameSummary,
)

logger = logging.getLogger(__name__)

# a random bot's turn is short in expectation; this only stops a runaway loop
MAX_BOT_STEPS = 10_000
MAX_NAME_LENGTH = 64

_bot_rng = random.SystemRandom()


def _engine(game: Game) -> GameEngine:
    """Load the engine for a started game.

    Args:
        game: A game whose state is set.

    Returns:
        Engine wrapping the stored state.
    """
    assert game.state is not None
    return GameEngine(GameState.model_validate(game.state))


def _seat_of(game: Game, user: User) -> GamePlayer | None:
    """Find the user's seat in a game.

    Args:
        game: Game to search.
        user: Requesting user.

    Returns:
        The seat, or None when the user is not seated.
    """
    return next((p for p in game.players if p.user_id == user.id), None)


def _seats(game: Game) -> list[GamePlayer]:
    """Seats in seat order (the relationship order can be stale after reseating)."""
    return sorted(game.players, key=lambda p: p.seat)


def _summary_fields(game: Game, user: User) -> dict[str, object]:
    """Fields shared by GameSummary and GameDetail.

    Args:
        game: Game to describe.
        user: Requesting user.

    Returns:
        Keyword arguments for either schema.
    """
    mine = _seat_of(game, user)
    names = {p.seat: p.name for p in game.players}
    your_turn = False
    current_name = winner_name = None
    if game.state is not None:
        engine = _engine(game)
        current_name = names.get(engine.state.current_player_id)
        if engine.state.winner_id is not None:
            winner_name = names.get(engine.state.winner_id)
        your_turn = (
            game.status == GameStatus.ACTIVE
            and mine is not None
            and mine.seat in engine.actors()
        )
    return {
        'id': game.id,
        'status': GameStatus(game.status),
        'host_name': game.host.display_name,
        'is_host': game.host_user_id == user.id,
        'max_players': game.max_players,
        'seats': [
            GameSeat(seat=p.seat, name=p.name, is_bot=p.is_bot, is_you=p is mine)
            for p in _seats(game)
        ],
        'your_seat': mine.seat if mine else None,
        'your_turn': your_turn,
        'current_player_name': current_name,
        'winner_name': winner_name,
        'version': game.version,
        'created_at': game.created_at,
        'updated_at': game.updated_at,
    }


def _summary(game: Game, user: User) -> GameSummary:
    """Describe a game for the lobby list."""
    return GameSummary.model_validate(_summary_fields(game, user))


def _detail(game: Game, user: User) -> GameDetail:
    """Describe a game with the user's view of the board (spectators see no hands)."""
    view = None
    if game.state is not None:
        mine = _seat_of(game, user)
        view = game_view(_engine(game), mine.seat if mine else None)
    return GameDetail.model_validate({**_summary_fields(game, user), 'view': view})


def _load(db: Session, game_id: int, *, for_update: bool = False) -> Game:
    """Fetch a game or fail with 404.

    Raises:
        HTTPException: 404 if the game does not exist.
    """
    game = game_crud.get(db, game_id, for_update=for_update)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Game not found.'
        )
    return game


def _require_status(game: Game, expected: GameStatus, detail: str) -> None:
    """Fail with 409 unless the game is in the expected status.

    Raises:
        HTTPException: 409 with `detail` when the status differs.
    """
    if game.status != expected:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _require_host(game: Game, user: User) -> None:
    """Fail with 403 unless the user hosts the game.

    Raises:
        HTTPException: 403 for anyone but the host.
    """
    if game.host_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Only the host can do that.',
        )


def _free_seat(game: Game) -> int:
    """Lowest free seat number.

    Raises:
        HTTPException: 409 when the table is full.
    """
    taken = {p.seat for p in game.players}
    for seat in range(1, game.max_players + 1):
        if seat not in taken:
            return seat
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT, detail='The game is full.'
    )


def _add_bot(db: Session, game: Game) -> None:
    """Seat a bot named after the lowest unused bot number."""
    names = {p.name for p in game.players}
    number = next(n for n in range(1, game.max_players + 1) if f'Bot {n}' not in names)
    game_crud.add_player(db, game, seat=_free_seat(game), name=f'Bot {number}')


def _touch(game: Game) -> None:
    """Bump the version so polling clients see the change."""
    game.version += 1


def _save(game: Game, engine: GameEngine) -> None:
    """Store the engine state and finish the game when it is over."""
    game.state = engine.state.model_dump(mode='json')
    if engine.state.phase == TurnPhase.GAME_OVER:
        game.status = GameStatus.FINISHED
    _touch(game)


def run_bots(engine: GameEngine, bot_seats: set[int], rng: random.Random) -> int:
    """Let bots move until the game waits on a human or ends.

    Args:
        engine: The game; mutated in place.
        bot_seats: Seats played by bots.
        rng: Source of the bots' choices.

    Returns:
        Number of bot moves made.
    """
    for step in range(MAX_BOT_STEPS):
        for seat in engine.actors():
            if seat not in bot_seats:
                continue
            action = choose_action(engine, seat, rng)
            if action is not None:
                engine.apply(seat, action)
                break
        else:
            return step
    logger.warning('bots hit the %d step limit', MAX_BOT_STEPS)
    return MAX_BOT_STEPS


def _advance_bots(game: Game, engine: GameEngine) -> None:
    """Run the game's bots and store the result."""
    run_bots(engine, {p.seat for p in game.players if p.is_bot}, _bot_rng)
    _save(game, engine)


def list_games(db: Session, user: User) -> GameList:
    """List the user's games and the lobbies they could join.

    Args:
        db: Database session.
        user: Requesting user.

    Returns:
        Both lists.
    """
    return GameList(
        mine=[_summary(g, user) for g in game_crud.list_for_user(db, user.id)],
        open=[_summary(g, user) for g in game_crud.list_open(db, user.id)],
    )


def create_game(db: Session, user: User, payload: GameCreate) -> GameDetail:
    """Open a lobby with the user in seat 1 and any requested bots.

    Args:
        db: Database session.
        user: Host.
        payload: Table size and bot count.

    Returns:
        The new lobby.
    """
    game = game_crud.create(db, host_user_id=user.id, max_players=payload.max_players)
    game_crud.add_player(
        db, game, seat=1, name=user.display_name[:MAX_NAME_LENGTH], user_id=user.id
    )
    for _ in range(payload.bots):
        _add_bot(db, game)
    return _detail(game, user)


def get_game(db: Session, user: User, game_id: int) -> GameDetail:
    """Get a game; anyone signed in may look, only seated players see a hand.

    Raises:
        HTTPException: 404 if the game does not exist.
    """
    return _detail(_load(db, game_id), user)


def join_game(db: Session, user: User, game_id: int) -> GameDetail:
    """Take a free seat in a lobby.

    Raises:
        HTTPException: 404 if missing; 409 if started, full, or already joined.
    """
    game = _load(db, game_id, for_update=True)
    _require_status(game, GameStatus.WAITING, 'The game has already started.')
    if _seat_of(game, user) is None:
        game_crud.add_player(
            db,
            game,
            seat=_free_seat(game),
            name=user.display_name[:MAX_NAME_LENGTH],
            user_id=user.id,
        )
        _touch(game)
    return _detail(game, user)


def leave_game(db: Session, user: User, game_id: int) -> None:
    """Leave a game.

    in a lobby the seat is freed (the host leaving closes the lobby); in a game
    in progress a bot takes the seat over, and a game with no humans left ends.

    Raises:
        HTTPException: 404 if the game does not exist or the user is not seated.
    """
    game = _load(db, game_id, for_update=True)
    seat = _seat_of(game, user)
    if seat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='You are not in this game.'
        )
    if game.status == GameStatus.WAITING and game.host_user_id == user.id:
        db.delete(game)
        return
    if game.status == GameStatus.ACTIVE:
        seat.user_id = None
        seat.is_bot = True
        if any(not p.is_bot for p in game.players):
            _advance_bots(game, _engine(game))
        else:
            game.status = GameStatus.FINISHED
            _touch(game)
        return
    game.players.remove(seat)
    if not any(not p.is_bot for p in game.players):
        db.delete(game)
        return
    _touch(game)


def add_bot(db: Session, user: User, game_id: int) -> GameDetail:
    """Seat a random bot in the host's lobby.

    Raises:
        HTTPException: 403 if not the host; 404 if missing; 409 if started or full.
    """
    game = _load(db, game_id, for_update=True)
    _require_host(game, user)
    _require_status(game, GameStatus.WAITING, 'The game has already started.')
    _add_bot(db, game)
    _touch(game)
    return _detail(game, user)


def remove_seat(db: Session, user: User, game_id: int, seat: int) -> GameDetail:
    """Remove a bot or another player from the host's lobby.

    Raises:
        HTTPException: 403 if not the host; 404 if missing; 409 if started or
            the host's own seat.
    """
    game = _load(db, game_id, for_update=True)
    _require_host(game, user)
    _require_status(game, GameStatus.WAITING, 'The game has already started.')
    target = next((p for p in game.players if p.seat == seat), None)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail='Seat is empty.'
        )
    if target.user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Leave the game to give up your own seat.',
        )
    game.players.remove(target)
    _touch(game)
    return _detail(game, user)


def start_game(db: Session, user: User, game_id: int) -> GameDetail:
    """Start the host's lobby: shuffle seating, deal the board, let bots place.

    Raises:
        HTTPException: 403 if not the host; 404 if missing; 409 if already
            started or fewer than two players are seated.
    """
    game = _load(db, game_id, for_update=True)
    _require_host(game, user)
    _require_status(game, GameStatus.WAITING, 'The game has already started.')
    if len(game.players) < 2:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='At least two players are needed. Add a bot or wait for others.',
        )

    order = list(game.players)
    _bot_rng.shuffle(order)
    # move everyone off their seat first: the (game, seat) unique constraint is
    # checked row by row, so swapping seats directly would collide
    for i, p in enumerate(order, start=1):
        p.seat = -i
    db.flush()
    for p in order:
        p.seat = -p.seat
    db.flush()

    engine = GameEngine.new_game([p.name for p in order])
    game.status = GameStatus.ACTIVE
    game.max_players = len(order)
    _advance_bots(game, engine)
    return _detail(game, user)


def submit_action(db: Session, user: User, game_id: int, action: Action) -> GameDetail:
    """Apply the user's move, then let the bots play.

    Raises:
        HTTPException: 400 if the move is illegal; 403 if not seated; 404 if
            missing; 409 if the game is not in progress.
    """
    game = _load(db, game_id, for_update=True)
    _require_status(game, GameStatus.ACTIVE, 'The game is not in progress.')
    seat = _seat_of(game, user)
    if seat is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail='You are not in this game.'
        )
    engine = _engine(game)
    try:
        engine.apply(seat.seat, action)
    except IllegalActionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    _advance_bots(game, engine)
    return _detail(game, user)


class GameService:
    """Game service for lobbies, seating, and play."""

    list_games = staticmethod(list_games)
    create_game = staticmethod(create_game)
    get_game = staticmethod(get_game)
    join_game = staticmethod(join_game)
    leave_game = staticmethod(leave_game)
    add_bot = staticmethod(add_bot)
    remove_seat = staticmethod(remove_seat)
    start_game = staticmethod(start_game)
    submit_action = staticmethod(submit_action)


game_service = GameService()
