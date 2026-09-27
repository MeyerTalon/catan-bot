"""the rules engine: validates and applies actions to a `GameState`.

several players can be asked to act at once (discarding after a 7, answering a
trade offer), so every call names the acting player. randomness (dice, the
development deck, stolen cards) comes from an injectable `random.Random`.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from typing import Dict, List, Set

from .actions import (
    Action,
    BuildCity,
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
    PlayMonopoly,
    PlayRoadBuilding,
    PlayYearOfPlenty,
    ProposeTrade,
    RespondTrade,
    RollDice,
)
from .board import Edge, edge_key, standard_board, topology
from .models import (
    DevCard,
    GameState,
    LogEntry,
    Player,
    Resource,
    TradeOffer,
    TurnPhase,
    empty_hand,
)

Cost = Dict[Resource, int]

ROAD_COST: Cost = {Resource.BRICK: 1, Resource.LUMBER: 1}
SETTLEMENT_COST: Cost = {
    Resource.BRICK: 1,
    Resource.LUMBER: 1,
    Resource.WOOL: 1,
    Resource.GRAIN: 1,
}
CITY_COST: Cost = {Resource.GRAIN: 2, Resource.ORE: 3}
DEV_CARD_COST: Cost = {Resource.WOOL: 1, Resource.GRAIN: 1, Resource.ORE: 1}

MAX_ROADS = 15
MAX_SETTLEMENTS = 5
MAX_CITIES = 4
BANK_SIZE = 19
POINTS_TO_WIN = 10
MIN_LONGEST_ROAD = 5
MIN_LARGEST_ARMY = 3
MAX_TRADE_PROPOSALS_PER_TURN = 3
MAX_LOG_ENTRIES = 200
MIN_PLAYERS = 2
MAX_PLAYERS = 4

DEV_DECK: List[DevCard] = (
    [DevCard.KNIGHT] * 14
    + [DevCard.VICTORY_POINT] * 5
    + [DevCard.ROAD_BUILDING] * 2
    + [DevCard.YEAR_OF_PLENTY] * 2
    + [DevCard.MONOPOLY] * 2
)

PLAYABLE_BEFORE_ROLL = {DevCard.KNIGHT}


class IllegalActionError(Exception):
    """raised when an action is not legal in the current state."""


def format_cards(cards: Cost) -> str:
    """renders a resource count map as text, e.g. '2 ore, 1 grain'."""
    parts = [f'{n} {r.value}' for r, n in cards.items() if n > 0]
    return ', '.join(parts) or 'nothing'


def _hand_subsets(hand: Cost, size: int) -> Iterator[Cost]:
    """yields every distinct way to pick `size` cards from a hand.

    Args:
        hand: resource counts to choose from.
        size: number of cards to pick.
    """
    kinds = [r for r in Resource if hand.get(r, 0) > 0]

    def _pick(i: int, left: int, chosen: Cost) -> Iterator[Cost]:
        """chooses counts for kinds[i:] summing to `left`."""
        if left == 0:
            yield dict(chosen)
            return
        if i == len(kinds):
            return
        kind = kinds[i]
        for n in range(min(left, hand[kind]), -1, -1):
            if n:
                chosen[kind] = n
            yield from _pick(i + 1, left - n, chosen)
            chosen.pop(kind, None)

    yield from _pick(0, size, {})


class GameEngine:
    """wraps a `GameState` and enforces the rules that move it forward."""

    def __init__(self, state: GameState, rng: random.Random | None = None) -> None:
        """starts from an existing state, e.g. one loaded from the database.

        Args:
            state: the game to drive; mutated in place by `apply`.
            rng: source of dice rolls and stolen cards; a fresh one when None.
        """
        self.state = state
        self.rng = rng or random.Random()

    @classmethod
    def new_game(cls, player_names: List[str], seed: int | None = None) -> GameEngine:
        """creates a fresh game in the setup phase.

        Args:
            player_names: seat order; ids are assigned from 1 in this order.
            seed: rng seed for the board, the development deck, and later dice.

        Raises:
            ValueError: if there are not 2-4 players.
        """
        if not MIN_PLAYERS <= len(player_names) <= MAX_PLAYERS:
            raise ValueError(f'catan needs {MIN_PLAYERS}-{MAX_PLAYERS} players.')
        rng = random.Random(seed)
        players = [Player(id=i, name=n) for i, n in enumerate(player_names, start=1)]
        deck = list(DEV_DECK)
        rng.shuffle(deck)
        state = GameState(
            players=players,
            board=standard_board(rng.randrange(2**32)),
            current_player_id=1,
            bank={r: BANK_SIZE for r in Resource},
            dev_deck=deck,
        )
        engine = cls(state, rng)
        engine._log(None, f'{players[0].name} places first.')
        return engine

    # ----- lookups -----

    def player(self, player_id: int) -> Player:
        """returns the player with this id.

        Raises:
            IllegalActionError: if no such player is seated.
        """
        for p in self.state.players:
            if p.id == player_id:
                return p
        raise IllegalActionError(f'no player {player_id}.')

    @property
    def current(self) -> Player:
        """the player whose turn it is."""
        return self.player(self.state.current_player_id)

    def _setup_order(self) -> List[int]:
        """seat ids in snake order: forward for round one, back for round two."""
        ids = [p.id for p in self.state.players]
        return ids + ids[::-1]

    def _building_owner(self, node: int) -> int | None:
        """id of the player with a settlement or city on a node, if any."""
        for p in self.state.players:
            if node in p.settlements or node in p.cities:
                return p.id
        return None

    def _road_owner(self, edge: Edge) -> int | None:
        """id of the player with a road on an edge, if any."""
        for p in self.state.players:
            if edge in p.roads:
                return p.id
        return None

    def victory_points(self, player_id: int, include_hidden: bool = True) -> int:
        """scores a player.

        Args:
            player_id: whose points to count.
            include_hidden: count victory point cards, which only their owner sees.
        """
        p = self.player(player_id)
        points = len(p.settlements) + 2 * len(p.cities)
        if self.state.longest_road_player_id == player_id:
            points += 2
        if self.state.largest_army_player_id == player_id:
            points += 2
        if include_hidden:
            points += (p.dev_cards + p.new_dev_cards).count(DevCard.VICTORY_POINT)
        return points

    def trade_ratio(self, player_id: int, resource: Resource) -> int:
        """best bank rate a player gets for a resource: 4, 3 (any port) or 2."""
        p = self.player(player_id)
        owned = set(p.settlements) | set(p.cities)
        ratio = 4
        for port in self.state.board.ports:
            if owned & set(port.nodes):
                if port.resource == resource:
                    return 2
                if port.resource is None:
                    ratio = 3
        return ratio

    def longest_road_length(self, player_id: int) -> int:
        """length of a player's longest continuous road.

        a road cannot continue through a node another player has built on.
        """
        p = self.player(player_id)
        adjacency: Dict[int, List[Edge]] = {}
        for edge in p.roads:
            for node in edge:
                adjacency.setdefault(node, []).append(edge)
        blocked = {
            n for n in adjacency if self._building_owner(n) not in (None, player_id)
        }

        def _walk(node: int, used: Set[Edge], start: bool) -> int:
            """longest extension from `node` without reusing an edge."""
            if not start and node in blocked:
                return 0
            best = 0
            for edge in adjacency.get(node, []):
                if edge in used:
                    continue
                nxt = edge[1] if edge[0] == node else edge[0]
                used.add(edge)
                best = max(best, 1 + _walk(nxt, used, False))
                used.discard(edge)
            return best

        return max((_walk(n, set(), True) for n in adjacency), default=0)

    def actors(self) -> List[int]:
        """ids of the players the game is waiting on right now."""
        state = self.state
        if state.phase == TurnPhase.GAME_OVER:
            return []
        if state.phase == TurnPhase.DISCARD:
            return sorted(state.discards_owed)
        if state.trade_offer is not None:
            responded = set(state.trade_offer.accepted) | set(
                state.trade_offer.rejected
            )
            waiting = [
                p.id
                for p in state.players
                if p.id != state.trade_offer.proposer_id and p.id not in responded
            ]
            return [state.trade_offer.proposer_id, *waiting]
        return [state.current_player_id]

    # ----- placement rules -----

    def _settlement_spot_free(self, node: int) -> bool:
        """whether a node and every neighbour are unbuilt (the distance rule)."""
        nodes = [node, *topology().node_neighbors[node]]
        return all(self._building_owner(n) is None for n in nodes)

    def _road_connects(self, player_id: int, edge: Edge) -> bool:
        """whether an edge touches the player's building or continues their road."""
        p = self.player(player_id)
        for node in edge:
            owner = self._building_owner(node)
            if owner == player_id:
                return True
            if owner is not None:
                continue
            if any(e in p.roads for e in topology().node_edges[node] if e != edge):
                return True
        return False

    def _legal_road_edges(self, player_id: int) -> List[Edge]:
        """edges where the player may build a road in normal play."""
        if len(self.player(player_id).roads) >= MAX_ROADS:
            return []
        return [
            e
            for e in topology().edges
            if self._road_owner(e) is None and self._road_connects(player_id, e)
        ]

    def _legal_settlement_nodes(self, player_id: int, setup: bool) -> List[int]:
        """nodes where the player may build a settlement.

        Args:
            player_id: the builder.
            setup: during setup no road connection is needed.
        """
        p = self.player(player_id)
        if len(p.settlements) >= MAX_SETTLEMENTS:
            return []
        road_nodes = {n for e in p.roads for n in e}
        return [
            n
            for n in range(len(topology().node_positions))
            if self._settlement_spot_free(n) and (setup or n in road_nodes)
        ]

    def _setup_road_edges(self) -> List[Edge]:
        """free edges touching the settlement just placed in setup."""
        node = self.state.last_settlement_node
        if node is None:
            return []
        return [e for e in topology().node_edges[node] if self._road_owner(e) is None]

    def _robber_victims(self, hex_id: int) -> List[int]:
        """players with cards and a building next to a hex, other than the mover."""
        nodes = topology().hex_nodes[hex_id]
        return sorted(
            {
                owner
                for n in nodes
                if (owner := self._building_owner(n)) is not None
                and owner != self.state.current_player_id
                and self.player(owner).card_count() > 0
            }
        )

    # ----- resources -----

    @staticmethod
    def _can_afford(p: Player, cost: Cost) -> bool:
        """whether a hand covers a cost."""
        return all(p.resources.get(r, 0) >= n for r, n in cost.items())

    def _pay(self, p: Player, cost: Cost) -> None:
        """moves a cost from a player's hand to the bank."""
        for r, n in cost.items():
            p.resources[r] -= n
            self.state.bank[r] += n

    def _take_from_bank(self, p: Player, cards: Cost) -> None:
        """moves cards from the bank to a player's hand."""
        for r, n in cards.items():
            self.state.bank[r] -= n
            p.resources[r] = p.resources.get(r, 0) + n

    def _require_affordable(self, p: Player, cost: Cost, what: str) -> None:
        """raises unless a player can pay for something.

        Raises:
            IllegalActionError: if the hand does not cover the cost.
        """
        if not self._can_afford(p, cost):
            raise IllegalActionError(f'Not enough resources for {what}.')

    # ----- legal actions -----

    def legal_actions(self, player_id: int) -> List[Action]:
        """lists every action a player may take right now.

        a domestic trade may offer any bundle; only one-for-one offers are
        listed here, which keeps the list finite for bots.
        """
        state = self.state
        if player_id not in self.actors():
            return []
        p = self.player(player_id)
        phase = state.phase

        if phase == TurnPhase.SETUP_SETTLEMENT:
            return [
                BuildSettlement(node=n)
                for n in self._legal_settlement_nodes(player_id, setup=True)
            ]
        if phase == TurnPhase.SETUP_ROAD:
            return [BuildRoad(edge=e) for e in self._setup_road_edges()]
        if phase == TurnPhase.DISCARD:
            owed = state.discards_owed[player_id]
            return [Discard(resources=c) for c in _hand_subsets(p.resources, owed)]
        if phase == TurnPhase.MOVE_ROBBER:
            return self._robber_actions()
        if phase == TurnPhase.ROAD_BUILDING:
            return [BuildRoad(edge=e) for e in self._legal_road_edges(player_id)]

        if state.trade_offer is not None:
            offer = state.trade_offer
            if player_id == offer.proposer_id:
                return [
                    *(ConfirmTrade(partner_id=pid) for pid in offer.accepted),
                    CancelTrade(),
                ]
            responses: List[Action] = [RespondTrade(accept=False)]
            if self._can_afford(p, offer.receive):
                responses.insert(0, RespondTrade(accept=True))
            return responses

        actions: List[Action] = []
        if phase == TurnPhase.ROLL:
            actions.append(RollDice())
        else:
            actions.extend(self._main_actions(p))
        if not state.dev_card_played:
            actions.extend(self._dev_card_actions(p, phase))
        return actions

    def _robber_actions(self) -> List[Action]:
        """every robber move, one per (hex, victim) pair."""
        actions: List[Action] = []
        for tile in self.state.board.hexes:
            if tile.id == self.state.board.robber_hex_id:
                continue
            victims = self._robber_victims(tile.id)
            if victims:
                actions.extend(MoveRobber(hex_id=tile.id, victim_id=v) for v in victims)
            else:
                actions.append(MoveRobber(hex_id=tile.id))
        return actions

    def _main_actions(self, p: Player) -> List[Action]:
        """building, buying, trading, and ending the turn after the roll."""
        state = self.state
        actions: List[Action] = []
        if self._can_afford(p, ROAD_COST):
            actions.extend(BuildRoad(edge=e) for e in self._legal_road_edges(p.id))
        if self._can_afford(p, SETTLEMENT_COST):
            actions.extend(
                BuildSettlement(node=n)
                for n in self._legal_settlement_nodes(p.id, setup=False)
            )
        if self._can_afford(p, CITY_COST) and len(p.cities) < MAX_CITIES:
            actions.extend(BuildCity(node=n) for n in p.settlements)
        if self._can_afford(p, DEV_CARD_COST) and state.dev_deck:
            actions.append(BuyDevCard())
        for give in Resource:
            if p.resources[give] < self.trade_ratio(p.id, give):
                continue
            actions.extend(
                MaritimeTrade(give=give, receive=r)
                for r in Resource
                if r != give and state.bank[r] > 0
            )
        if state.trades_proposed < MAX_TRADE_PROPOSALS_PER_TURN:
            actions.extend(
                ProposeTrade(give={give: 1}, receive={r: 1})
                for give in Resource
                if p.resources[give] > 0
                for r in Resource
                if r != give
            )
        actions.append(EndTurn())
        return actions

    def _dev_card_actions(self, p: Player, phase: TurnPhase) -> List[Action]:
        """development cards the player may play in this phase."""
        actions: List[Action] = []
        held = set(p.dev_cards)
        if DevCard.KNIGHT in held:
            actions.append(PlayKnight())
        if phase != TurnPhase.MAIN:
            return actions
        if DevCard.ROAD_BUILDING in held:
            actions.append(PlayRoadBuilding())
        if DevCard.YEAR_OF_PLENTY in held:
            bank = self.state.bank
            actions.extend(
                PlayYearOfPlenty(resources=(a, b))
                for i, a in enumerate(Resource)
                for b in list(Resource)[i:]
                if bank[a] >= (2 if a == b else 1) and bank[b] >= 1
            )
        if DevCard.MONOPOLY in held:
            actions.extend(PlayMonopoly(resource=r) for r in Resource)
        return actions

    # ----- applying actions -----

    def apply(self, player_id: int, action: Action) -> GameState:
        """applies one player's action and returns the resulting state.

        Args:
            player_id: the acting player.
            action: what they do.

        Raises:
            IllegalActionError: if the action is not legal in the current state.
        """
        state = self.state
        if state.phase == TurnPhase.GAME_OVER:
            raise IllegalActionError('The game is over.')
        if player_id not in self.actors():
            raise IllegalActionError('It is not your move.')
        p = self.player(player_id)

        if state.phase == TurnPhase.DISCARD:
            if not isinstance(action, Discard):
                raise IllegalActionError('Discard half your cards first.')
            self._discard(p, action)
        elif state.trade_offer is not None:
            self._apply_trade_step(p, action)
        elif state.phase in (TurnPhase.SETUP_SETTLEMENT, TurnPhase.SETUP_ROAD):
            self._apply_setup(p, action)
        elif state.phase == TurnPhase.MOVE_ROBBER:
            if not isinstance(action, MoveRobber):
                raise IllegalActionError('Move the robber first.')
            self._move_robber(p, action)
        elif state.phase == TurnPhase.ROAD_BUILDING:
            if not isinstance(action, BuildRoad):
                raise IllegalActionError('Place your free roads first.')
            self._build_road(p, action.edge, free=True)
            state.free_roads -= 1
            self._finish_road_building_if_done(p)
        else:
            self._apply_turn_action(p, action)

        self._check_winner()
        return state

    def _apply_setup(self, p: Player, action: Action) -> None:
        """places a free settlement, then a road touching it, in snake order."""
        state = self.state
        if state.phase == TurnPhase.SETUP_SETTLEMENT:
            if not isinstance(action, BuildSettlement):
                raise IllegalActionError('Place a settlement.')
            if action.node not in self._legal_settlement_nodes(p.id, setup=True):
                raise IllegalActionError('You cannot build a settlement there.')
            p.settlements.append(action.node)
            state.last_settlement_node = action.node
            state.phase = TurnPhase.SETUP_ROAD
            if state.setup_step >= len(state.players):
                self._grant_starting_resources(p, action.node)
            else:
                self._log(p.id, 'placed a settlement.')
            return

        if not isinstance(action, BuildRoad):
            raise IllegalActionError('Place a road next to your new settlement.')
        edge = edge_key(*action.edge)
        if edge not in self._setup_road_edges():
            raise IllegalActionError('The road must touch your new settlement.')
        p.roads.append(edge)
        self._log(p.id, 'placed a road.')
        state.setup_step += 1
        state.last_settlement_node = None
        order = self._setup_order()
        if state.setup_step >= len(order):
            state.current_player_id = order[0]
            state.phase = TurnPhase.ROLL
            self._log(None, 'Setup complete. The game begins.')
        else:
            state.current_player_id = order[state.setup_step]
            state.phase = TurnPhase.SETUP_SETTLEMENT

    def _grant_starting_resources(self, p: Player, node: int) -> None:
        """hands out one card per resource hex touching the second settlement."""
        gained = empty_hand()
        for hex_id in topology().node_hexes[node]:
            resource = self.state.board.hexes[hex_id].resource
            if resource is not None and self.state.bank[resource] > 0:
                gained[resource] += 1
        self._take_from_bank(p, gained)
        self._log(p.id, f'placed a settlement and took {format_cards(gained)}.')

    def _apply_turn_action(self, p: Player, action: Action) -> None:
        """handles the current player's roll or main-phase action."""
        state = self.state
        if isinstance(action, PlayKnight):
            self._play_knight(p)
            return
        if state.phase == TurnPhase.ROLL:
            if not isinstance(action, RollDice):
                raise IllegalActionError('Roll the dice first.')
            self._roll(p)
            return
        if isinstance(action, RollDice):
            raise IllegalActionError('You already rolled this turn.')
        if isinstance(action, BuildRoad):
            self._require_affordable(p, ROAD_COST, 'a road')
            self._build_road(p, action.edge, free=False)
        elif isinstance(action, BuildSettlement):
            self._build_settlement(p, action.node)
        elif isinstance(action, BuildCity):
            self._build_city(p, action.node)
        elif isinstance(action, BuyDevCard):
            self._buy_dev_card(p)
        elif isinstance(action, PlayRoadBuilding):
            self._play_road_building(p)
        elif isinstance(action, PlayYearOfPlenty):
            self._play_year_of_plenty(p, action)
        elif isinstance(action, PlayMonopoly):
            self._play_monopoly(p, action.resource)
        elif isinstance(action, MaritimeTrade):
            self._maritime_trade(p, action)
        elif isinstance(action, ProposeTrade):
            self._propose_trade(p, action)
        elif isinstance(action, EndTurn):
            self._end_turn(p)
        else:
            raise IllegalActionError('That action is not available now.')

    def _roll(self, p: Player) -> None:
        """rolls the dice, then produces resources or starts the robber."""
        state = self.state
        dice = (self.rng.randint(1, 6), self.rng.randint(1, 6))
        state.dice = dice
        total = sum(dice)
        self._log(p.id, f'rolled {total}.')
        if total != 7:
            self._produce(total)
            state.phase = TurnPhase.MAIN
            return
        state.discards_owed = {
            q.id: q.card_count() // 2 for q in state.players if q.card_count() > 7
        }
        state.robber_return_phase = TurnPhase.MAIN
        if state.discards_owed:
            state.phase = TurnPhase.DISCARD
            names = ', '.join(self.player(i).name for i in state.discards_owed)
            self._log(None, f'{names} must discard half their cards.')
        else:
            state.phase = TurnPhase.MOVE_ROBBER

    def _produce(self, total: int) -> None:
        """pays out every hex showing `total`, respecting the bank's supply.

        when the bank cannot cover every claim on a resource, nobody gets it,
        unless only one player is owed that resource (they get what is left).
        """
        state = self.state
        topo = topology()
        owed: Dict[int, Cost] = {p.id: empty_hand() for p in state.players}
        for tile in state.board.hexes:
            if (
                tile.number_token != total
                or tile.id == state.board.robber_hex_id
                or tile.resource is None
            ):
                continue
            for node in topo.hex_nodes[tile.id]:
                for p in state.players:
                    if node in p.settlements:
                        owed[p.id][tile.resource] += 1
                    elif node in p.cities:
                        owed[p.id][tile.resource] += 2

        for resource in Resource:
            claims = {pid: c[resource] for pid, c in owed.items() if c[resource] > 0}
            if sum(claims.values()) <= state.bank[resource]:
                continue
            if len(claims) == 1:
                (only,) = claims
                owed[only][resource] = state.bank[resource]
            else:
                for pid in claims:
                    owed[pid][resource] = 0
                self._log(None, f'The bank is short of {resource.value}.')

        for pid, cards in owed.items():
            if sum(cards.values()):
                self._take_from_bank(self.player(pid), cards)
                self._log(pid, f'received {format_cards(cards)}.')

    def _discard(self, p: Player, action: Discard) -> None:
        """returns the owed half of a hand to the bank."""
        state = self.state
        cards = {r: n for r, n in action.resources.items() if n}
        owed = state.discards_owed[p.id]
        if any(n < 0 for n in cards.values()) or sum(cards.values()) != owed:
            raise IllegalActionError(f'Discard exactly {owed} cards.')
        self._require_affordable(p, cards, 'that discard')
        self._pay(p, cards)
        del state.discards_owed[p.id]
        self._log(p.id, f'discarded {format_cards(cards)}.')
        if not state.discards_owed:
            state.phase = TurnPhase.MOVE_ROBBER

    def _move_robber(self, p: Player, action: MoveRobber) -> None:
        """moves the robber and steals a random card from the chosen victim."""
        state = self.state
        if not 0 <= action.hex_id < len(state.board.hexes):
            raise IllegalActionError('No such hex.')
        if action.hex_id == state.board.robber_hex_id:
            raise IllegalActionError('The robber must move to a different hex.')
        victims = self._robber_victims(action.hex_id)
        if victims and action.victim_id not in victims:
            raise IllegalActionError('Choose a player next to that hex to rob.')
        if not victims and action.victim_id is not None:
            raise IllegalActionError('Nobody there can be robbed.')

        state.board.robber_hex_id = action.hex_id
        state.phase = state.robber_return_phase or TurnPhase.MAIN
        state.robber_return_phase = None
        if action.victim_id is None:
            self._log(p.id, 'moved the robber.')
            return
        victim = self.player(action.victim_id)
        pool = [r for r in Resource for _ in range(victim.resources[r])]
        stolen = self.rng.choice(pool)
        victim.resources[stolen] -= 1
        p.resources[stolen] += 1
        self._log(p.id, f'moved the robber and stole a card from {victim.name}.')

    def _build_road(self, p: Player, edge: Edge, free: bool) -> None:
        """places a road, paying for it unless free."""
        edge = edge_key(*edge)
        if edge not in self._legal_road_edges(p.id):
            raise IllegalActionError('You cannot build a road there.')
        if not free:
            self._pay(p, ROAD_COST)
        p.roads.append(edge)
        self._log(p.id, 'built a road.')
        self._update_longest_road()

    def _build_settlement(self, p: Player, node: int) -> None:
        """builds a settlement on a free node reached by the player's road."""
        self._require_affordable(p, SETTLEMENT_COST, 'a settlement')
        if node not in self._legal_settlement_nodes(p.id, setup=False):
            raise IllegalActionError('You cannot build a settlement there.')
        self._pay(p, SETTLEMENT_COST)
        p.settlements.append(node)
        self._log(p.id, 'built a settlement.')
        # a settlement can cut an opponent's road in two
        self._update_longest_road()

    def _build_city(self, p: Player, node: int) -> None:
        """upgrades one of the player's settlements."""
        self._require_affordable(p, CITY_COST, 'a city')
        if node not in p.settlements:
            raise IllegalActionError('Cities replace one of your settlements.')
        if len(p.cities) >= MAX_CITIES:
            raise IllegalActionError('You have no cities left.')
        self._pay(p, CITY_COST)
        p.settlements.remove(node)
        p.cities.append(node)
        self._log(p.id, 'built a city.')

    def _buy_dev_card(self, p: Player) -> None:
        """draws the top development card; it is playable from next turn."""
        self._require_affordable(p, DEV_CARD_COST, 'a development card')
        if not self.state.dev_deck:
            raise IllegalActionError('No development cards are left.')
        self._pay(p, DEV_CARD_COST)
        p.new_dev_cards.append(self.state.dev_deck.pop())
        self._log(p.id, 'bought a development card.')

    def _take_dev_card(self, p: Player, card: DevCard) -> None:
        """removes a card being played, enforcing one card per turn.

        Raises:
            IllegalActionError: if a card was already played this turn or the
                player holds no playable card of that kind.
        """
        if self.state.dev_card_played:
            raise IllegalActionError('You already played a development card this turn.')
        if card not in p.dev_cards:
            raise IllegalActionError(
                'You have no playable card of that kind (new cards wait a turn).'
            )
        p.dev_cards.remove(card)
        self.state.dev_card_played = True

    def _play_knight(self, p: Player) -> None:
        """plays a knight, before or after the roll."""
        state = self.state
        if state.phase not in (TurnPhase.ROLL, TurnPhase.MAIN):
            raise IllegalActionError('You cannot play a knight now.')
        self._take_dev_card(p, DevCard.KNIGHT)
        p.knights_played += 1
        self._log(p.id, 'played a knight.')
        holder = state.largest_army_player_id
        best = self.player(holder).knights_played if holder is not None else 0
        if p.knights_played >= MIN_LARGEST_ARMY and p.knights_played > best:
            if holder != p.id:
                self._log(p.id, 'took largest army.')
            state.largest_army_player_id = p.id
        state.robber_return_phase = state.phase
        state.phase = TurnPhase.MOVE_ROBBER

    def _play_road_building(self, p: Player) -> None:
        """plays road building: up to two free roads next."""
        self._take_dev_card(p, DevCard.ROAD_BUILDING)
        self._log(p.id, 'played road building.')
        self.state.free_roads = min(2, MAX_ROADS - len(p.roads))
        self.state.phase = TurnPhase.ROAD_BUILDING
        self._finish_road_building_if_done(p)

    def _finish_road_building_if_done(self, p: Player) -> None:
        """returns to the main phase once no free road is left or placeable."""
        if self.state.free_roads <= 0 or not self._legal_road_edges(p.id):
            self.state.free_roads = 0
            self.state.phase = TurnPhase.MAIN

    def _play_year_of_plenty(self, p: Player, action: PlayYearOfPlenty) -> None:
        """plays year of plenty: two resources from the bank."""
        wanted = empty_hand()
        for r in action.resources:
            wanted[r] += 1
        if any(self.state.bank[r] < n for r, n in wanted.items()):
            raise IllegalActionError('The bank does not have those resources.')
        self._take_dev_card(p, DevCard.YEAR_OF_PLENTY)
        self._take_from_bank(p, wanted)
        self._log(p.id, f'played year of plenty for {format_cards(wanted)}.')

    def _play_monopoly(self, p: Player, resource: Resource) -> None:
        """plays monopoly: collects one resource from every other player."""
        self._take_dev_card(p, DevCard.MONOPOLY)
        taken = 0
        for other in self.state.players:
            if other.id != p.id:
                taken += other.resources[resource]
                other.resources[resource] = 0
        p.resources[resource] += taken
        self._log(p.id, f'played monopoly and took {taken} {resource.value}.')

    def _maritime_trade(self, p: Player, action: MaritimeTrade) -> None:
        """trades with the bank at the player's best rate."""
        if action.give == action.receive:
            raise IllegalActionError('Trade for a different resource.')
        ratio = self.trade_ratio(p.id, action.give)
        self._require_affordable(p, {action.give: ratio}, 'that trade')
        if self.state.bank[action.receive] < 1:
            raise IllegalActionError(f'The bank has no {action.receive.value}.')
        self._pay(p, {action.give: ratio})
        self._take_from_bank(p, {action.receive: 1})
        self._log(
            p.id,
            f'traded {ratio} {action.give.value} with the bank for 1 '
            f'{action.receive.value}.',
        )

    def _propose_trade(self, p: Player, action: ProposeTrade) -> None:
        """opens a trade offer to every other player."""
        state = self.state
        give = {r: n for r, n in action.give.items() if n}
        receive = {r: n for r, n in action.receive.items() if n}
        if state.trades_proposed >= MAX_TRADE_PROPOSALS_PER_TURN:
            raise IllegalActionError(
                f'At most {MAX_TRADE_PROPOSALS_PER_TURN} trade offers per turn.'
            )
        if not give or not receive:
            raise IllegalActionError('A trade must give and receive something.')
        if any(n < 0 for n in [*give.values(), *receive.values()]):
            raise IllegalActionError('Trade amounts must be positive.')
        if set(give) & set(receive):
            raise IllegalActionError('Do not give and ask for the same resource.')
        self._require_affordable(p, give, 'that offer')
        state.trades_proposed += 1
        state.trade_offer = TradeOffer(proposer_id=p.id, give=give, receive=receive)
        self._log(p.id, f'offered {format_cards(give)} for {format_cards(receive)}.')

    def _apply_trade_step(self, p: Player, action: Action) -> None:
        """handles responses to, and the conclusion of, an open trade offer."""
        state = self.state
        offer = state.trade_offer
        assert offer is not None
        if p.id == offer.proposer_id:
            if isinstance(action, CancelTrade):
                state.trade_offer = None
                self._log(p.id, 'withdrew the trade offer.')
            elif isinstance(action, ConfirmTrade):
                self._confirm_trade(p, offer, action.partner_id)
            else:
                raise IllegalActionError('Confirm or cancel your trade offer first.')
            return

        if not isinstance(action, RespondTrade):
            raise IllegalActionError('Accept or reject the trade offer.')
        if action.accept:
            self._require_affordable(p, offer.receive, 'that trade')
            offer.accepted.append(p.id)
            self._log(p.id, 'accepted the offer.')
        else:
            offer.rejected.append(p.id)
            self._log(p.id, 'rejected the offer.')
        if len(offer.rejected) == len(state.players) - 1:
            state.trade_offer = None
            self._log(None, 'Nobody accepted the trade.')

    def _confirm_trade(self, p: Player, offer: TradeOffer, partner_id: int) -> None:
        """swaps cards between the proposer and one accepting player."""
        if partner_id not in offer.accepted:
            raise IllegalActionError('That player has not accepted.')
        partner = self.player(partner_id)
        self._require_affordable(p, offer.give, 'that trade')
        if not self._can_afford(partner, offer.receive):
            raise IllegalActionError(f'{partner.name} can no longer pay.')
        for r, n in offer.give.items():
            p.resources[r] -= n
            partner.resources[r] += n
        for r, n in offer.receive.items():
            partner.resources[r] -= n
            p.resources[r] += n
        self.state.trade_offer = None
        self._log(p.id, f'traded with {partner.name}.')

    def _end_turn(self, p: Player) -> None:
        """passes play on; cards bought this turn become playable."""
        state = self.state
        p.dev_cards.extend(p.new_dev_cards)
        p.new_dev_cards = []
        ids = [q.id for q in state.players]
        state.current_player_id = ids[(ids.index(p.id) + 1) % len(ids)]
        state.turn_number += 1
        state.phase = TurnPhase.ROLL
        state.dev_card_played = False
        state.trades_proposed = 0
        state.dice = None
        self._log(p.id, 'ended their turn.')

    # ----- awards and victory -----

    def _update_longest_road(self) -> None:
        """reassigns longest road after roads or settlements change.

        the holder keeps it on a tie; if they drop behind, a single leader of
        at least 5 takes it, and a tie for the lead leaves it unclaimed.
        """
        state = self.state
        lengths = {p.id: self.longest_road_length(p.id) for p in state.players}
        best = max(lengths.values())
        holder = state.longest_road_player_id
        if holder is not None and lengths[holder] == best >= MIN_LONGEST_ROAD:
            return
        leaders = [pid for pid, n in lengths.items() if n == best]
        new = leaders[0] if best >= MIN_LONGEST_ROAD and len(leaders) == 1 else None
        if new != holder:
            state.longest_road_player_id = new
            if new is not None:
                self._log(new, f'took longest road ({best}).')
            else:
                self._log(None, 'Nobody holds longest road.')

    def _check_winner(self) -> None:
        """ends the game when the current player reaches 10 points on their turn."""
        state = self.state
        if state.phase in (TurnPhase.SETUP_SETTLEMENT, TurnPhase.SETUP_ROAD):
            return
        pid = state.current_player_id
        if self.victory_points(pid) >= POINTS_TO_WIN:
            state.phase = TurnPhase.GAME_OVER
            state.winner_id = pid
            state.trade_offer = None
            self._log(pid, f'wins with {self.victory_points(pid)} points!')

    def _log(self, player_id: int | None, message: str) -> None:
        """appends to the public log, keeping only the newest entries.

        messages about a player are prefixed with their name.
        """
        if player_id is not None:
            message = f'{self.player(player_id).name} {message}'
        log = self.state.log
        log.append(
            LogEntry(
                seq=log[-1].seq + 1 if log else 0,
                turn=self.state.turn_number,
                player_id=player_id,
                message=message,
            )
        )
        del self.state.log[:-MAX_LOG_ENTRIES]
