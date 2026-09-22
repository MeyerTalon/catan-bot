"""core data types for a game of Catan.

plain pydantic models so a `GameState` round-trips through json and can be
stored unchanged in the backend's `game_sessions.state` column.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Dict, List, Tuple

from pydantic import BaseModel, Field


class Resource(StrEnum):
    """the five tradeable resources."""

    BRICK = 'brick'
    LUMBER = 'lumber'
    WOOL = 'wool'
    GRAIN = 'grain'
    ORE = 'ore'


class TurnPhase(StrEnum):
    """where the current player is within their turn."""

    SETUP = 'setup'
    ROLL = 'roll'
    MAIN = 'main'


class HexTile(BaseModel):
    """one hex on the board; the desert has no resource or number token."""

    id: int
    resource: Resource | None = None
    number_token: int | None = None


class Board(BaseModel):
    """hex layout plus the robber's position."""

    hexes: List[HexTile]
    robber_hex_id: int


class Player(BaseModel):
    """a seat at the table and everything it owns."""

    id: int
    name: str
    victory_points: int = 0
    resources: Dict[Resource, int] = Field(default_factory=dict)
    roads: List[Tuple[int, int]] = Field(
        default_factory=list, description='edges as (node_a, node_b) ids.'
    )
    settlements: List[int] = Field(default_factory=list, description='node ids.')
    cities: List[int] = Field(default_factory=list, description='node ids.')


class GameState(BaseModel):
    """complete snapshot of a game between actions."""

    players: List[Player]
    board: Board
    current_player_id: int
    turn_number: int = 1
    phase: TurnPhase = TurnPhase.SETUP
