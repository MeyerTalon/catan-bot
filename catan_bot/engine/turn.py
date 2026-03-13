"""Action dataclasses and the single apply_action() entry-point.

Design
------
* All handlers mutate GameState in-place.
* Callers are responsible for legality (use rules.py before calling here).
* Random events (dice roll, stolen card selection) accept an optional
  ``random.Random`` instance so tests are deterministic.

Phase flow
----------
Normal turn:
    PRE_ROLL
      ├─ PlayKnight → MOVE_ROBBER → (STEAL →) PRE_ROLL   [pre-roll knight]
      └─ Roll ──────────────────────────────────────────→ POST_ROLL
                                                            or DISCARD → MOVE_ROBBER → (STEAL →) POST_ROLL
    POST_ROLL
      ├─ Build / BuyDev / MaritimeTrade  (stay in POST_ROLL)
      ├─ PlayKnight     → MOVE_ROBBER → (STEAL →) POST_ROLL
      ├─ PlayRoadBuilding → ROAD_BUILDING → POST_ROLL
      ├─ PlayYearOfPlenty  (stay in POST_ROLL)
      ├─ PlayMonopoly      (stay in POST_ROLL)
      └─ EndTurn ─────────────────────────────────────── next player's PRE_ROLL

Initial placement:
    INITIAL_SETTLEMENT → INITIAL_ROAD → INITIAL_SETTLEMENT → …
    (snake draft: 0,1,2,3,3,2,1,0 for 4 players)
    After last placement → player 0's PRE_ROLL
"""

from __future__ import annotations

import random as _random_module
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

from catan_bot.engine.rules import (
    legal_roads,
    legal_steal_targets,
    update_largest_army,
    update_longest_road,
)
from catan_bot.engine.state import BUILD_COSTS, DevCard, GameState, Phase
from catan_bot.models import Resource

# ---------------------------------------------------------------------------
# Action dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlaceInitialSettlement:
    vertex_id: int


@dataclass(frozen=True)
class PlaceInitialRoad:
    edge_id: int


@dataclass(frozen=True)
class Roll:
    """Roll the dice.  The result is sampled using the provided RNG."""


@dataclass(frozen=True)
class Discard:
    """Discard exactly ``discard_count(state, actor)`` cards."""
    resources: Dict[Resource, int]


@dataclass(frozen=True)
class MoveRobber:
    hex_id: int


@dataclass(frozen=True)
class Steal:
    """Steal from target_player_id, or None to pass when there are no targets."""
    target_player_id: Optional[int]


@dataclass(frozen=True)
class BuildRoad:
    edge_id: int


@dataclass(frozen=True)
class BuildSettlement:
    vertex_id: int


@dataclass(frozen=True)
class BuildCity:
    vertex_id: int


@dataclass(frozen=True)
class BuyDevCard:
    pass


@dataclass(frozen=True)
class PlayKnight:
    pass


@dataclass(frozen=True)
class PlayRoadBuilding:
    pass


@dataclass(frozen=True)
class PlaceRoadBuildingRoad:
    """Place one of the two free roads during Road Building."""
    edge_id: int


@dataclass(frozen=True)
class PlayYearOfPlenty:
    resource1: Resource
    resource2: Resource


@dataclass(frozen=True)
class PlayMonopoly:
    resource: Resource


@dataclass(frozen=True)
class MaritimeTrade:
    give: Resource
    ratio: int       # 2, 3, or 4
    receive: Resource


@dataclass(frozen=True)
class EndTurn:
    pass


Action = Union[
    PlaceInitialSettlement,
    PlaceInitialRoad,
    Roll,
    Discard,
    MoveRobber,
    Steal,
    BuildRoad,
    BuildSettlement,
    BuildCity,
    BuyDevCard,
    PlayKnight,
    PlayRoadBuilding,
    PlaceRoadBuildingRoad,
    PlayYearOfPlenty,
    PlayMonopoly,
    MaritimeTrade,
    EndTurn,
]


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------


