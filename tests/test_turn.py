"""Tests for engine/turn.py — apply_action and full game-flow sequences."""

import random

import pytest

from catan_bot.board import generate_standard_board
from catan_bot.engine.rules import legal_initial_roads, legal_initial_settlements
from catan_bot.engine.state import BUILD_COSTS, DevCard, GameState, Phase
from catan_bot.engine.turn import (
    Action,
    BuildCity,
    BuildRoad,
    BuildSettlement,
    BuyDevCard,
    Discard,
    EndTurn,
    MaritimeTrade,
    MoveRobber,
    PlaceInitialRoad,
    PlaceInitialSettlement,
    PlaceRoadBuildingRoad,
    PlayKnight,
    PlayMonopoly,
    PlayRoadBuilding,
    PlayYearOfPlenty,
    Roll,
    Steal,
    apply_action,
    current_actor,
)
from catan_bot.models import Resource


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def board():
    return generate_standard_board()


@pytest.fixture
def state(board):
    return GameState.create_new(board=board, n_players=4, seed=0)


def det_rng(result: int):
    """Return an RNG whose randint always returns result // 2 + result // 2."""
    rng = random.Random(0)
    # Monkey-patch randint so the sum is deterministic
    rng.randint = lambda a, b: result // 2 if result % 2 == 0 else (result // 2 + (result % 2))
    return rng


def fixed_roll_rng(total: int):
    """RNG that produces a specific dice total (splits evenly across two dice)."""
    half = total // 2
    rest = total - half

    class _FixedRng:
        _calls = 0

        def randint(self, a, b):
            self._calls += 1
            return half if self._calls % 2 == 1 else rest

        def choice(self, seq):
            return seq[0]

    return _FixedRng()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_initial_placement(state: GameState) -> None:
    """Complete the full initial placement for all players (snake draft).

    4 players × 2 rounds × 2 actions = 16 total actions.
    """
    rng = random.Random(42)
    while state.phase in (Phase.INITIAL_SETTLEMENT, Phase.INITIAL_ROAD):
        if state.phase == Phase.INITIAL_SETTLEMENT:
            legal = legal_initial_settlements(state)
            v = rng.choice(legal)
            apply_action(state, PlaceInitialSettlement(v))
        else:
            legal = legal_initial_roads(state)
            e = rng.choice(legal)
            apply_action(state, PlaceInitialRoad(e))


def give(state: GameState, player_id: int, cost: dict) -> None:
    for r, amt in cost.items():
        state.players[player_id].resources[r] = (
            state.players[player_id].resources.get(r, 0) + amt
        )


# ---------------------------------------------------------------------------
# Initial placement
# ---------------------------------------------------------------------------


class TestInitialPlacement:
    def test_placement_follows_snake_order(self, state):
        s = state.copy()
        order = s.initial_placement_order  # [0,1,2,3,3,2,1,0]
        rng = random.Random(7)
        for expected_player in order:
            assert s.current_player == expected_player
            legal = legal_initial_settlements(s)
            v = rng.choice(legal)
            apply_action(s, PlaceInitialSettlement(v))
            assert s.phase == Phase.INITIAL_ROAD
            legal_r = legal_initial_roads(s)
            e = rng.choice(legal_r)
            apply_action(s, PlaceInitialRoad(e))

    def test_transitions_to_pre_roll_after_completion(self, state):
        s = state.copy()
        run_initial_placement(s)
        assert s.phase == Phase.PRE_ROLL
        assert s.current_player == 0

    def test_second_round_grants_resources(self, state):
        s = state.copy()
        rng = random.Random(99)

        # First round — no resources
        for _ in range(4):
            v = rng.choice(legal_initial_settlements(s))
            apply_action(s, PlaceInitialSettlement(v))
            e = rng.choice(legal_initial_roads(s))
            apply_action(s, PlaceInitialRoad(e))

        # Second round — each player should receive resources
        total_before = sum(
            p.resource_count for p in s.players
        )
        for _ in range(4):
            v = rng.choice(legal_initial_settlements(s))
            apply_action(s, PlaceInitialSettlement(v))
            e = rng.choice(legal_initial_roads(s))
            apply_action(s, PlaceInitialRoad(e))

        total_after = sum(p.resource_count for p in s.players)
        assert total_after > total_before

    def test_turn_number_increments_after_placement(self, state):
        s = state.copy()
        run_initial_placement(s)
        assert s.turn_number == 1  # first normal turn started


