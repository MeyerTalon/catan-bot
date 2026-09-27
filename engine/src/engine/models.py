"""core data types for a game of Catan.

plain pydantic models so a `GameState` round-trips through json and can be
stored unchanged in the backend's `games.state` column.
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


class DevCard(StrEnum):
    """development card kinds."""

    KNIGHT = 'knight'
    VICTORY_POINT = 'victory_point'
    ROAD_BUILDING = 'road_building'
    YEAR_OF_PLENTY = 'year_of_plenty'
    MONOPOLY = 'monopoly'


class TurnPhase(StrEnum):
    """what the game is waiting for."""

    SETUP_SETTLEMENT = 'setup_settlement'
    SETUP_ROAD = 'setup_road'
    ROLL = 'roll'
    DISCARD = 'discard'
    MOVE_ROBBER = 'move_robber'
    MAIN = 'main'
    ROAD_BUILDING = 'road_building'
    GAME_OVER = 'game_over'


def empty_hand() -> Dict[Resource, int]:
    """returns a hand with zero of every resource."""
    return {r: 0 for r in Resource}


class HexTile(BaseModel):
    """one hex on the board, at axial coordinates (q, r).

    the desert has no resource or number token.
    """

    id: int
    q: int = 0
    r: int = 0
    resource: Resource | None = None
    number_token: int | None = None


class Port(BaseModel):
    """a harbour on a coastal edge; `resource` None is a generic 3:1 port."""

    resource: Resource | None = None
    nodes: Tuple[int, int]


class Board(BaseModel):
    """hex layout, harbours, and the robber's position."""

    hexes: List[HexTile]
    ports: List[Port] = Field(default_factory=list)
    robber_hex_id: int


class Player(BaseModel):
    """a seat at the table and everything it owns."""

    id: int
    name: str
    resources: Dict[Resource, int] = Field(default_factory=empty_hand)
    dev_cards: List[DevCard] = Field(
        default_factory=list, description='playable cards held before this turn.'
    )
    new_dev_cards: List[DevCard] = Field(
        default_factory=list, description='cards bought this turn; playable next turn.'
    )
    knights_played: int = 0
    roads: List[Tuple[int, int]] = Field(
        default_factory=list, description='edges as (node_a, node_b) ids.'
    )
    settlements: List[int] = Field(default_factory=list, description='node ids.')
    cities: List[int] = Field(default_factory=list, description='node ids.')

    def card_count(self) -> int:
        """total resource cards in hand."""
        return sum(self.resources.values())


class TradeOffer(BaseModel):
    """a domestic trade the current player has put to the table.

    `give` is what the proposer hands over, `receive` what they ask for.
    """

    proposer_id: int
    give: Dict[Resource, int]
    receive: Dict[Resource, int]
    accepted: List[int] = Field(default_factory=list)
    rejected: List[int] = Field(default_factory=list)


class LogEntry(BaseModel):
    """one line of the public game log; `seq` numbers entries from 0."""

    seq: int
    turn: int
    player_id: int | None = None
    message: str


class GameState(BaseModel):
    """complete snapshot of a game between actions."""

    players: List[Player]
    board: Board
    current_player_id: int
    turn_number: int = 1
    phase: TurnPhase = TurnPhase.SETUP_SETTLEMENT
    setup_step: int = Field(
        default=0, description='index into the snake order of setup placements.'
    )
    last_settlement_node: int | None = Field(
        default=None, description='the setup settlement the next road must touch.'
    )
    dice: Tuple[int, int] | None = None
    bank: Dict[Resource, int] = Field(default_factory=dict)
    dev_deck: List[DevCard] = Field(default_factory=list)
    discards_owed: Dict[int, int] = Field(default_factory=dict)
    robber_return_phase: TurnPhase | None = None
    free_roads: int = 0
    dev_card_played: bool = False
    trade_offer: TradeOffer | None = None
    trades_proposed: int = 0
    longest_road_player_id: int | None = None
    largest_army_player_id: int | None = None
    winner_id: int | None = None
    log: List[LogEntry] = Field(default_factory=list)