def apply_action(
    state: GameState,
    action: Action,
    rng: Optional[_random_module.Random] = None,
) -> None:
    """Apply *action* to *state* in-place.

    Parameters
    ----------
    state  : mutable game state.
    action : a validated action (caller must check legality).
    rng    : seeded Random for reproducible dice/steal randomness.
             Defaults to the global random module.
    """
    _rng = rng or _random_module  # type: ignore[assignment]

    if isinstance(action, PlaceInitialSettlement):
        _initial_settlement(state, action.vertex_id)
    elif isinstance(action, PlaceInitialRoad):
        _initial_road(state, action.edge_id)
    elif isinstance(action, Roll):
        _roll(state, _rng)
    elif isinstance(action, Discard):
        _discard(state, action.resources)
    elif isinstance(action, MoveRobber):
        _move_robber(state, action.hex_id, _rng)
    elif isinstance(action, Steal):
        _steal(state, action.target_player_id, _rng)
    elif isinstance(action, BuildRoad):
        _build_road(state, action.edge_id)
    elif isinstance(action, BuildSettlement):
        _build_settlement(state, action.vertex_id)
    elif isinstance(action, BuildCity):
        _build_city(state, action.vertex_id)
    elif isinstance(action, BuyDevCard):
        _buy_dev_card(state)
    elif isinstance(action, PlayKnight):
        _play_knight(state)
    elif isinstance(action, PlayRoadBuilding):
        _play_road_building(state)
    elif isinstance(action, PlaceRoadBuildingRoad):
        _road_building_road(state, action.edge_id)
    elif isinstance(action, PlayYearOfPlenty):
        _play_year_of_plenty(state, action.resource1, action.resource2)
    elif isinstance(action, PlayMonopoly):
        _play_monopoly(state, action.resource)
    elif isinstance(action, MaritimeTrade):
        _maritime_trade(state, action.give, action.ratio, action.receive)
    elif isinstance(action, EndTurn):
        _end_turn(state)
    else:
        raise ValueError(f"Unknown action type: {type(action)}")


def current_actor(state: GameState) -> int:
    """Return the player_id who must act next.

    During DISCARD this is the first player in the pending queue, not
    necessarily the player who rolled.
    """
    if state.phase == Phase.DISCARD and state.pending_discard_players:
        return state.pending_discard_players[0]
    return state.current_player


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _check_win(state: GameState) -> None:
    if state.winner is not None:
        state.phase = Phase.GAME_OVER


def _start_turn(state: GameState) -> None:
    """Prepare state for the start of the current player's normal turn."""
    p = state.players[state.current_player]
    # Newly bought dev cards become playable.
    for card in DevCard:
        p.dev_cards[card] = p.dev_cards.get(card, 0) + p.dev_cards_new.get(card, 0)
        p.dev_cards_new[card] = 0
    p.has_played_dev_this_turn = False
    state.last_roll = None
    state.turn_number += 1
    state.phase = Phase.PRE_ROLL


def _after_robber(state: GameState) -> None:
    """Return to the correct phase after robber + optional steal resolves."""
    if state.last_roll is None:
        # Knight was played before rolling; player still needs to roll.
        state.phase = Phase.PRE_ROLL
    else:
        state.phase = Phase.POST_ROLL


# ---------------------------------------------------------------------------
# Initial placement
# ---------------------------------------------------------------------------


def _initial_settlement(state: GameState, vertex_id: int) -> None:
    player_id = state.current_player
    state.settlements[vertex_id] = player_id
    state.last_initial_settlement = vertex_id

    # Second-round placements give starting resources.
    if state.is_second_initial_settlement:
        for hid in state.board.vertex_hexes[vertex_id]:
            res = state.board.hex_resources[hid]
            if res is not None:
                state.players[player_id].receive(res)

    state.phase = Phase.INITIAL_ROAD


def _initial_road(state: GameState, edge_id: int) -> None:
    state.roads[edge_id] = state.current_player
    state.initial_placement_index += 1

    if state.initial_placement_done:
        # Snake draft finished — normal play begins with player 0.
        state.current_player = 0
        _start_turn(state)
    else:
        state.current_player = (
            state.initial_placement_order[state.initial_placement_index]
        )
        state.phase = Phase.INITIAL_SETTLEMENT


# ---------------------------------------------------------------------------
# Dice roll and resource distribution
# ---------------------------------------------------------------------------


def _roll(state: GameState, rng) -> None:
    total = rng.randint(1, 6) + rng.randint(1, 6)
    state.last_roll = total

    if total == 7:
        state.pending_discard_players = [
            pid
            for pid in range(len(state.players))
            if state.players[pid].resource_count > 7
        ]
        if state.pending_discard_players:
            state.phase = Phase.DISCARD
        else:
            state.phase = Phase.MOVE_ROBBER
    else:
        _distribute_resources(state, total)
        state.phase = Phase.POST_ROLL


def _distribute_resources(state: GameState, roll: int) -> None:
    for hid, token in state.board.hex_tokens.items():
        if token != roll or hid == state.robber_hex:
            continue
        res = state.board.hex_resources[hid]
        if res is None:
            continue
        for vid in state.board.hex_vertices[hid]:
            if vid in state.settlements:
                state.players[state.settlements[vid]].receive(res, 1)
            elif vid in state.cities:
                state.players[state.cities[vid]].receive(res, 2)


# ---------------------------------------------------------------------------
# Discard (after rolling 7)
# ---------------------------------------------------------------------------


def _discard(state: GameState, resources: Dict[Resource, int]) -> None:
    player_id = state.pending_discard_players.pop(0)
    p = state.players[player_id]
    for r, amt in resources.items():
        p.resources[r] -= amt

    if not state.pending_discard_players:
        state.phase = Phase.MOVE_ROBBER