# ---------------------------------------------------------------------------
# Roll
# ---------------------------------------------------------------------------


class TestRoll:
    def test_non_7_distributes_resources(self, state):
        s = state.copy()
        run_initial_placement(s)
        # Find a token value that matches a hex adjacent to some settlement
        board = s.board
        # Place a settlement manually near a hex with token 6
        token_hex = next(
            (hid for hid, tok in board.hex_tokens.items() if tok == 6), None
        )
        if token_hex is None:
            pytest.skip("No hex with token 6 on standard board")
        v = board.hex_vertices[token_hex][0]
        s.settlements[v] = 0   # give player 0 a settlement there

        before = s.players[0].resource_count
        apply_action(s, Roll(), rng=fixed_roll_rng(6))
        assert s.players[0].resource_count > before
        assert s.phase == Phase.POST_ROLL

    def test_roll_7_triggers_move_robber(self, state):
        s = state.copy()
        run_initial_placement(s)
        # Make sure no player has >7 cards so we skip straight to MOVE_ROBBER
        apply_action(s, Roll(), rng=fixed_roll_rng(7))
        assert s.phase == Phase.MOVE_ROBBER

    def test_roll_7_with_fat_hand_triggers_discard(self, state):
        s = state.copy()
        run_initial_placement(s)
        # Give player 1 a fat hand
        s.players[1].resources[Resource.BRICK] = 8
        apply_action(s, Roll(), rng=fixed_roll_rng(7))
        assert s.phase == Phase.DISCARD
        assert 1 in s.pending_discard_players

    def test_robber_blocks_resource(self, state):
        s = state.copy()
        run_initial_placement(s)
        board = s.board
        token_hex = next(hid for hid, tok in board.hex_tokens.items() if tok == 6)
        v = board.hex_vertices[token_hex][0]
        s.settlements[v] = 0
        s.robber_hex = token_hex   # robber blocks this hex

        before = s.players[0].resource_count
        apply_action(s, Roll(), rng=fixed_roll_rng(6))
        assert s.players[0].resource_count == before   # blocked


# ---------------------------------------------------------------------------
# Discard
# ---------------------------------------------------------------------------


