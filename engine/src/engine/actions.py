"""actions a player can submit to the engine.

each action carries a literal `type` so the union can be parsed from json
without knowing the concrete class up front.
"""

from __future__ import annotations

from typing import Annotated, Dict, Literal, Tuple

from pydantic import BaseModel, Field, TypeAdapter

from .models import Resource


class RollDice(BaseModel):
    """roll both dice to start the main part of the turn."""

    type: Literal['roll_dice'] = 'roll_dice'


class Discard(BaseModel):
    """return half a hand of more than seven cards after a 7 is rolled."""

    type: Literal['discard'] = 'discard'
    resources: Dict[Resource, int]


class MoveRobber(BaseModel):
    """move the robber and steal one card from a player next to its new hex."""

    type: Literal['move_robber'] = 'move_robber'
    hex_id: int
    victim_id: int | None = None


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


class BuyDevCard(BaseModel):
    """buy the top development card."""

    type: Literal['buy_dev_card'] = 'buy_dev_card'


class PlayKnight(BaseModel):
    """play a knight: move the robber and count towards largest army."""

    type: Literal['play_knight'] = 'play_knight'


class PlayRoadBuilding(BaseModel):
    """play road building: place two roads for free."""

    type: Literal['play_road_building'] = 'play_road_building'


class PlayYearOfPlenty(BaseModel):
    """play year of plenty: take any two resources from the bank."""

    type: Literal['play_year_of_plenty'] = 'play_year_of_plenty'
    resources: Tuple[Resource, Resource]


class PlayMonopoly(BaseModel):
    """play monopoly: every other player hands over all of one resource."""

    type: Literal['play_monopoly'] = 'play_monopoly'
    resource: Resource


class MaritimeTrade(BaseModel):
    """trade with the bank at 4:1, or at a better port rate."""

    type: Literal['maritime_trade'] = 'maritime_trade'
    give: Resource
    receive: Resource


class ProposeTrade(BaseModel):
    """offer `give` to the other players in exchange for `receive`."""

    type: Literal['propose_trade'] = 'propose_trade'
    give: Dict[Resource, int]
    receive: Dict[Resource, int]


class RespondTrade(BaseModel):
    """accept or reject the open trade offer."""

    type: Literal['respond_trade'] = 'respond_trade'
    accept: bool


class ConfirmTrade(BaseModel):
    """complete the open trade offer with one player who accepted it."""

    type: Literal['confirm_trade'] = 'confirm_trade'
    partner_id: int


class CancelTrade(BaseModel):
    """withdraw the open trade offer."""

    type: Literal['cancel_trade'] = 'cancel_trade'


class EndTurn(BaseModel):
    """pass play to the next player."""

    type: Literal['end_turn'] = 'end_turn'


Action = Annotated[
    RollDice
    | Discard
    | MoveRobber
    | BuildRoad
    | BuildSettlement
    | BuildCity
    | BuyDevCard
    | PlayKnight
    | PlayRoadBuilding
    | PlayYearOfPlenty
    | PlayMonopoly
    | MaritimeTrade
    | ProposeTrade
    | RespondTrade
    | ConfirmTrade
    | CancelTrade
    | EndTurn,
    Field(discriminator='type'),
]

action_adapter: TypeAdapter[Action] = TypeAdapter(Action)
