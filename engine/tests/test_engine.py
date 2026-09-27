"""rules engine behaviour."""

from __future__ import annotations

import random
from collections import Counter

import pytest

from engine import GameEngine, IllegalActionError, choose_action, game_view
from engine.actions import (
    BuildRoad,
    BuildSettlement,
    BuyDevCard,
    CancelTrade,
    ConfirmTrade,
    Discard,
    EndTurn,
    MaritimeTrade,
    MoveRobber,
    PlayKnight,
    ProposeTrade,
    RespondTrade,
    RollDice,
)
from engine.board import standard_board, topology
from engine.models import DevCard, Resource, TurnPhase


def _setup_done(players: int = 2, seed: int = 0) -> GameEngine:
    """plays the setup phase with the first legal placement each time."""
    engine = GameEngine.new_game([f'p{i}' for i in range(1, players + 1)], seed=seed)
    while engine.state.phase in (TurnPhase.SETUP_SETTLEMENT, TurnPhase.SETUP_ROAD):
        pid = engine.state.current_player_id
        engine.apply(pid, engine.legal_actions(pid)[0])
    return engine


def _to_main(engine: GameEngine) -> None:
    """puts the current player straight into the main phase."""
    engine.state.phase = TurnPhase.MAIN


def _give(engine: GameEngine, pid: int, **cards: int) -> None:
    """adds resources to a hand, taking them from the bank."""
    for name, n in cards.items():
        r = Resource(name)
        engine.state.bank[r] -= n
        engine.player(pid).resources[r] += n


def test_standard_board_layout() -> None:
    board = standard_board(seed=7)
    counts = Counter(h.resource for h in board.hexes)
    assert counts[None] == 1
    assert counts[Resource.ORE] == counts[Resource.BRICK] == 3
    assert board.hexes[board.robber_hex_id].resource is None
    assert len(board.ports) == 9
    neighbors = topology().hex_neighbors
    for h in board.hexes:
        if h.number_token in (6, 8):
            assert all(
                board.hexes[n].number_token not in (6, 8) for n in neighbors[h.id]
            )


def test_board_is_reproducible_from_seed() -> None:
    assert standard_board(seed=3) == standard_board(seed=3)


def test_new_game_rejects_bad_player_counts() -> None:
    with pytest.raises(ValueError):
        GameEngine.new_game(['solo'])
    with pytest.raises(ValueError):
        GameEngine.new_game(['a', 'b', 'c', 'd', 'e'])


def test_setup_runs_in_snake_order_and_pays_second_settlement() -> None:
    engine = GameEngine.new_game(['a', 'b', 'c'], seed=1)
    order = []
    while engine.state.phase in (TurnPhase.SETUP_SETTLEMENT, TurnPhase.SETUP_ROAD):
        pid = engine.state.current_player_id
        if engine.state.phase == TurnPhase.SETUP_SETTLEMENT:
            order.append(pid)
        engine.apply(pid, engine.legal_actions(pid)[0])
    assert order == [1, 2, 3, 3, 2, 1]
    assert engine.state.phase == TurnPhase.ROLL
    assert engine.state.current_player_id == 1
    for p in engine.state.players:
        second = p.settlements[1]
        expected = sum(
            1
            for h in topology().node_hexes[second]
            if engine.state.board.hexes[h].resource is not None
        )
        assert p.card_count() == expected


def test_setup_road_must_touch_new_settlement() -> None:
    engine = GameEngine.new_game(['a', 'b'], seed=1)
    engine.apply(1, BuildSettlement(node=0))
    far = next(e for e in topology().edges if 0 not in e)
    with pytest.raises(IllegalActionError):
        engine.apply(1, BuildRoad(edge=far))


def test_distance_rule_blocks_adjacent_settlement() -> None:
    engine = GameEngine.new_game(['a', 'b'], seed=1)
    engine.apply(1, BuildSettlement(node=10))
    engine.apply(1, BuildRoad(edge=topology().node_edges[10][0]))
    neighbor = topology().node_neighbors[10][0]
    with pytest.raises(IllegalActionError):
        engine.apply(2, BuildSettlement(node=neighbor))


def test_only_actors_may_act() -> None:
    engine = _setup_done()
    with pytest.raises(IllegalActionError):
        engine.apply(2, RollDice())
    assert engine.legal_actions(2) == []


class _FixedDice(random.Random):
    """an rng whose dice always show the given faces."""

    def __init__(self, *faces: int) -> None:
        super().__init__(0)
        self.faces = list(faces)

    def randint(self, a: int, b: int) -> int:
        """returns the next fixed face, cycling."""
        self.faces.append(self.faces.pop(0))
        return self.faces[-1]


