"""Game and seat CRUD operations."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.game import Game, GamePlayer, GameStatus

LIST_LIMIT = 50


def create(db: Session, *, host_user_id: uuid.UUID, max_players: int) -> Game:
    """Create an empty lobby.

    Args:
        db: Database session.
        host_user_id: User creating the game.
        max_players: Seats at the table.

    Returns:
        Created Game model instance.

    Note:
        Caller must commit or use within db_session context manager.
    """
    game = Game(
        host_user_id=host_user_id,
        max_players=max_players,
        status=GameStatus.WAITING,
        version=0,
    )
    db.add(game)
    db.flush()
    return game


def get(db: Session, game_id: int, *, for_update: bool = False) -> Game | None:
    """Get a game with its seats and host.

    Args:
        db: Database session.
        game_id: Game id.
        for_update: Lock the game row until the transaction ends, so concurrent
            moves on the same game apply one after the other.

    Returns:
        Game model instance if found, None otherwise.
    """
    query = (
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.players), selectinload(Game.host))
    )
    if for_update:
        query = query.with_for_update(of=Game)
    return db.execute(query).scalar_one_or_none()


def add_player(
    db: Session,
    game: Game,
    *,
    seat: int,
    name: str,
    user_id: uuid.UUID | None = None,
) -> GamePlayer:
    """Seat a user, or a bot when no user id is given.

    Args:
        db: Database session.
        game: Game to join.
        seat: Free seat number.
        name: Display name.
        user_id: Seated user; None seats a bot.

    Returns:
        Created GamePlayer model instance.
    """
    player = GamePlayer(seat=seat, name=name, user_id=user_id, is_bot=user_id is None)
    game.players.append(player)
    db.flush()
    return player


def list_for_user(db: Session, user_id: uuid.UUID) -> list[Game]:
    """List games the user is seated in, most recently changed first.

    Args:
        db: Database session.
        user_id: User UUID.

    Returns:
        Up to LIST_LIMIT games.
    """
    seated = select(GamePlayer.game_id).where(GamePlayer.user_id == user_id)
    query = (
        select(Game)
        .where(Game.id.in_(seated))
        .options(selectinload(Game.players), selectinload(Game.host))
        .order_by(Game.updated_at.desc())
        .limit(LIST_LIMIT)
    )
    return list(db.execute(query).scalars())


def list_open(db: Session, user_id: uuid.UUID) -> list[Game]:
    """List lobbies with a free seat that the user is not already in.

    Args:
        db: Database session.
        user_id: User UUID.

    Returns:
        Up to LIST_LIMIT games, newest first.
    """
    seated = select(GamePlayer.game_id).where(GamePlayer.user_id == user_id)
    taken = (
        select(func.count(GamePlayer.id))
        .where(GamePlayer.game_id == Game.id)
        .scalar_subquery()
    )
    query = (
        select(Game)
        .where(
            Game.status == GameStatus.WAITING,
            Game.id.not_in(seated),
            taken < Game.max_players,
        )
        .options(selectinload(Game.players), selectinload(Game.host))
        .order_by(Game.created_at.desc())
        .limit(LIST_LIMIT)
    )
    return list(db.execute(query).scalars())


class GameCRUD:
    """Game CRUD operations namespace.

    Provides database operations for Game and GamePlayer models.
    """

    create = staticmethod(create)
    get = staticmethod(get)
    add_player = staticmethod(add_player)
    list_for_user = staticmethod(list_for_user)
    list_open = staticmethod(list_open)


game_crud = GameCRUD()
