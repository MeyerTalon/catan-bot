"""actions a player can submit to the engine.

each action carries a literal `type` so the union can be parsed from json
without knowing the concrete class up front.
"""

from __future__ import annotations

from typing import Annotated, Literal, Tuple

from pydantic import BaseModel, Field


class BuildRoad(BaseModel):
    """place a road on an edge."""

    type: Literal['build_road'] = 'build_road'
    edge: Tuple[int, int]


class BuildSettlement(BaseModel):
    """place a settlement on a node."""

    type: Literal['build_settlement'] = 'build_settlement'
    node: int


class BuildCity(BaseModel):
    """upgrade an owned settlement to a city."""

    type: Literal['build_city'] = 'build_city'
    node: int


class EndTurn(BaseModel):
    """pass play to the next player."""

    type: Literal['end_turn'] = 'end_turn'


Action = Annotated[
    BuildRoad | BuildSettlement | BuildCity | EndTurn,
    Field(discriminator='type'),
]
