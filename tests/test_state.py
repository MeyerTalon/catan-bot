"""Tests for engine/state.py — GameState creation, queries, and copy."""

import pytest

from catan_bot.board import generate_standard_board, generate_random_board
from catan_bot.engine.state import (
    DEV_CARD_COUNTS,
    MAX_CITIES,
    MAX_ROADS,
    MAX_SETTLEMENTS,
    WIN_VP,
    DevCard,
    GameState,
    Phase,
    PlayerState,
)
from catan_bot.models import Resource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fresh_state():
    board = generate_standard_board()
    return GameState.create_new(board=board, n_players=4, seed=0)


# ---------------------------------------------------------------------------
# Initial state invariants
# ---------------------------------------------------------------------------


def test_phase_is_initial_settlement(fresh_state):
    assert fresh_state.phase == Phase.INITIAL_SETTLEMENT


def test_correct_number_of_players(fresh_state):
    assert len(fresh_state.players) == 4


def test_player_ids_match_indices(fresh_state):
    for i, p in enumerate(fresh_state.players):
        assert p.player_id == i


def test_starting_resources_are_zero(fresh_state):
    for player in fresh_state.players:
        assert player.resource_count == 0


def test_starting_dev_cards_are_zero(fresh_state):
    for player in fresh_state.players:
        assert player.dev_card_count == 0


def test_board_occupation_empty(fresh_state):
    assert len(fresh_state.settlements) == 0
    assert len(fresh_state.cities) == 0
    assert len(fresh_state.roads) == 0


def test_dev_deck_has_25_cards(fresh_state):
    assert fresh_state.dev_deck_remaining == 25
    assert sum(DEV_CARD_COUNTS.values()) == 25


def test_dev_deck_composition(fresh_state):
    from collections import Counter
    counts = Counter(fresh_state.dev_deck)
    for card, expected in DEV_CARD_COUNTS.items():
        assert counts[card] == expected


def test_robber_starts_on_desert(fresh_state):
    desert_hid = next(
        hid for hid, res in fresh_state.board.hex_resources.items() if res is None
    )
    assert fresh_state.robber_hex == desert_hid


def test_initial_placement_snake_order(fresh_state):
    order = fresh_state.initial_placement_order
    assert order == [0, 1, 2, 3, 3, 2, 1, 0]
    assert fresh_state.current_player == 0


def test_no_special_awards_at_start(fresh_state):
    assert fresh_state.longest_road_player is None
    assert fresh_state.largest_army_player is None


def test_winner_is_none_at_start(fresh_state):
    assert fresh_state.winner is None


# ---------------------------------------------------------------------------
# Piece-count helpers
# ---------------------------------------------------------------------------


def test_all_pieces_available_at_start(fresh_state):
    for pid in range(4):
        assert fresh_state.settlements_remaining(pid) == MAX_SETTLEMENTS
        assert fresh_state.cities_remaining(pid) == MAX_CITIES
        assert fresh_state.roads_remaining(pid) == MAX_ROADS


def test_settlements_on_board_reflects_dict(fresh_state):
    s = fresh_state.copy()
    s.settlements[5] = 0
    assert s.settlements_on_board(0) == 1
    assert s.settlements_on_board(1) == 0


def test_cities_on_board_reflects_dict(fresh_state):
    s = fresh_state.copy()
    s.cities[10] = 2
    assert s.cities_on_board(2) == 1
    assert s.cities_on_board(0) == 0


# ---------------------------------------------------------------------------
# Victory points
# ---------------------------------------------------------------------------


def test_vp_zero_at_start(fresh_state):
    for pid in range(4):
        assert fresh_state.victory_points(pid) == 0


def test_vp_settlement_counts(fresh_state):
    s = fresh_state.copy()
    s.settlements[5] = 0
    assert s.victory_points(0) == 1


def test_vp_city_counts_two(fresh_state):
    s = fresh_state.copy()
    s.cities[5] = 0
    assert s.victory_points(0) == 2


def test_vp_longest_road_adds_two(fresh_state):
    s = fresh_state.copy()
    s.longest_road_player = 1
    assert s.victory_points(1) == 2
    assert s.victory_points(0) == 0


def test_vp_largest_army_adds_two(fresh_state):
    s = fresh_state.copy()
    s.largest_army_player = 2
    assert s.victory_points(2) == 2