def test_rolling_seven_makes_big_hands_discard_then_robber_moves() -> None:
    engine = _setup_done()
    engine.rng = _FixedDice(3, 4)
    for p in engine.state.players:
        p.resources = {r: 0 for r in Resource}
    engine.state.bank = {r: 19 for r in Resource}
    _give(engine, 2, ore=5, grain=4)
    engine.apply(1, RollDice())
    assert engine.state.phase == TurnPhase.DISCARD
    assert engine.state.discards_owed == {2: 4}
    with pytest.raises(IllegalActionError):
        engine.apply(2, Discard(resources={Resource.ORE: 3}))
    engine.apply(2, Discard(resources={Resource.ORE: 4}))
    assert engine.player(2).card_count() == 5
    assert engine.state.phase == TurnPhase.MOVE_ROBBER
    move = engine.legal_actions(1)[0]
    assert isinstance(move, MoveRobber)
    engine.apply(1, move)
    assert engine.state.phase == TurnPhase.MAIN
    assert engine.state.board.robber_hex_id == move.hex_id


def test_robber_steals_one_card_from_victim() -> None:
    engine = _setup_done()
    engine.state.phase = TurnPhase.MOVE_ROBBER
    victim = engine.player(2)
    hex_id = topology().node_hexes[victim.settlements[0]][0]
    if hex_id == engine.state.board.robber_hex_id:
        hex_id = topology().node_hexes[victim.settlements[1]][0]
    before = victim.card_count() + engine.player(1).card_count()
    victim_cards = victim.card_count()
    engine.apply(1, MoveRobber(hex_id=hex_id, victim_id=2))
    assert victim.card_count() == victim_cards - 1
    assert victim.card_count() + engine.player(1).card_count() == before


def test_robber_needs_a_victim_when_one_is_available() -> None:
    engine = _setup_done()
    engine.state.phase = TurnPhase.MOVE_ROBBER
    hex_id = topology().node_hexes[engine.player(2).settlements[0]][0]
    if hex_id != engine.state.board.robber_hex_id:
        with pytest.raises(IllegalActionError):
            engine.apply(1, MoveRobber(hex_id=hex_id))


def test_longest_road_goes_to_first_to_five_and_holder_keeps_tie() -> None:
    engine = _setup_done()
    p1, p2 = engine.player(1), engine.player(2)
    p1.settlements, p2.settlements = [], []
    p1.roads, p2.roads = _path(0, 5), []
    engine._update_longest_road()
    assert engine.state.longest_road_player_id == 1
    assert engine.victory_points(1) == 2
    p2.roads = _path(40, 5)
    engine._update_longest_road()
    assert engine.state.longest_road_player_id == 1
    p2.roads = _path(40, 6)
    engine._update_longest_road()
    assert engine.state.longest_road_player_id == 2


def test_simultaneous_tie_leaves_longest_road_unclaimed() -> None:
    engine = _setup_done()
    p1, p2 = engine.player(1), engine.player(2)
    p1.settlements, p2.settlements = [], []
    p1.roads, p2.roads = _path(0, 5), _path(40, 5)
    engine._update_longest_road()
    assert engine.state.longest_road_player_id is None


def _path(start: int, length: int) -> list[tuple[int, int]]:
    """a simple path of `length` edges from `start` through the node graph."""
    topo = topology()
    path: list[tuple[int, int]] = []
    seen = {start}
    node = start
    while len(path) < length:
        nxt = next(n for n in topo.node_neighbors[node] if n not in seen)
        path.append((min(node, nxt), max(node, nxt)))
        seen.add(nxt)
        node = nxt
    return path


def test_longest_road_is_cut_by_opponent_settlement() -> None:
    engine = _setup_done()
    p1, p2 = engine.player(1), engine.player(2)
    p1.roads = _path(0, 6)
    p1.settlements, p1.cities, p2.settlements = [], [], []
    assert engine.longest_road_length(1) == 6
    middle = p1.roads[2][1] if p1.roads[2][1] in p1.roads[3] else p1.roads[2][0]
    p2.settlements = [middle]
    assert engine.longest_road_length(1) == 3


def test_new_dev_card_cannot_be_played_until_next_turn() -> None:
    engine = _setup_done()
    _to_main(engine)
    engine.state.dev_deck.append(DevCard.KNIGHT)
    _give(engine, 1, wool=1, grain=1, ore=1)
    engine.apply(1, BuyDevCard())
    assert engine.player(1).new_dev_cards == [DevCard.KNIGHT]
    assert PlayKnight() not in engine.legal_actions(1)
    with pytest.raises(IllegalActionError):
        engine.apply(1, PlayKnight())
    engine.apply(1, EndTurn())
    assert engine.player(1).dev_cards == [DevCard.KNIGHT]


