"""Game and GamePlayer ORM models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class GameStatus(StrEnum):
    """Lifecycle of a game: lobby, in play, done."""

    WAITING = 'waiting'
    ACTIVE = 'active'
    FINISHED = 'finished'


class Game(Base):
    """A Catan game: a lobby until the host starts it, then an engine state.

    Attributes:
        id: Primary key, auto-increment.
        host_user_id: User who created the game and may start it.
        status: One of GameStatus.
        max_players: Seats in the lobby (2-4).
        state: Serialized engine `GameState`; None until the game starts.
        version: Bumped on every change so clients can skip unchanged polls.
        created_at: When the game was created.
        updated_at: When the game last changed.
        players: Seated humans and bots, ordered by seat.
        host: Related User instance.
    """

    __tablename__ = 'games'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    host_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=GameStatus.WAITING, index=True
    )
    max_players: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    players: Mapped[list[GamePlayer]] = relationship(
        'GamePlayer',
        back_populates='game',
        cascade='all, delete-orphan',
        order_by='GamePlayer.seat',
    )
    host: Mapped[User] = relationship('User')


class GamePlayer(Base):
    """One seat in a game, held by a user or a bot.

    once the game starts, `seat` is the engine's player id and sets turn order.

    Attributes:
        id: Primary key, auto-increment.
        game_id: Game this seat belongs to.
        seat: Seat number, 1-based.
        user_id: Seated user; None for a bot.
        is_bot: Whether a random bot plays this seat.
        name: Display name shown to the table.
        joined_at: When the seat was taken.
    """

    __tablename__ = 'game_players'
    __table_args__ = (
        UniqueConstraint('game_id', 'seat', name='uq_game_players_game_seat'),
        UniqueConstraint('game_id', 'user_id', name='uq_game_players_game_user'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False, index=True
    )
    seat: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=True,
        index=True,
    )
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    game: Mapped[Game] = relationship('Game', back_populates='players')
