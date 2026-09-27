"""Game lobby and play API schemas.

the in-game view and action types come straight from the rules engine, so the
OpenAPI schema (and the generated frontend types) always match what it accepts.
"""

from __future__ import annotations

from datetime import datetime

from engine import MAX_PLAYERS, MIN_PLAYERS, Action, GameView
from pydantic import BaseModel, Field, model_validator

from app.models.game import GameStatus


class GameCreate(BaseModel):
    """Request body for POST /games.

    Attributes:
        max_players: Seats at the table, including the host and bots.
        bots: Seats to fill with random bots straight away.
    """

    max_players: int = Field(default=4, ge=MIN_PLAYERS, le=MAX_PLAYERS)
    bots: int = Field(default=0, ge=0, le=MAX_PLAYERS - 1)

    @model_validator(mode='after')
    def _bots_leave_room_for_host(self) -> GameCreate:
        """Reject more bots than there are seats besides the host's.

        Returns:
            The validated model.

        Raises:
            ValueError: If the bots would not fit.
        """
        if self.bots > self.max_players - 1:
            raise ValueError('bots must leave a seat for the host.')
        return self


class GameSeat(BaseModel):
    """One occupied seat, as shown in lobbies and game lists.

    Attributes:
        seat: Seat number; the engine player id once the game starts.
        name: Display name.
        is_bot: Whether a random bot plays this seat.
        is_you: Whether the requesting user holds this seat.
    """

    seat: int
    name: str
    is_bot: bool
    is_you: bool


class GameSummary(BaseModel):
    """A game as listed in the lobby.

    Attributes:
        id: Game id.
        status: waiting, active, or finished.
        host_name: Display name of the host.
        is_host: Whether the requesting user is the host.
        max_players: Seats at the table.
        seats: Occupied seats in seat order.
        your_seat: The requesting user's seat, if seated.
        your_turn: Whether the game is waiting on the requesting user.
        current_player_name: Whose turn it is, once started.
        winner_name: Winner, once finished.
        version: Bumped on every change.
        created_at: When the game was created.
        updated_at: When the game last changed.
    """

    id: int
    status: GameStatus
    host_name: str
    is_host: bool
    max_players: int
    seats: list[GameSeat]
    your_seat: int | None
    your_turn: bool
    current_player_name: str | None
    winner_name: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class GameDetail(GameSummary):
    """A game with the requesting user's view of the board.

    Attributes:
        view: What the requesting user may see; None while in the lobby.
    """

    view: GameView | None = None


class GameList(BaseModel):
    """Response for GET /games.

    Attributes:
        mine: Games the requesting user is seated in, most recently active first.
        open: Lobbies with a free seat the requesting user could join.
    """

    mine: list[GameSummary]
    open: list[GameSummary]


class GameActionRequest(BaseModel):
    """Request body for POST /games/{game_id}/actions.

    Attributes:
        action: The move to make, discriminated by its `type`.
    """

    action: Action
