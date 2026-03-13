"""Tests for engine/rules.py.

Uses a fixed board (generate_standard_board) and manually constructs
game states to probe each legality function in isolation.
"""

import pytest

from catan_bot.board import generate_standard_board
from catan_bot.engine.rules import (
    can_buy_dev,
    can_play_dev,
    discard_count,
    legal_cities,
    legal_initial_roads,
    legal_initial_settlements,
    legal_maritime_trades,
    legal_robber_hexes,
    legal_roads,
    legal_settlements,
    legal_steal_targets,
    road_length,
    update_largest_army,
    update_longest_road,
)
from catan_bot.engine.state import BUILD_COSTS, DevCard, GameState, Phase
from catan_bot.models import Resource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def board():
    return generate_standard_board()


@pytest.fixture
def state(board):
    """Fresh game state with an empty board."""
    return GameState.create_new(board=board, n_players=4, seed=0)


# Grab a stable vertex to use as "vertex 0" in tests
def first_vertex(board):
    return min(board.vertex_positions)


def neighbors_of(board, vertex_id):
    return board.vertex_neighbors[vertex_id]


def edges_of(board, vertex_id):
    return board.vertex_edges[vertex_id]


# ---------------------------------------------------------------------------
# Initial settlement legality
# ---------------------------------------------------------------------------


