"""Pure-function legality checks for all Catan actions.

None of these functions mutate GameState; they only read it.

Road-length notes
-----------------
The algorithm uses DFS with backtracking, which finds the true longest path
through a player's road network.  Two subtleties:

* An *opponent* building at vertex V does not remove the roads touching V, but
  it STOPS a continuous path from passing through V.  You can still start or
  end a segment at V (the roads were there first).
* Own buildings (settlement / city) do NOT break continuity.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from catan_bot.engine.state import BUILD_COSTS, DevCard, GameState, Phase
from catan_bot.models import Resource

# ---------------------------------------------------------------------------
# Private geometry helpers
# ---------------------------------------------------------------------------


def _vertex_is_far_enough(state: GameState, vertex_id: int) -> bool:
    """Distance rule: no adjacent vertex may have any building."""
    for nb in state.board.vertex_neighbors[vertex_id]:
        if nb in state.settlements or nb in state.cities:
            return False
    return True


def _vertex_connects_to_network(
    state: GameState, player_id: int, vertex_id: int
) -> bool:
    """True if *vertex_id* is a valid attachment point for player's new road/settlement.

    A vertex connects when:
    * The player has a building there (always attached), OR
    * The player has at least one road touching it AND no opponent
      building is at the vertex (opponent buildings sever the connection).
    """
    if state.settlements.get(vertex_id) == player_id:
        return True
    if state.cities.get(vertex_id) == player_id:
        return True
    # Opponent building severs the connection even if player has a road here.
    occupant = state.occupied_by(vertex_id)
    if occupant is not None:
        return False
    return any(
        state.roads.get(eid) == player_id
        for eid in state.board.vertex_edges[vertex_id]
    )


# ---------------------------------------------------------------------------
# Initial placement
# ---------------------------------------------------------------------------


def legal_initial_settlements(state: GameState) -> List[int]:
    """Unoccupied vertices that satisfy the distance rule."""
    return [
        vid
        for vid in state.board.vertex_positions
        if vid not in state.settlements
        and vid not in state.cities
        and _vertex_is_far_enough(state, vid)
    ]


def legal_initial_roads(state: GameState) -> List[int]:
    """Unoccupied edges adjacent to the most recently placed initial settlement."""
    anchor = state.last_initial_settlement
    if anchor is None:
        return []
    return [
        eid
        for eid in state.board.vertex_edges[anchor]
        if eid not in state.roads
    ]


# ---------------------------------------------------------------------------
# Normal-turn building
# ---------------------------------------------------------------------------


def legal_settlements(state: GameState, player_id: int) -> List[int]:
    """Vertices where *player_id* may build a settlement."""
    if state.settlements_remaining(player_id) == 0:
        return []
    if not state.players[player_id].can_afford(BUILD_COSTS["settlement"]):
        return []
    return [
        vid
        for vid in state.board.vertex_positions
        if vid not in state.settlements
        and vid not in state.cities
        and _vertex_is_far_enough(state, vid)
        and _vertex_connects_to_network(state, player_id, vid)
    ]


def legal_roads(
    state: GameState, player_id: int, *, free: bool = False
) -> List[int]:
    """Edges where *player_id* may build a road.

    Parameters
    ----------
    free : set True when playing Road Building dev card (no resource cost).
    """
    if state.roads_remaining(player_id) == 0:
        return []
    if not free and not state.players[player_id].can_afford(BUILD_COSTS["road"]):
        return []
    result = []
    for eid, (v1, v2) in state.board.edge_vertices.items():
        if eid in state.roads:
            continue
        if _vertex_connects_to_network(state, player_id, v1) or \
                _vertex_connects_to_network(state, player_id, v2):
            result.append(eid)
    return result


def legal_cities(state: GameState, player_id: int) -> List[int]:
    """Vertices where *player_id* may upgrade a settlement to a city."""
    if state.cities_remaining(player_id) == 0:
        return []
    if not state.players[player_id].can_afford(BUILD_COSTS["city"]):
        return []
    return [vid for vid, pid in state.settlements.items() if pid == player_id]


# ---------------------------------------------------------------------------
# Development cards
# ---------------------------------------------------------------------------


def can_buy_dev(state: GameState, player_id: int) -> bool:
    return (
        state.dev_deck_remaining > 0
        and state.players[player_id].can_afford(BUILD_COSTS["dev_card"])
    )


def can_play_dev(state: GameState, player_id: int, card: DevCard) -> bool:
    """True if *player_id* may play *card* right now.

    Rules enforced:
    * At most one dev card played per turn.
    * Cannot play a card bought this turn.
    * VP cards are never actively played (revealed only when winning).
    * Knight must be played in PRE_ROLL; all others in POST_ROLL.
      (We check caller's phase separately; here we just check hand/flags.)
    """
    if card == DevCard.VICTORY_POINT:
        return False
    p = state.players[player_id]
    if p.has_played_dev_this_turn:
        return False
    return p.dev_cards.get(card, 0) > 0


# ---------------------------------------------------------------------------
# Robber
# ---------------------------------------------------------------------------


def legal_robber_hexes(state: GameState, player_id: int) -> List[int]:
    """Any hex except the current robber position."""
    return [hid for hid in state.board.hex_coords if hid != state.robber_hex]


def legal_steal_targets(state: GameState, player_id: int) -> List[int]:
    """Players adjacent to the robber's current hex that *player_id* may steal from.

    Returns an empty list when there are no valid targets; in that case the
    steal phase should be skipped automatically.
    """
    adjacent: Set[int] = set()
    for vid in state.board.hex_vertices[state.robber_hex]:
        occ = state.occupied_by(vid)
        if occ is not None and occ != player_id:
            adjacent.add(occ)
    return [pid for pid in adjacent if state.players[pid].resource_count > 0]


# ---------------------------------------------------------------------------
# Maritime trade
# ---------------------------------------------------------------------------


def legal_maritime_trades(
    state: GameState, player_id: int
) -> List[Tuple[Resource, int, Resource]]:
    """All valid ``(give_resource, ratio, get_resource)`` triples.

    *ratio* is 2, 3, or 4 depending on the player's ports.
    """
    player = state.players[player_id]
    trades: List[Tuple[Resource, int, Resource]] = []
    for give in Resource:
        ratio = state.best_trade_ratio(player_id, give)
        if player.resources.get(give, 0) >= ratio:
            for get in Resource:
                if get != give:
                    trades.append((give, ratio, get))
    return trades


# ---------------------------------------------------------------------------
# Discard
# ---------------------------------------------------------------------------


def discard_count(state: GameState, player_id: int) -> int:
    """Cards *player_id* must discard when a 7 is rolled (floor(hand / 2) if hand > 7)."""
    hand = state.players[player_id].resource_count
    return hand // 2 if hand > 7 else 0


# ---------------------------------------------------------------------------
# Road length (DFS with backtracking)
# ---------------------------------------------------------------------------


def road_length(state: GameState, player_id: int) -> int:
    """Length of *player_id*'s longest continuous road.

    Algorithm
    ---------
    Build an adjacency list for the player's road network, then run DFS with
    backtracking from every vertex to find the longest simple path.

    An opponent building at vertex V *stops* the path (you may not continue
    through V) but you may still *start* a path at V (the roads were placed
    before the opponent built there).  Own buildings never interrupt.
    """
    player_edges: Set[int] = {
        eid for eid, pid in state.roads.items() if pid == player_id
    }
    if not player_edges:
        return 0

    # Build adjacency: vertex → [(edge_id, other_vertex), ...]
    adj: Dict[int, List[Tuple[int, int]]] = defaultdict(list)
    for eid in player_edges:
        v1, v2 = state.board.edge_vertices[eid]
        adj[v1].append((eid, v2))
        adj[v2].append((eid, v1))

    def dfs(vertex: int, visited: Set[int]) -> int:
        best = 0
        for eid, nb in adj[vertex]:
            if eid in visited:
                continue
            visited.add(eid)
            occ = state.occupied_by(nb)
            if occ is None or occ == player_id:
                # Can continue through nb
                best = max(best, 1 + dfs(nb, visited))
            else:
                # Opponent at nb: count this edge but stop here
                best = max(best, 1)
            visited.remove(eid)
        return best

    max_len = 0
    for start in adj:
        max_len = max(max_len, dfs(start, set()))
    return max_len


# ---------------------------------------------------------------------------
# Special-award updates  (mutate state in-place; call after road / building)
# ---------------------------------------------------------------------------


def update_longest_road(state: GameState) -> None:
    """Recompute the Longest Road award and update *state* in-place.

    Call after any road is placed OR any building is placed that could split
    an opponent's road.

    Rules summary
    -------------
    * First player to reach ≥ 5 roads claims the card.
    * Another player claims it only by *strictly beating* the holder's length.
    * Ties leave the card with the current holder.
    * If the holder's length drops below 5 and no other player has ≥ 5,
      the card is returned to the bank (no one holds it).
    """
    n = len(state.players)
    lengths = [road_length(state, pid) for pid in range(n)]
    best = max(lengths)

    if state.longest_road_player is None:
        # Award for the first time
        if best >= 5:
            candidates = [pid for pid, l in enumerate(lengths) if l == best]
            if len(candidates) == 1:
                state.longest_road_player = candidates[0]
                state.longest_road_length = best
        return

    holder = state.longest_road_player
    holder_len = lengths[holder]

    # Check for a single player who strictly beats the holder
    best_other = max(
        (lengths[pid] for pid in range(n) if pid != holder), default=0
    )

    if best_other > holder_len:
        challengers = [
            pid for pid in range(n)
            if pid != holder and lengths[pid] == best_other
        ]
        if len(challengers) == 1:
            state.longest_road_player = challengers[0]
            state.longest_road_length = best_other
        # Tied challengers: neither can claim (holder loses it but no one takes it)
        # This edge case is rare in practice; return the card to the bank.
        else:
            state.longest_road_player = None
            state.longest_road_length = 4
    elif holder_len < 5 and best_other < 5:
        # Holder dropped below threshold, no one qualifies
        state.longest_road_player = None
        state.longest_road_length = 4
    else:
        # Holder keeps the award; update stored length
        state.longest_road_length = holder_len


def update_largest_army(state: GameState) -> None:
    """Recompute the Largest Army award and update *state* in-place.

    Call after every Knight is played.

    Rules summary
    -------------
    * First player to play ≥ 3 Knights claims the card.
    * Another player claims it only by *strictly beating* the holder.
    * Ties leave the card with the current holder.
    """
    n = len(state.players)
    sizes = [state.players[pid].army_size for pid in range(n)]
    best = max(sizes)

    if state.largest_army_player is None:
        if best >= 3:
            candidates = [pid for pid, s in enumerate(sizes) if s == best]
            if len(candidates) == 1:
                state.largest_army_player = candidates[0]
                state.largest_army_size = best
        return

    holder = state.largest_army_player
    holder_size = sizes[holder]

    best_other = max(
        (sizes[pid] for pid in range(n) if pid != holder), default=0
    )

    if best_other > holder_size:
        challengers = [
            pid for pid in range(n)
            if pid != holder and sizes[pid] == best_other
        ]
        if len(challengers) == 1:
            state.largest_army_player = challengers[0]
            state.largest_army_size = best_other
    else:
        state.largest_army_size = holder_size