def test_one_dev_card_per_turn_and_largest_army() -> None:
    engine = _setup_done()
    p1 = engine.player(1)
    p1.dev_cards = [DevCard.KNIGHT, DevCard.KNIGHT]
    p1.knights_played = 2
    engine.apply(1, PlayKnight())
    assert engine.state.largest_army_player_id == 1
    assert engine.state.phase == TurnPhase.MOVE_ROBBER
    engine.apply(1, engine.legal_actions(1)[0])
    assert engine.state.phase == TurnPhase.ROLL
    assert PlayKnight() not in engine.legal_actions(1)


def test_maritime_trade_uses_port_rate() -> None:
    engine = _setup_done()
    _to_main(engine)
    port = next(p for p in engine.state.board.ports if p.resource is not None)
    assert port.resource is not None
    p1 = engine.player(1)
    p1.settlements.append(port.nodes[0])
    p1.resources = {r: 0 for r in Resource}
    engine.state.bank = {r: 19 for r in Resource}
    _give(engine, 1, **{port.resource.value: 2})
    receive = next(r for r in Resource if r != port.resource)
    engine.apply(1, MaritimeTrade(give=port.resource, receive=receive))
    assert p1.resources[port.resource] == 0
    assert p1.resources[receive] == 1


def test_domestic_trade_flow() -> None:
    engine = _setup_done(players=3)
    _to_main(engine)
    for p in engine.state.players:
        p.resources = {r: 0 for r in Resource}
    engine.state.bank = {r: 19 for r in Resource}
    _give(engine, 1, ore=2)
    _give(engine, 3, wool=1)
    engine.apply(1, ProposeTrade(give={Resource.ORE: 2}, receive={Resource.WOOL: 1}))
    assert engine.actors() == [1, 2, 3]
    assert engine.legal_actions(2) == [RespondTrade(accept=False)]
    engine.apply(2, RespondTrade(accept=False))
    engine.apply(3, RespondTrade(accept=True))
    engine.apply(1, ConfirmTrade(partner_id=3))
    assert engine.player(1).resources[Resource.WOOL] == 1
    assert engine.player(3).resources[Resource.ORE] == 2
    assert engine.state.trade_offer is None


def test_trade_offer_closes_when_everyone_rejects() -> None:
    engine = _setup_done()
    _to_main(engine)
    _give(engine, 1, ore=1)
    engine.apply(1, ProposeTrade(give={Resource.ORE: 1}, receive={Resource.WOOL: 1}))
    engine.apply(2, RespondTrade(accept=False))
    assert engine.state.trade_offer is None
    assert engine.actors() == [1]


def test_proposer_can_cancel() -> None:
    engine = _setup_done()
    _to_main(engine)
    _give(engine, 1, ore=1)
    engine.apply(1, ProposeTrade(give={Resource.ORE: 1}, receive={Resource.WOOL: 1}))
    engine.apply(1, CancelTrade())
    assert engine.state.trade_offer is None


def test_points_reached_off_turn_win_at_start_of_own_turn() -> None:
    engine = _setup_done()
    _to_main(engine)
    engine.player(2).dev_cards = [DevCard.VICTORY_POINT] * 8
    engine.apply(1, EndTurn())
    assert engine.state.phase == TurnPhase.GAME_OVER
    assert engine.state.winner_id == 2
    with pytest.raises(IllegalActionError):
        engine.apply(2, RollDice())


def test_view_hides_other_hands() -> None:
    engine = _setup_done()
    engine.player(2).dev_cards = [DevCard.VICTORY_POINT]
    view = game_view(engine, 1)
    me, other = view.players
    assert me.resources is not None
    assert other.resources is None and other.dev_cards is None
    assert other.dev_card_count == 1
    assert other.victory_points == engine.victory_points(2, include_hidden=False)
    assert view.legal_actions == engine.legal_actions(1)


def test_random_bots_finish_a_game() -> None:
    engine = GameEngine.new_game(['a', 'b', 'c', 'd'], seed=5)
    rng = random.Random(5)
    for _ in range(50_000):
        if engine.state.phase == TurnPhase.GAME_OVER:
            break
        for pid in engine.actors():
            action = choose_action(engine, pid, rng)
            if action is not None:
                engine.apply(pid, action)
                break
    assert engine.state.winner_id is not None
    for r in Resource:
        held = sum(p.resources[r] for p in engine.state.players)
        assert held + engine.state.bank[r] == 19