class TestInitialSettlements:
    def test_all_54_vertices_legal_on_empty_board(self, state):
        legal = legal_initial_settlements(state)
        assert len(legal) == 54

    def test_occupied_vertex_not_legal(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        s.settlements[v] = 0
        assert v not in legal_initial_settlements(s)

    def test_adjacent_vertex_not_legal(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        s.settlements[v] = 0
        for nb in neighbors_of(s.board, v):
            assert nb not in legal_initial_settlements(s)

    def test_non_adjacent_vertex_still_legal(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        s.settlements[v] = 0
        legal = legal_initial_settlements(s)
        # Vertices 2+ hops away are still legal
        blocked = {v} | set(neighbors_of(s.board, v))
        assert any(vid not in blocked for vid in legal)

    def test_city_also_blocks_adjacent(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        s.cities[v] = 1  # a city blocks neighbors too
        for nb in neighbors_of(s.board, v):
            assert nb not in legal_initial_settlements(s)


# ---------------------------------------------------------------------------
# Initial road legality
# ---------------------------------------------------------------------------


class TestInitialRoads:
    def test_roads_adjacent_to_anchor(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        s.last_initial_settlement = v
        expected = set(edges_of(s.board, v))
        assert set(legal_initial_roads(s)) == expected

    def test_already_placed_road_excluded(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        s.last_initial_settlement = v
        road_edge = edges_of(s.board, v)[0]
        s.roads[road_edge] = 0
        assert road_edge not in legal_initial_roads(s)

    def test_no_anchor_returns_empty(self, state):
        assert legal_initial_roads(state) == []


# ---------------------------------------------------------------------------
# Normal settlement legality
# ---------------------------------------------------------------------------


class TestSettlements:
    def _give_resources(self, player, cost):
        for r, amt in cost.items():
            player.resources[r] = amt

    def test_no_roads_means_no_legal_settlements(self, state):
        s = state.copy()
        self._give_resources(s.players[0], BUILD_COSTS["settlement"])
        assert legal_settlements(s, 0) == []

    def test_vertex_connected_via_road(self, state):
        s = state.copy()
        self._give_resources(s.players[0], BUILD_COSTS["settlement"])
        v = first_vertex(s.board)
        road_edge = edges_of(s.board, v)[0]
        # Place a road; the other endpoint of this road is a candidate
        v1, v2 = s.board.edge_vertices[road_edge]
        s.roads[road_edge] = 0
        legal = legal_settlements(s, 0)
        # v1 and v2 are the endpoints; whichever is free & far enough is legal
        assert v1 in legal or v2 in legal

    def test_distance_rule_still_applies(self, state):
        s = state.copy()
        self._give_resources(s.players[0], BUILD_COSTS["settlement"])
        v = first_vertex(s.board)
        road_edge = edges_of(s.board, v)[0]
        s.roads[road_edge] = 0
        v1, v2 = s.board.edge_vertices[road_edge]
        # Place opponent settlement at v1 — neither v1 nor its neighbors legal
        s.settlements[v1] = 1
        legal = legal_settlements(s, 0)
        assert v1 not in legal
        for nb in neighbors_of(s.board, v1):
            assert nb not in legal

    def test_cannot_afford_returns_empty(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        road_edge = edges_of(s.board, v)[0]
        s.roads[road_edge] = 0
        # No resources given → can't afford
        assert legal_settlements(s, 0) == []

    def test_no_pieces_remaining_returns_empty(self, state):
        s = state.copy()
        self._give_resources(s.players[0], BUILD_COSTS["settlement"])
        v = first_vertex(s.board)
        road_edge = edges_of(s.board, v)[0]
        s.roads[road_edge] = 0
        # Use all 5 settlement slots
        for i, vid in enumerate(list(s.board.vertex_positions)[:5]):
            s.settlements[vid] = 0
        assert legal_settlements(s, 0) == []


# ---------------------------------------------------------------------------
# Road legality
# ---------------------------------------------------------------------------


class TestRoads:
    def _give_road_resources(self, player):
        player.resources[Resource.BRICK] = 1
        player.resources[Resource.LUMBER] = 1

    def test_settlement_anchors_road(self, state):
        s = state.copy()
        self._give_road_resources(s.players[0])
        v = first_vertex(s.board)
        s.settlements[v] = 0
        legal = legal_roads(s, 0)
        # All edges incident to v must be legal
        for eid in edges_of(s.board, v):
            assert eid in legal

    def test_road_extends_from_road(self, state):
        s = state.copy()
        self._give_road_resources(s.players[0])
        v = first_vertex(s.board)
        eid = edges_of(s.board, v)[0]
        s.roads[eid] = 0
        legal = legal_roads(s, 0)
        # Edges incident to either endpoint of eid (and unoccupied) should be legal
        v1, v2 = s.board.edge_vertices[eid]
        adjacent_edges = set(edges_of(s.board, v1)) | set(edges_of(s.board, v2))
        adjacent_edges.discard(eid)
        for e in adjacent_edges:
            assert e in legal

    def test_opponent_building_severs_connection(self, state):
        s = state.copy()
        self._give_road_resources(s.players[0])
        # Player 0 road at edge (v1-v2); opponent at v2; new road must attach at v1 side
        v = first_vertex(s.board)
        eid = edges_of(s.board, v)[0]
        v1, v2 = s.board.edge_vertices[eid]
        s.roads[eid] = 0
        s.settlements[v2] = 1  # opponent at v2
        legal = legal_roads(s, 0)
        # Edges only incident to v2 (not v1) should NOT be legal
        v2_only_edges = [
            e for e in edges_of(s.board, v2)
            if e != eid and all(
                ep in (s.board.edge_vertices[e])
                for ep in [v2]
            )
        ]
        for e in v2_only_edges:
            ev1, ev2 = s.board.edge_vertices[e]
            # If this edge connects only through v2 (v1 not reachable from player's side)
            other_end = ev1 if ev2 == v2 else ev2
            if other_end != v1 and not any(
                s.roads.get(xe) == 0 for xe in edges_of(s.board, other_end)
            ):
                assert e not in legal

    def test_own_building_does_not_sever(self, state):
        s = state.copy()
        self._give_road_resources(s.players[0])
        v = first_vertex(s.board)
        eid = edges_of(s.board, v)[0]
        v1, v2 = s.board.edge_vertices[eid]
        s.roads[eid] = 0
        s.settlements[v2] = 0  # OWN settlement at v2 — should NOT sever
        legal = legal_roads(s, 0)
        # Edges at v2 should still be reachable
        assert any(
            e in legal for e in edges_of(s.board, v2) if e != eid
        )

    def test_free_road_ignores_cost(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        s.settlements[v] = 0
        # No resources, but free=True
        assert legal_roads(s, 0, free=True) != []
        assert legal_roads(s, 0, free=False) == []


# ---------------------------------------------------------------------------
# City legality
# ---------------------------------------------------------------------------


class TestCities:
    def test_can_upgrade_own_settlement(self, state):
        s = state.copy()
        for r, amt in BUILD_COSTS["city"].items():
            s.players[0].resources[r] = amt
        v = first_vertex(s.board)
        s.settlements[v] = 0
        assert v in legal_cities(s, 0)

    def test_cannot_upgrade_opponent_settlement(self, state):
        s = state.copy()
        for r, amt in BUILD_COSTS["city"].items():
            s.players[0].resources[r] = amt
        v = first_vertex(s.board)
        s.settlements[v] = 1  # opponent
        assert v not in legal_cities(s, 0)

    def test_cannot_upgrade_existing_city(self, state):
        s = state.copy()
        for r, amt in BUILD_COSTS["city"].items():
            s.players[0].resources[r] = amt
        v = first_vertex(s.board)
        s.cities[v] = 0  # already a city
        assert v not in legal_cities(s, 0)

    def test_cannot_afford(self, state):
        s = state.copy()
        v = first_vertex(s.board)
        s.settlements[v] = 0
        assert legal_cities(s, 0) == []


# ---------------------------------------------------------------------------
# Dev card legality
# ---------------------------------------------------------------------------


class TestDevCards:
    def test_can_buy_with_resources(self, state):
        s = state.copy()
        for r, amt in BUILD_COSTS["dev_card"].items():
            s.players[0].resources[r] = amt
        assert can_buy_dev(s, 0)

    def test_cannot_buy_without_resources(self, state):
        assert not can_buy_dev(state, 0)

    def test_cannot_buy_empty_deck(self, state):
        s = state.copy()
        for r, amt in BUILD_COSTS["dev_card"].items():
            s.players[0].resources[r] = amt
        s.dev_deck.clear()
        assert not can_buy_dev(s, 0)

    def test_can_play_knight_in_hand(self, state):
        s = state.copy()
        s.players[0].dev_cards[DevCard.KNIGHT] = 1
        assert can_play_dev(s, 0, DevCard.KNIGHT)

    def test_cannot_play_if_played_this_turn(self, state):
        s = state.copy()
        s.players[0].dev_cards[DevCard.KNIGHT] = 1
        s.players[0].has_played_dev_this_turn = True
        assert not can_play_dev(s, 0, DevCard.KNIGHT)

    def test_cannot_play_newly_bought_card(self, state):
        s = state.copy()
        s.players[0].dev_cards_new[DevCard.KNIGHT] = 1
        # dev_cards (playable) is still 0
        assert not can_play_dev(s, 0, DevCard.KNIGHT)

    def test_cannot_play_vp_card(self, state):
        s = state.copy()
        s.players[0].dev_cards[DevCard.VICTORY_POINT] = 1
        assert not can_play_dev(s, 0, DevCard.VICTORY_POINT)


# ---------------------------------------------------------------------------
# Robber + steal
# ---------------------------------------------------------------------------


class TestRobber:
    def test_all_hexes_except_current_are_legal(self, state):
        legal = legal_robber_hexes(state, 0)
        assert state.robber_hex not in legal
        assert len(legal) == 18  # 19 hexes minus 1

    def test_legal_steal_targets_adjacent_with_resources(self, state):
        s = state.copy()
        # Place robber on hex 5, put opponent settlement on an adjacent vertex
        robber_hex = 5
        s.robber_hex = robber_hex
        adj_vertex = s.board.hex_vertices[robber_hex][0]
        s.settlements[adj_vertex] = 1
        s.players[1].resources[Resource.BRICK] = 2
        targets = legal_steal_targets(s, 0)
        assert 1 in targets

    def test_player_with_no_resources_not_stealable(self, state):
        s = state.copy()
        robber_hex = 5
        s.robber_hex = robber_hex
        adj_vertex = s.board.hex_vertices[robber_hex][0]
        s.settlements[adj_vertex] = 1
        # Player 1 has 0 resources
        targets = legal_steal_targets(s, 0)
        assert 1 not in targets

    def test_own_building_not_a_steal_target(self, state):
        s = state.copy()
        robber_hex = 5
        s.robber_hex = robber_hex
        adj_vertex = s.board.hex_vertices[robber_hex][0]
        s.settlements[adj_vertex] = 0  # own settlement
        s.players[0].resources[Resource.BRICK] = 2
        targets = legal_steal_targets(s, 0)
        assert 0 not in targets


# ---------------------------------------------------------------------------
# Maritime trade
# ---------------------------------------------------------------------------


class TestMaritimeTrade:
    def test_no_trades_without_resources(self, state):
        assert legal_maritime_trades(state, 0) == []

    def test_bank_4to1_trade(self, state):
        s = state.copy()
        s.players[0].resources[Resource.BRICK] = 4
        trades = legal_maritime_trades(s, 0)
        brick_trades = [(g, r, rcv) for g, r, rcv in trades if g == Resource.BRICK]
        assert all(r == 4 for _, r, _ in brick_trades)
        assert len(brick_trades) == 4  # can get any of 4 other resources

    def test_generic_port_gives_3to1(self, state):
        s = state.copy()
        generic_v = next(
            vid for vid, res in s.board.vertex_ports.items() if res is None
        )
        s.settlements[generic_v] = 0
        s.players[0].resources[Resource.BRICK] = 3
        trades = legal_maritime_trades(s, 0)
        brick_trades = [(g, r, rcv) for g, r, rcv in trades if g == Resource.BRICK]
        assert all(r == 3 for _, r, _ in brick_trades)

    def test_specific_port_gives_2to1(self, state):
        s = state.copy()
        brick_v = next(
            vid for vid, res in s.board.vertex_ports.items()
            if res == Resource.BRICK
        )
        s.settlements[brick_v] = 0
        s.players[0].resources[Resource.BRICK] = 2
        trades = legal_maritime_trades(s, 0)
        brick_trades = [(g, r, rcv) for g, r, rcv in trades if g == Resource.BRICK]
        assert all(r == 2 for _, r, _ in brick_trades)

    def test_cannot_give_and_receive_same_resource(self, state):
        s = state.copy()
        s.players[0].resources[Resource.BRICK] = 4
        trades = legal_maritime_trades(s, 0)
        assert all(give != receive for give, _, receive in trades)


# ---------------------------------------------------------------------------
# Discard
# ---------------------------------------------------------------------------


class TestDiscard:
    def test_no_discard_under_8_cards(self, state):
        s = state.copy()
        s.players[0].resources[Resource.BRICK] = 7
        assert discard_count(s, 0) == 0

    def test_discard_half_when_over_7(self, state):
        s = state.copy()
        s.players[0].resources[Resource.BRICK] = 8
        assert discard_count(s, 0) == 4

    def test_discard_floors(self, state):
        s = state.copy()
        s.players[0].resources[Resource.BRICK] = 9
        assert discard_count(s, 0) == 4  # floor(9/2) = 4

    def test_discard_large_hand(self, state):
        s = state.copy()
        s.players[0].resources[Resource.BRICK] = 14
        assert discard_count(s, 0) == 7


# ---------------------------------------------------------------------------
# Road length
# ---------------------------------------------------------------------------


class TestRoadLength:
    def _place_road_chain(self, state, player_id, edge_ids):
        """Place roads along a list of edge IDs without checking legality."""
        for eid in edge_ids:
            state.roads[eid] = player_id

    def test_empty_road_network(self, state):
        assert road_length(state, 0) == 0

    def test_single_road(self, state):
        s = state.copy()
        eid = list(s.board.edge_vertices)[0]
        s.roads[eid] = 0
        assert road_length(s, 0) == 1

    def test_linear_chain(self, state):
        """Build a straight chain of 5 roads and verify length == 5."""
        s = state.copy()
        # Walk the board graph: pick a starting vertex and extend linearly
        v = first_vertex(s.board)
        current_v = v
        chain = []
        visited_v = {current_v}
        for _ in range(5):
            found = False
            for eid in edges_of(s.board, current_v):
                if eid in chain:
                    continue
                ev1, ev2 = s.board.edge_vertices[eid]
                nxt = ev2 if ev1 == current_v else ev1
                if nxt not in visited_v:
                    chain.append(eid)
                    visited_v.add(nxt)
                    current_v = nxt
                    found = True
                    break
            if not found:
                break
        self._place_road_chain(s, 0, chain)
        assert road_length(s, 0) == len(chain)

    def test_opponent_building_splits_road(self, state):
        """A-B-C-D linear road; opponent at B → longest segment is 2 (B-C-D)."""
        s = state.copy()
        # Find a linear sequence of 3 roads: edge0=(vA,vB), edge1=(vB,vC), edge2=(vC,vD)
        vA = first_vertex(s.board)
        eAB = edges_of(s.board, vA)[0]
        vB = s.board.edge_vertices[eAB]
        vB = vB[1] if vB[0] == vA else vB[0]

        # Find edge from vB that doesn't lead back to vA
        eBC = next(
            e for e in edges_of(s.board, vB)
            if e != eAB and vA not in s.board.edge_vertices[e]
        )
        vC = s.board.edge_vertices[eBC]
        vC = vC[1] if vC[0] == vB else vC[0]

        eCD = next(
            e for e in edges_of(s.board, vC)
            if e != eBC and vB not in s.board.edge_vertices[e]
        )

        self._place_road_chain(s, 0, [eAB, eBC, eCD])
        # Without opponent: length should be 3
        assert road_length(s, 0) == 3

        # Place opponent at vB
        s.settlements[vB] = 1
        # Now: A-B (len 1) and B-C-D (len 2) → max = 2
        assert road_length(s, 0) == 2

    def test_own_building_does_not_break_road(self, state):
        """Own settlement at vB should NOT reduce road length."""
        s = state.copy()
        vA = first_vertex(s.board)
        eAB = edges_of(s.board, vA)[0]
        vB = s.board.edge_vertices[eAB]
        vB = vB[1] if vB[0] == vA else vB[0]

        eBC = next(
            e for e in edges_of(s.board, vB)
            if e != eAB and vA not in s.board.edge_vertices[e]
        )

        self._place_road_chain(s, 0, [eAB, eBC])
        s.settlements[vB] = 0  # own building — should not break
        assert road_length(s, 0) == 2


# ---------------------------------------------------------------------------
# Longest road award
# ---------------------------------------------------------------------------


class TestLongestRoad:
    def _lay_n_roads(self, state, player_id, n):
        """Lay n roads in a chain starting from an arbitrary free vertex."""
        v = first_vertex(state.board)
        current_v = v
        visited_v = {current_v}
        chain = []
        for _ in range(n):
            for eid in edges_of(state.board, current_v):
                if eid in state.roads:
                    continue
                ev1, ev2 = state.board.edge_vertices[eid]
                nxt = ev2 if ev1 == current_v else ev1
                if nxt not in visited_v:
                    state.roads[eid] = player_id
                    chain.append(eid)
                    visited_v.add(nxt)
                    current_v = nxt
                    break
        return chain

    def test_no_award_below_5(self, state):
        s = state.copy()
        self._lay_n_roads(s, 0, 4)
        update_longest_road(s)
        assert s.longest_road_player is None

    def test_award_at_5(self, state):
        s = state.copy()
        self._lay_n_roads(s, 0, 5)
        update_longest_road(s)
        assert s.longest_road_player == 0
        assert s.longest_road_length == 5

    def test_holder_not_displaced_by_equal_length(self, state):
        s = state.copy()
        self._lay_n_roads(s, 0, 5)
        update_longest_road(s)
        # Player 1 also reaches 5 — holder (0) keeps it
        # (We need different vertices; shift starting point)
        v = list(s.board.vertex_positions)[10]
        current_v = v
        visited_v = set(s.roads.values())  # crude — just use a fresh chain
        placed = 0
        for eid, (ev1, ev2) in s.board.edge_vertices.items():
            if eid not in s.roads:
                s.roads[eid] = 1
                placed += 1
                if placed == 5:
                    break
        update_longest_road(s)
        # Player 0 is still the holder (claimed first)
        assert s.longest_road_player == 0

    def test_holder_displaced_by_longer_road(self, state):
        s = state.copy()
        self._lay_n_roads(s, 0, 5)
        update_longest_road(s)
        # Give player 1 a longer road
        placed = 0
        for eid in s.board.edge_vertices:
            if eid not in s.roads:
                s.roads[eid] = 1
                placed += 1
                if placed == 7:
                    break
        update_longest_road(s)
        assert s.longest_road_player == 1

    def test_award_removed_when_holder_drops_below_5(self, state):
        s = state.copy()
        chain = self._lay_n_roads(s, 0, 5)
        update_longest_road(s)
        assert s.longest_road_player == 0
        # Remove all of player 0's roads
        for eid in chain:
            del s.roads[eid]
        update_longest_road(s)
        assert s.longest_road_player is None


# ---------------------------------------------------------------------------
# Largest army award
# ---------------------------------------------------------------------------


class TestLargestArmy:
    def test_no_award_below_3_knights(self, state):
        s = state.copy()
        s.players[0].dev_cards_played[DevCard.KNIGHT] = 2
        update_largest_army(s)
        assert s.largest_army_player is None

    def test_award_at_3_knights(self, state):
        s = state.copy()
        s.players[0].dev_cards_played[DevCard.KNIGHT] = 3
        update_largest_army(s)
        assert s.largest_army_player == 0
        assert s.largest_army_size == 3

    def test_holder_keeps_award_on_tie(self, state):
        s = state.copy()
        s.players[0].dev_cards_played[DevCard.KNIGHT] = 3
        update_largest_army(s)
        s.players[1].dev_cards_played[DevCard.KNIGHT] = 3
        update_largest_army(s)
        assert s.largest_army_player == 0  # holder keeps

    def test_holder_displaced_by_larger_army(self, state):
        s = state.copy()
        s.players[0].dev_cards_played[DevCard.KNIGHT] = 3
        update_largest_army(s)
        s.players[1].dev_cards_played[DevCard.KNIGHT] = 4
        update_largest_army(s)
        assert s.largest_army_player == 1
        assert s.largest_army_size == 4
