"""what one player is allowed to see of a game.

`GameState` holds everything, including other players' hands and the order of
the development deck. `game_view` strips that down to public information plus
the viewer's own hand, and attaches the viewer's legal actions and the board
geometry a client needs to draw it.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from pydantic import BaseModel

from .actions import Action, Discard
from .board import topology
from .engine import MAX_TRADE_PROPOSALS_PER_TURN, GameEngine
from .models import (
    Board,
    DevCard,
    LogEntry,
    Resource,
    TradeOffer,
    TurnPhase,
)

LOG_TAIL = 60


class PlayerView(BaseModel):
    """one seat as seen by the viewer; hands are private unless it is theirs."""

    id: int
    name: str
    victory_points: int
    resource_count: int
    dev_card_count: int
    knights_played: int
    longest_road_length: int
    roads: List[Tuple[int, int]]
    settlements: List[int]
    cities: List[int]
    resources: Dict[Resource, int] | None = None
    dev_cards: List[DevCard] | None = None
    new_dev_cards: List[DevCard] | None = None
    trade_ratios: Dict[Resource, int] | None = None


class GameView(BaseModel):
    """a game from one seat's point of view.

    `legal_actions` never lists discards (there can be thousands of them);
    `discards_owed` says how many cards each player must return instead.
    """

    viewer_id: int | None
    players: List[PlayerView]
    board: Board
    node_positions: List[Tuple[float, float]]
    edges: List[Tuple[int, int]]
    current_player_id: int
    turn_number: int
    phase: TurnPhase
    dice: Tuple[int, int] | None
    bank: Dict[Resource, int]
    dev_deck_count: int
    discards_owed: Dict[int, int]
    free_roads: int
    dev_card_played: bool
    trade_offer: TradeOffer | None
    trades_left: int
    longest_road_player_id: int | None
    largest_army_player_id: int | None
    winner_id: int | None
    waiting_on: List[int]
    legal_actions: List[Action]
    log: List[LogEntry]


def game_view(engine: GameEngine, viewer_id: int | None) -> GameView:
    """builds the view of a game for one seat.

    Args:
        engine: the game.
        viewer_id: the viewer's seat, or None for a spectator (no private info).

    Returns:
        the redacted view.
    """
    state = engine.state
    finished = state.phase == TurnPhase.GAME_OVER
    players = []
    for p in state.players:
        mine = p.id == viewer_id
        # hidden victory point cards are revealed once the game ends
        players.append(
            PlayerView(
                id=p.id,
                name=p.name,
                victory_points=engine.victory_points(
                    p.id, include_hidden=mine or finished
                ),
                resource_count=p.card_count(),
                dev_card_count=len(p.dev_cards) + len(p.new_dev_cards),
                knights_played=p.knights_played,
                longest_road_length=engine.longest_road_length(p.id),
                roads=p.roads,
                settlements=p.settlements,
                cities=p.cities,
                resources=dict(p.resources) if mine else None,
                dev_cards=list(p.dev_cards) if mine else None,
                new_dev_cards=list(p.new_dev_cards) if mine else None,
                trade_ratios=(
                    {r: engine.trade_ratio(p.id, r) for r in Resource} if mine else None
                ),
            )
        )

    legal: List[Action] = []
    if viewer_id is not None and state.phase != TurnPhase.DISCARD:
        legal = [
            a for a in engine.legal_actions(viewer_id) if not isinstance(a, Discard)
        ]

    topo = topology()
    return GameView(
        viewer_id=viewer_id,
        players=players,
        board=state.board,
        node_positions=topo.node_positions,
        edges=topo.edges,
        current_player_id=state.current_player_id,
        turn_number=state.turn_number,
        phase=state.phase,
        dice=state.dice,
        bank=state.bank,
        dev_deck_count=len(state.dev_deck),
        discards_owed=state.discards_owed,
        free_roads=state.free_roads,
        dev_card_played=state.dev_card_played,
        trade_offer=state.trade_offer,
        trades_left=MAX_TRADE_PROPOSALS_PER_TURN - state.trades_proposed,
        longest_road_player_id=state.longest_road_player_id,
        largest_army_player_id=state.largest_army_player_id,
        winner_id=state.winner_id,
        waiting_on=engine.actors(),
        legal_actions=legal,
        log=state.log[-LOG_TAIL:],
    )