class TestDiscard:
    def test_single_discard_advances_to_move_robber(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.players[0].resources[Resource.BRICK] = 8
        apply_action(s, Roll(), rng=fixed_roll_rng(7))
        assert s.phase == Phase.DISCARD
        assert current_actor(s) == 0
        apply_action(s, Discard({Resource.BRICK: 4}))
        assert s.phase == Phase.MOVE_ROBBER
        assert s.players[0].resources[Resource.BRICK] == 4

    def test_multiple_discards_processed_sequentially(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.players[0].resources[Resource.BRICK] = 8
        s.players[2].resources[Resource.GRAIN] = 10
        apply_action(s, Roll(), rng=fixed_roll_rng(7))
        assert len(s.pending_discard_players) == 2
        # Player 0 discards first
        apply_action(s, Discard({Resource.BRICK: 4}))
        assert s.phase == Phase.DISCARD
        assert current_actor(s) == 2
        # Player 2 discards
        apply_action(s, Discard({Resource.GRAIN: 5}))
        assert s.phase == Phase.MOVE_ROBBER


# ---------------------------------------------------------------------------
# Robber + steal
# ---------------------------------------------------------------------------


class TestRobberSteal:
    def test_move_robber_to_new_hex(self, state):
        s = state.copy()
        run_initial_placement(s)
        apply_action(s, Roll(), rng=fixed_roll_rng(7))
        old_hex = s.robber_hex
        new_hex = next(h for h in s.board.hex_coords if h != old_hex)
        apply_action(s, MoveRobber(new_hex), rng=fixed_roll_rng(7))
        assert s.robber_hex == new_hex

    def test_move_robber_skips_steal_when_no_targets(self, state):
        s = state.copy()
        run_initial_placement(s)
        apply_action(s, Roll(), rng=fixed_roll_rng(7))
        # Move to a hex with no adjacent opponent settlements
        empty_hex = next(
            hid for hid in s.board.hex_coords
            if hid != s.robber_hex
            and not any(
                s.settlements.get(vid) not in (None, s.current_player)
                or s.cities.get(vid) not in (None, s.current_player)
                for vid in s.board.hex_vertices[hid]
            )
        )
        apply_action(s, MoveRobber(empty_hex), rng=fixed_roll_rng(7))
        assert s.phase == Phase.POST_ROLL

    def test_steal_transfers_resource(self, state):
        s = state.copy()
        run_initial_placement(s)

        # Set up: robber on hex, opponent settlement adjacent with resources
        target_hex = next(h for h in s.board.hex_coords if h != s.robber_hex)
        vid = s.board.hex_vertices[target_hex][0]
        s.settlements[vid] = 1
        s.players[1].resources[Resource.BRICK] = 3
        s.robber_hex = target_hex
        s.phase = Phase.STEAL
        s.last_roll = 7   # simulate post-roll steal so _after_robber → POST_ROLL

        before_thief = s.players[0].resource_count
        before_victim = s.players[1].resource_count
        apply_action(s, Steal(1), rng=fixed_roll_rng(7))
        assert s.players[0].resource_count == before_thief + 1
        assert s.players[1].resource_count == before_victim - 1
        assert s.phase == Phase.POST_ROLL

    def test_pre_roll_knight_returns_to_pre_roll(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.players[0].dev_cards[DevCard.KNIGHT] = 1
        assert s.phase == Phase.PRE_ROLL
        assert s.last_roll is None  # not yet rolled

        apply_action(s, PlayKnight())
        assert s.phase == Phase.MOVE_ROBBER
        assert s.players[0].has_played_dev_this_turn

        new_hex = next(h for h in s.board.hex_coords if h != s.robber_hex)
        apply_action(s, MoveRobber(new_hex), rng=fixed_roll_rng(4))
        # Resolve steal phase if it was triggered (pass steal with None target)
        if s.phase == Phase.STEAL:
            apply_action(s, Steal(None), rng=fixed_roll_rng(4))
        # Knight before roll → must return to PRE_ROLL so player can still roll
        assert s.phase == Phase.PRE_ROLL


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


class TestBuilding:
    def _setup_post_roll(self, state):
        s = state.copy()
        run_initial_placement(s)
        apply_action(s, Roll(), rng=fixed_roll_rng(4))
        # Force POST_ROLL in case the roll triggered DISCARD or MOVE_ROBBER.
        # Also set last_roll so _after_robber returns to POST_ROLL, not PRE_ROLL.
        s.phase = Phase.POST_ROLL
        s.last_roll = 4
        return s

    def test_build_road(self, state):
        s = self._setup_post_roll(state)
        give(s, 0, BUILD_COSTS["road"])
        v0 = list(s.settlements.keys())[0] if s.settlements else 0
        # Give player 0 a settlement to anchor a road
        v0 = next(v for v, p in s.settlements.items() if p == 0)
        edge = s.board.vertex_edges[v0][0]
        if edge not in s.roads:
            apply_action(s, BuildRoad(edge))
            assert s.roads[edge] == 0
            assert s.players[0].resources[Resource.BRICK] == 0

    def test_build_settlement(self, state):
        s = self._setup_post_roll(state)
        give(s, 0, BUILD_COSTS["settlement"])
        # Find a vertex adjacent to an existing player 0 road, far from other buildings
        from catan_bot.engine.rules import legal_settlements
        legal = legal_settlements(s, 0)
        if not legal:
            pytest.skip("No legal settlement spots after initial placement")
        v = legal[0]
        before_count = s.settlements_on_board(0)
        apply_action(s, BuildSettlement(v))
        assert s.settlements_on_board(0) == before_count + 1

    def test_build_city(self, state):
        s = self._setup_post_roll(state)
        give(s, 0, BUILD_COSTS["city"])
        # Find player 0 settlement
        v = next((v for v, p in s.settlements.items() if p == 0), None)
        if v is None:
            pytest.skip("Player 0 has no settlements")
        apply_action(s, BuildCity(v))
        assert v not in s.settlements
        assert s.cities[v] == 0


# ---------------------------------------------------------------------------
# Development cards
# ---------------------------------------------------------------------------


class TestDevCards:
    def _setup_post_roll(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.phase = Phase.POST_ROLL
        s.last_roll = 4   # required so _after_robber returns to POST_ROLL
        return s

    def test_buy_dev_card_moves_to_new(self, state):
        s = self._setup_post_roll(state)
        give(s, 0, BUILD_COSTS["dev_card"])
        deck_before = s.dev_deck_remaining
        apply_action(s, BuyDevCard())
        assert s.dev_deck_remaining == deck_before - 1
        total_new = sum(s.players[0].dev_cards_new.values())
        assert total_new == 1

    def test_new_card_not_playable_same_turn(self, state):
        from catan_bot.engine.rules import can_play_dev
        s = self._setup_post_roll(state)
        give(s, 0, BUILD_COSTS["dev_card"])
        apply_action(s, BuyDevCard())
        # Whatever card was drawn is in dev_cards_new, not dev_cards
        for card in DevCard:
            if s.players[0].dev_cards_new.get(card, 0) > 0:
                assert not can_play_dev(s, 0, card)

    def test_new_card_becomes_playable_next_turn(self, state):
        from catan_bot.engine.rules import can_play_dev
        s = self._setup_post_roll(state)
        give(s, 0, BUILD_COSTS["dev_card"])
        apply_action(s, BuyDevCard())
        # End turn → next player's turn → back to player 0
        apply_action(s, EndTurn())
        apply_action(s, Roll(), rng=fixed_roll_rng(4))
        s.phase = Phase.POST_ROLL
        apply_action(s, EndTurn())   # player 1
        apply_action(s, Roll(), rng=fixed_roll_rng(4))
        s.phase = Phase.POST_ROLL
        apply_action(s, EndTurn())   # player 2
        apply_action(s, Roll(), rng=fixed_roll_rng(4))
        s.phase = Phase.POST_ROLL
        apply_action(s, EndTurn())   # player 3
        # Now it's player 0's turn again
        assert s.current_player == 0
        for card in DevCard:
            if s.players[0].dev_cards.get(card, 0) > 0:
                if card != DevCard.VICTORY_POINT:
                    assert can_play_dev(s, 0, card)

    def test_play_year_of_plenty(self, state):
        s = self._setup_post_roll(state)
        s.players[0].dev_cards[DevCard.YEAR_OF_PLENTY] = 1
        before = s.players[0].resources.get(Resource.ORE, 0)
        apply_action(s, PlayYearOfPlenty(Resource.ORE, Resource.GRAIN))
        assert s.players[0].resources[Resource.ORE] == before + 1
        assert s.players[0].resources[Resource.GRAIN] >= 1
        assert s.players[0].dev_cards[DevCard.YEAR_OF_PLENTY] == 0
        assert s.phase == Phase.POST_ROLL

    def test_play_monopoly(self, state):
        s = self._setup_post_roll(state)
        s.players[0].dev_cards[DevCard.MONOPOLY] = 1
        # Clear all players' brick to get a known baseline
        for pid in range(len(s.players)):
            s.players[pid].resources[Resource.BRICK] = 0
        s.players[1].resources[Resource.BRICK] = 3
        s.players[2].resources[Resource.BRICK] = 2
        apply_action(s, PlayMonopoly(Resource.BRICK))
        assert s.players[0].resources[Resource.BRICK] == 5
        assert s.players[1].resources[Resource.BRICK] == 0
        assert s.players[2].resources[Resource.BRICK] == 0
        assert s.phase == Phase.POST_ROLL

    def test_play_road_building_places_two_roads(self, state):
        s = self._setup_post_roll(state)
        s.players[0].dev_cards[DevCard.ROAD_BUILDING] = 1
        apply_action(s, PlayRoadBuilding())
        assert s.phase == Phase.ROAD_BUILDING
        assert s.road_building_roads_placed == 0

        # Place first free road
        from catan_bot.engine.rules import legal_roads
        roads = legal_roads(s, 0, free=True)
        assert roads
        apply_action(s, PlaceRoadBuildingRoad(roads[0]))
        assert s.road_building_roads_placed == 1
        assert s.roads[roads[0]] == 0

        # Place second free road
        roads2 = legal_roads(s, 0, free=True)
        apply_action(s, PlaceRoadBuildingRoad(roads2[0]))
        assert s.road_building_roads_placed == 2
        assert s.phase == Phase.POST_ROLL

    def test_road_building_no_cost(self, state):
        s = self._setup_post_roll(state)
        s.players[0].dev_cards[DevCard.ROAD_BUILDING] = 1
        # No road resources in hand
        assert s.players[0].resources.get(Resource.BRICK, 0) == 0
        apply_action(s, PlayRoadBuilding())
        from catan_bot.engine.rules import legal_roads
        roads = legal_roads(s, 0, free=True)
        if roads:
            apply_action(s, PlaceRoadBuildingRoad(roads[0]))
            # Resources unchanged
            assert s.players[0].resources.get(Resource.BRICK, 0) == 0

    def test_play_knight_updates_army(self, state):
        s = self._setup_post_roll(state)
        s.players[0].dev_cards[DevCard.KNIGHT] = 3
        for _ in range(3):
            # Allow playing another dev card each iteration
            s.players[0].has_played_dev_this_turn = False
            apply_action(s, PlayKnight())
            # After each knight, robber must be moved
            new_hex = next(h for h in s.board.hex_coords if h != s.robber_hex)
            apply_action(s, MoveRobber(new_hex), rng=fixed_roll_rng(4))
            if s.phase == Phase.STEAL:
                apply_action(s, Steal(None), rng=fixed_roll_rng(4))

        assert s.players[0].army_size == 3
        assert s.largest_army_player == 0


# ---------------------------------------------------------------------------
# Maritime trade
# ---------------------------------------------------------------------------


class TestMaritimeTrade:
    def test_4to1_bank_trade(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.phase = Phase.POST_ROLL
        s.players[0].resources[Resource.BRICK] = 4
        apply_action(s, MaritimeTrade(Resource.BRICK, 4, Resource.GRAIN))
        assert s.players[0].resources[Resource.BRICK] == 0
        assert s.players[0].resources[Resource.GRAIN] >= 1

    def test_2to1_port_trade(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.phase = Phase.POST_ROLL
        brick_v = next(
            vid for vid, res in s.board.vertex_ports.items()
            if res == Resource.BRICK
        )
        s.settlements[brick_v] = 0
        s.players[0].resources[Resource.BRICK] = 2
        apply_action(s, MaritimeTrade(Resource.BRICK, 2, Resource.ORE))
        assert s.players[0].resources[Resource.BRICK] == 0
        assert s.players[0].resources[Resource.ORE] >= 1


# ---------------------------------------------------------------------------
# End turn
# ---------------------------------------------------------------------------


class TestEndTurn:
    def test_end_turn_advances_player(self, state):
        s = state.copy()
        run_initial_placement(s)
        assert s.current_player == 0
        s.phase = Phase.POST_ROLL
        apply_action(s, EndTurn())
        assert s.current_player == 1
        assert s.phase == Phase.PRE_ROLL

    def test_end_turn_wraps_around(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.current_player = 3
        s.phase = Phase.POST_ROLL
        apply_action(s, EndTurn())
        assert s.current_player == 0

    def test_dev_cards_new_become_playable_on_next_turn(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.players[0].dev_cards_new[DevCard.KNIGHT] = 1
        s.phase = Phase.POST_ROLL
        apply_action(s, EndTurn())   # advances to player 1
        # Cycle back to player 0
        for _ in range(3):
            s.phase = Phase.POST_ROLL
            apply_action(s, EndTurn())
        assert s.current_player == 0
        assert s.players[0].dev_cards[DevCard.KNIGHT] == 1
        assert s.players[0].dev_cards_new[DevCard.KNIGHT] == 0

    def test_turn_number_increments(self, state):
        s = state.copy()
        run_initial_placement(s)
        t0 = s.turn_number
        s.phase = Phase.POST_ROLL
        apply_action(s, EndTurn())
        assert s.turn_number == t0 + 1


# ---------------------------------------------------------------------------
# Win condition
# ---------------------------------------------------------------------------


class TestWin:
    def test_game_over_when_10_vp(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.phase = Phase.POST_ROLL

        # Give player 0 nine settlements (bypassing piece limits for test)
        verts = [v for v in s.board.vertex_positions if v not in s.settlements][:9]
        for v in verts:
            s.settlements[v] = 0

        # One more settlement pushes to 10+ VP
        give(s, 0, BUILD_COSTS["settlement"])
        from catan_bot.engine.rules import legal_settlements
        legal = legal_settlements(s, 0)
        if legal:
            apply_action(s, BuildSettlement(legal[0]))
            assert s.phase == Phase.GAME_OVER
            assert s.winner == 0

    def test_no_end_turn_after_game_over(self, state):
        s = state.copy()
        run_initial_placement(s)
        s.phase = Phase.GAME_OVER
        # Applying EndTurn on a finished game should not change winner
        apply_action(s, EndTurn())
        assert s.phase == Phase.GAME_OVER