# ---------------------------------------------------------------------------
# Robber
# ---------------------------------------------------------------------------


def _move_robber(state: GameState, hex_id: int, rng) -> None:
    state.robber_hex = hex_id
    targets = legal_steal_targets(state, state.current_player)
    if targets:
        state.phase = Phase.STEAL
    else:
        _after_robber(state)


def _steal(
    state: GameState,
    target_player_id: Optional[int],
    rng,
) -> None:
    if target_player_id is not None:
        target = state.players[target_player_id]
        available = [r for r, cnt in target.resources.items() if cnt > 0]
        if available:
            stolen = rng.choice(available)
            target.resources[stolen] -= 1
            state.players[state.current_player].receive(stolen)
    _after_robber(state)


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


def _build_road(state: GameState, edge_id: int) -> None:
    state.players[state.current_player].pay(BUILD_COSTS["road"])
    state.roads[edge_id] = state.current_player
    update_longest_road(state)
    _check_win(state)


def _build_settlement(state: GameState, vertex_id: int) -> None:
    state.players[state.current_player].pay(BUILD_COSTS["settlement"])
    state.settlements[vertex_id] = state.current_player
    update_longest_road(state)   # opponent roads may be split
    _check_win(state)


def _build_city(state: GameState, vertex_id: int) -> None:
    state.players[state.current_player].pay(BUILD_COSTS["city"])
    del state.settlements[vertex_id]
    state.cities[vertex_id] = state.current_player
    _check_win(state)


# ---------------------------------------------------------------------------
# Development cards — buy
# ---------------------------------------------------------------------------


def _buy_dev_card(state: GameState) -> None:
    player_id = state.current_player
    state.players[player_id].pay(BUILD_COSTS["dev_card"])
    card = state.draw_dev_card()
    if card is not None:
        p = state.players[player_id]
        p.dev_cards_new[card] = p.dev_cards_new.get(card, 0) + 1
    _check_win(state)   # drawn VP card might complete 10 points


# ---------------------------------------------------------------------------
# Development cards — play
# ---------------------------------------------------------------------------


def _use_dev_card(state: GameState, card: DevCard) -> None:
    """Move card from playable hand to played pile and set the turn flag."""
    p = state.players[state.current_player]
    p.dev_cards[card] -= 1
    p.dev_cards_played[card] = p.dev_cards_played.get(card, 0) + 1
    p.has_played_dev_this_turn = True


def _play_knight(state: GameState) -> None:
    _use_dev_card(state, DevCard.KNIGHT)
    update_largest_army(state)
    _check_win(state)
    if state.phase != Phase.GAME_OVER:
        state.phase = Phase.MOVE_ROBBER


def _play_road_building(state: GameState) -> None:
    _use_dev_card(state, DevCard.ROAD_BUILDING)
    state.road_building_roads_placed = 0
    # Skip immediately if no roads can be placed (e.g. all 15 used).
    if not legal_roads(state, state.current_player, free=True):
        state.phase = Phase.POST_ROLL
    else:
        state.phase = Phase.ROAD_BUILDING


def _road_building_road(state: GameState, edge_id: int) -> None:
    state.roads[edge_id] = state.current_player
    update_longest_road(state)
    state.road_building_roads_placed += 1
    _check_win(state)
    if state.phase == Phase.GAME_OVER:
        return
    if state.road_building_roads_placed >= 2:
        state.phase = Phase.POST_ROLL
    elif not legal_roads(state, state.current_player, free=True):
        # No room for second road.
        state.phase = Phase.POST_ROLL


def _play_year_of_plenty(
    state: GameState, r1: Resource, r2: Resource
) -> None:
    _use_dev_card(state, DevCard.YEAR_OF_PLENTY)
    p = state.players[state.current_player]
    p.receive(r1)
    p.receive(r2)
    # Phase stays POST_ROLL.


def _play_monopoly(state: GameState, resource: Resource) -> None:
    _use_dev_card(state, DevCard.MONOPOLY)
    p = state.players[state.current_player]
    total = 0
    for pid, other in enumerate(state.players):
        if pid == state.current_player:
            continue
        taken = other.resources.get(resource, 0)
        other.resources[resource] = 0
        total += taken
    p.receive(resource, total)
    # Phase stays POST_ROLL.


# ---------------------------------------------------------------------------
# Maritime trade
# ---------------------------------------------------------------------------


def _maritime_trade(
    state: GameState, give: Resource, ratio: int, receive: Resource
) -> None:
    p = state.players[state.current_player]
    p.resources[give] -= ratio
    p.receive(receive)


# ---------------------------------------------------------------------------
# End turn
# ---------------------------------------------------------------------------


def _end_turn(state: GameState) -> None:
    _check_win(state)
    if state.phase == Phase.GAME_OVER:
        return
    n = len(state.players)
    state.current_player = (state.current_player + 1) % n
    _start_turn(state)
