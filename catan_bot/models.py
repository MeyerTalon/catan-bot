from __future__ import annotations

from enum import Enum
from typing import Dict, List, Literal, Optional, Tuple

from pydantic import BaseModel, Field


class Resource(str, Enum):
    BRICK = "brick"
    LUMBER = "lumber"
    WOOL = "wool"
    GRAIN = "grain"
    ORE = "ore"


class BuildType(str, Enum):
    ROAD = "road"
    SETTLEMENT = "settlement"
    CITY = "city"
    DEVELOPMENT_CARD = "development_card"


class TradeType(str, Enum):
    PLAYER = "player"
    BANK = "bank"
    PORT = "port"


class Player(BaseModel):
    id: int
    name: str
    victory_points: int = 0
    resources: Dict[Resource, int] = Field(default_factory=dict)
    roads: List[Tuple[int, int]] = Field(
        default_factory=list,
        description="Edges as (node_a, node_b) ids.",
    )
    settlements: List[int] = Field(default_factory=list, description="Node ids.")
    cities: List[int] = Field(default_factory=list, description="Node ids.")


class HexTile(BaseModel):
    id: int
    resource: Optional[Resource]  # desert can be None
    number_token: Optional[int]  # desert can be None


class RobberState(BaseModel):
    hex_id: int


class BoardState(BaseModel):
    """
    A highly simplified board representation intended for the model.
    """

    hexes: List[HexTile]
    robber: RobberState


class TurnPhase(str, Enum):
    START_OF_TURN = "start_of_turn"
    AFTER_ROLL = "after_roll"
    MAIN_ACTION = "main_action"
    END_OF_TURN = "end_of_turn"


class GameState(BaseModel):
    """
    Minimal but structured representation of a Catan game state tailored
    to LLM consumption.
    """

    players: List[Player]
    current_player_id: int
    board: BoardState
    turn_number: int
    phase: TurnPhase


class BuildAction(BaseModel):
    type: Literal["build"] = "build"
    build_type: BuildType
    location: str = Field(
        ...,
        description="Symbolic location identifier, e.g. 'node_12' or 'edge_5_6'.",
    )


class TradeAction(BaseModel):
    type: Literal["trade"] = "trade"
    trade_type: TradeType
    target_player_id: Optional[int] = Field(
        None, description="Required for player trades."
    )
    give: Dict[Resource, int]
    receive: Dict[Resource, int]


class RobberAction(BaseModel):
    type: Literal["move_robber"] = "move_robber"
    target_hex_id: int
    steal_from_player_id: Optional[int] = None


class EndTurnAction(BaseModel):
    type: Literal["end_turn"] = "end_turn"


MoveAction = BuildAction | TradeAction | RobberAction | EndTurnAction


class ModelMoveResponse(BaseModel):
    """
    The structured object the LLM must return as JSON.
    """

    reasoning: str = Field(
        ...,
        description="Short natural-language explanation of the move.",
    )
    action: MoveAction