def test_vp_dev_card_hidden_in_public_count(fresh_state):
    s = fresh_state.copy()
    s.players[0].dev_cards[DevCard.VICTORY_POINT] = 2
    assert s.victory_points(0) == 2
    assert s.public_victory_points(0) == 0


def test_winner_detected_at_10_vp(fresh_state):
    s = fresh_state.copy()
    # 5 settlements + 2 cities + longest road + largest army = 5 + 4 + 2 + 2 = 13
    for v in range(5):
        s.settlements[v] = 0
    for v in range(5, 7):
        s.cities[v] = 0
    s.longest_road_player = 0
    s.largest_army_player = 0
    assert s.winner == 0


# ---------------------------------------------------------------------------
# PlayerState helpers
# ---------------------------------------------------------------------------


def test_can_afford_exact(fresh_state):
    p = fresh_state.players[0].copy()
    p.resources[Resource.BRICK] = 1
    p.resources[Resource.LUMBER] = 1
    assert p.can_afford({Resource.BRICK: 1, Resource.LUMBER: 1})


def test_cannot_afford_short(fresh_state):
    p = fresh_state.players[0].copy()
    p.resources[Resource.BRICK] = 0
    assert not p.can_afford({Resource.BRICK: 1})


def test_pay_deducts_resources(fresh_state):
    p = fresh_state.players[0].copy()
    p.resources[Resource.ORE] = 3
    p.pay({Resource.ORE: 2})
    assert p.resources[Resource.ORE] == 1


def test_receive_adds_resources(fresh_state):
    p = fresh_state.players[0].copy()
    p.receive(Resource.GRAIN, 3)
    assert p.resources[Resource.GRAIN] == 3


def test_army_size_tracks_knights(fresh_state):
    p = fresh_state.players[0].copy()
    p.dev_cards_played[DevCard.KNIGHT] = 3
    assert p.army_size == 3


# ---------------------------------------------------------------------------
# Port / trade ratio
# ---------------------------------------------------------------------------


def test_best_trade_ratio_no_port(fresh_state):
    # No settlements placed → no ports → 4:1 bank
    assert fresh_state.best_trade_ratio(0, Resource.BRICK) == 4


def test_best_trade_ratio_generic_port(fresh_state):
    s = fresh_state.copy()
    # Give player 0 a vertex that has a 3:1 port
    generic_port_vertex = next(
        vid for vid, res in s.board.vertex_ports.items() if res is None
    )
    s.settlements[generic_port_vertex] = 0
    assert s.best_trade_ratio(0, Resource.BRICK) == 3


def test_best_trade_ratio_specific_port(fresh_state):
    s = fresh_state.copy()
    # Give player 0 a vertex with a 2:1 Brick port
    brick_port_vertex = next(
        vid for vid, res in s.board.vertex_ports.items() if res == Resource.BRICK
    )
    s.settlements[brick_port_vertex] = 0
    assert s.best_trade_ratio(0, Resource.BRICK) == 2
    # Other resources should still be 4:1 (no generic port)
    assert s.best_trade_ratio(0, Resource.WOOL) == 4


# ---------------------------------------------------------------------------
# Copy isolation
# ---------------------------------------------------------------------------


def test_copy_is_independent(fresh_state):
    original = fresh_state.copy()
    clone = original.copy()
    clone.settlements[99] = 0
    clone.players[0].resources[Resource.ORE] = 99
    clone.phase = Phase.GAME_OVER

    assert 99 not in original.settlements
    assert original.players[0].resources[Resource.ORE] == 0
    assert original.phase == Phase.INITIAL_SETTLEMENT


def test_copy_shares_board_reference(fresh_state):
    clone = fresh_state.copy()
    assert clone.board is fresh_state.board


# ---------------------------------------------------------------------------
# Random board smoke test
# ---------------------------------------------------------------------------


def test_create_new_with_random_board():
    for seed in range(5):
        s = GameState.create_new(n_players=4, seed=seed)
        assert s.winner is None
        assert s.phase == Phase.INITIAL_SETTLEMENT
        assert s.dev_deck_remaining == 25


def test_create_new_deterministic():
    s1 = GameState.create_new(seed=42)
    s2 = GameState.create_new(seed=42)
    assert s1.dev_deck == s2.dev_deck
    assert s1.robber_hex == s2.robber_hex
    assert s1.board.hex_resources == s2.board.hex_resources
