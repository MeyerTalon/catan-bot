"""Mutable game-state for a 4-player Catan game (no player-to-player trades).

Separate from catan_bot/models.py, which is the LLM I/O schema.
This module is the engine's internal representation; it must be:
  - fast to copy (MCTS needs thousands of rollouts)
  - fully self-contained (given a GameState you can reconstruct any derived fact)
  - bug-free (the rules engine builds on top of this)

Key design choices
------------------
* Plain dataclasses — no Pydantic overhead.
* CatanBoard is immutable (topology never changes); GameState holds a shared
  reference so deep-copies are cheap.
* Mutable in-place API.  Callers that need isolation call state.copy() first.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from catan_bot.board import CatanBoard, generate_random_board
from catan_bot.models import Resource

# ---------------------------------------------------------------------------
# Enums and constants
# ---------------------------------------------------------------------------


class DevCard(str, Enum):
    KNIGHT = "knight"
    VICTORY_POINT = "victory_point"
    ROAD_BUILDING = "road_building"
    YEAR_OF_PLENTY = "year_of_plenty"
    MONOPOLY = "monopoly"


DEV_CARD_COUNTS: Dict[DevCard, int] = {
    DevCard.KNIGHT: 14,
    DevCard.VICTORY_POINT: 5,
    DevCard.ROAD_BUILDING: 2,
    DevCard.YEAR_OF_PLENTY: 2,
    DevCard.MONOPOLY: 2,
}

# Cost to build each structure / buy a dev card.
BUILD_COSTS: Dict[str, Dict[Resource, int]] = {
    "road":        {Resource.BRICK: 1, Resource.LUMBER: 1},
    "settlement":  {Resource.BRICK: 1, Resource.LUMBER: 1, Resource.WOOL: 1, Resource.GRAIN: 1},
    "city":        {Resource.ORE: 3, Resource.GRAIN: 2},
    "dev_card":    {Resource.ORE: 1, Resource.GRAIN: 1, Resource.WOOL: 1},
}

# Number of pieces each player starts with.
MAX_ROADS        = 15
MAX_SETTLEMENTS  = 5
MAX_CITIES       = 4

# Victory points needed to win.
WIN_VP = 10


class Phase(str, Enum):
    """Turn phase — determines which actions are legal."""

    # ---- Initial placement (snake draft) ----
    INITIAL_SETTLEMENT = "initial_settlement"  # current player places a settlement
    INITIAL_ROAD       = "initial_road"        # current player places a road next to last settlement

    # ---- Normal turn ----
    PRE_ROLL    = "pre_roll"     # may play Knight, then must roll
    ROLL        = "roll"         # must roll dice
    DISCARD     = "discard"      # ≥1 player must discard half their cards (after rolling 7)
    MOVE_ROBBER = "move_robber"  # must move robber to a new hex
    STEAL       = "steal"        # optionally steal 1 card from an adjacent player
    POST_ROLL   = "post_roll"    # build / buy / play dev card / trade / end turn

    # ---- Dev card sub-phases (entered from POST_ROLL) ----
    YEAR_OF_PLENTY = "year_of_plenty"  # choose 2 resources from bank
    MONOPOLY       = "monopoly"        # choose a resource to claim from all players
    ROAD_BUILDING  = "road_building"   # place up to 2 free roads

    # ---- Terminal ----
    GAME_OVER = "game_over"


# ---------------------------------------------------------------------------
# PlayerState
# ---------------------------------------------------------------------------


@dataclass
class PlayerState:
    """Per-player mutable state."""

    player_id: int

    # Resources in hand.
    resources: Dict[Resource, int] = field(
        default_factory=lambda: {r: 0 for r in Resource}
    )

    # Dev cards available to play this turn (not bought this turn).
    dev_cards: Dict[DevCard, int] = field(
        default_factory=lambda: {d: 0 for d in DevCard}
    )
    # Dev cards bought THIS turn — cannot be played until next turn.
    dev_cards_new: Dict[DevCard, int] = field(
        default_factory=lambda: {d: 0 for d in DevCard}
    )
    # Dev cards already played (used to track army size).
    dev_cards_played: Dict[DevCard, int] = field(
        default_factory=lambda: {d: 0 for d in DevCard}
    )

    # Set True when a dev card is played during the current turn.
    has_played_dev_this_turn: bool = False

    # ----------------------------------------------------------------
    # Simple computed properties
    # ----------------------------------------------------------------

    @property
    def resource_count(self) -> int:
        return sum(self.resources.values())

    @property
    def dev_card_count(self) -> int:
        """Total dev cards in hand (playable + newly bought)."""
        return sum(self.dev_cards.values()) + sum(self.dev_cards_new.values())

    @property
    def army_size(self) -> int:
        return self.dev_cards_played.get(DevCard.KNIGHT, 0)

    def can_afford(self, cost: Dict[Resource, int]) -> bool:
        return all(self.resources.get(r, 0) >= amt for r, amt in cost.items())

    def pay(self, cost: Dict[Resource, int]) -> None:
        """Deduct resources.  Caller must ensure can_afford() first."""
        for r, amt in cost.items():
            self.resources[r] -= amt

    def receive(self, resource: Resource, amount: int = 1) -> None:
        self.resources[resource] = self.resources.get(resource, 0) + amount

    def copy(self) -> "PlayerState":
        p = PlayerState(player_id=self.player_id)
        p.resources        = dict(self.resources)
        p.dev_cards        = dict(self.dev_cards)
        p.dev_cards_new    = dict(self.dev_cards_new)
        p.dev_cards_played = dict(self.dev_cards_played)
        p.has_played_dev_this_turn = self.has_played_dev_this_turn
        return p


# ---------------------------------------------------------------------------
# GameState
# ---------------------------------------------------------------------------


@dataclass
class GameState:
    """Complete mutable state of one Catan game."""

    # Immutable board topology shared across all copies.
    board: CatanBoard

    # Per-player state; index == player_id.
    players: List[PlayerState]

    # ---- Board occupation ----
    settlements: Dict[int, int] = field(default_factory=dict)  # vertex_id → player_id
    cities:      Dict[int, int] = field(default_factory=dict)  # vertex_id → player_id
    roads:       Dict[int, int] = field(default_factory=dict)  # edge_id   → player_id

    # ---- Robber ----
    robber_hex: int = 0  # hex_id; starts on the desert

    # ---- Dev card deck ----
    # Ordered list; cards are drawn from the front (index 0).
    dev_deck: List[DevCard] = field(default_factory=list)

    # ---- Special awards ----
    longest_road_player: Optional[int] = None  # None until first player hits ≥5
    longest_road_length: int = 4               # current holder's length (threshold = 5)
    largest_army_player: Optional[int] = None  # None until first player hits ≥3 knights
    largest_army_size:   int = 2               # current holder's size   (threshold = 3)

    # ---- Turn tracking ----
    current_player: int  = 0
    turn_number:    int  = 0
    phase:          Phase = Phase.INITIAL_SETTLEMENT

    # ---- Initial placement sub-state ----
    # Snake-draft order, e.g. [0,1,2,3,3,2,1,0] for 4 players.
    initial_placement_order: List[int] = field(default_factory=list)
    initial_placement_index: int = 0
    # Vertex of the most recent initial settlement (needed to constrain road placement).
    last_initial_settlement: Optional[int] = None

    # ---- Post-7 sub-state ----
    # Players who still need to discard (index into self.players).
    pending_discard_players: List[int] = field(default_factory=list)

    # ---- Road-building sub-state ----
    road_building_roads_placed: int = 0  # 0, 1, or 2

    # ---- Year-of-plenty sub-state ----
    # Resources already chosen (0 or 1 so far; 2 = resolved).
    year_of_plenty_chosen: List[Resource] = field(default_factory=list)

    # ---- Last dice roll ----
    last_roll: Optional[int] = None

    # ----------------------------------------------------------------
    # Factory
    # ----------------------------------------------------------------

    @classmethod
    def create_new(
        cls,
        board: Optional[CatanBoard] = None,
        n_players: int = 4,
        seed: Optional[int] = None,
    ) -> "GameState":
        """Create a fresh game ready for initial placement.

        Parameters
        ----------
        board     : provide a pre-built CatanBoard, or None to generate randomly.
        n_players : 2–4 players supported.
        seed      : RNG seed for deck shuffle and (if board is None) board generation.
        """
        rng = random.Random(seed)

        if board is None:
            board = generate_random_board(seed=seed)

        # Robber starts on the desert.
        desert_hex = next(
            hid for hid, res in board.hex_resources.items() if res is None
        )

        # Shuffle dev-card deck.
        deck: List[DevCard] = [
            card
            for card, count in DEV_CARD_COUNTS.items()
            for _ in range(count)
        ]
        rng.shuffle(deck)

        # Snake-draft placement order: [0,1,...,n-1, n-1,...,1,0]
        fwd = list(range(n_players))
        order = fwd + list(reversed(fwd))

        players = [PlayerState(player_id=i) for i in range(n_players)]

        return cls(
            board=board,
            players=players,
            robber_hex=desert_hex,
            dev_deck=deck,
            initial_placement_order=order,
            initial_placement_index=0,
            current_player=order[0],
            phase=Phase.INITIAL_SETTLEMENT,
        )

    # ----------------------------------------------------------------
    # Cheap copy (board is shared; everything else is shallow/new)
    # ----------------------------------------------------------------

    def copy(self) -> "GameState":
        """Return a copy suitable for MCTS rollouts.

        CatanBoard is immutable so we share the reference.
        All mutable game state is copied.
        """
        g = GameState.__new__(GameState)
        g.board    = self.board          # shared — never mutated
        g.players  = [p.copy() for p in self.players]

        g.settlements = dict(self.settlements)
        g.cities      = dict(self.cities)
        g.roads       = dict(self.roads)

        g.robber_hex = self.robber_hex
        g.dev_deck   = list(self.dev_deck)

        g.longest_road_player = self.longest_road_player
        g.longest_road_length = self.longest_road_length
        g.largest_army_player = self.largest_army_player
        g.largest_army_size   = self.largest_army_size

        g.current_player = self.current_player
        g.turn_number    = self.turn_number
        g.phase          = self.phase

        g.initial_placement_order = list(self.initial_placement_order)
        g.initial_placement_index = self.initial_placement_index
        g.last_initial_settlement = self.last_initial_settlement

        g.pending_discard_players   = list(self.pending_discard_players)
        g.road_building_roads_placed = self.road_building_roads_placed
        g.year_of_plenty_chosen      = list(self.year_of_plenty_chosen)
        g.last_roll                  = self.last_roll

        return g

    # ----------------------------------------------------------------
    # Piece-count queries  (computed from board state, no duplication)
    # ----------------------------------------------------------------

    def settlements_on_board(self, player_id: int) -> int:
        """Settlements currently on the board (not upgraded to cities)."""
        return sum(1 for pid in self.settlements.values() if pid == player_id)

    def cities_on_board(self, player_id: int) -> int:
        return sum(1 for pid in self.cities.values() if pid == player_id)

    def roads_on_board(self, player_id: int) -> int:
        return sum(1 for pid in self.roads.values() if pid == player_id)

    def settlements_remaining(self, player_id: int) -> int:
        return MAX_SETTLEMENTS - self.settlements_on_board(player_id)

    def cities_remaining(self, player_id: int) -> int:
        return MAX_CITIES - self.cities_on_board(player_id)

    def roads_remaining(self, player_id: int) -> int:
        return MAX_ROADS - self.roads_on_board(player_id)

    # ----------------------------------------------------------------
    # Victory-point queries
    # ----------------------------------------------------------------

    def victory_points(self, player_id: int) -> int:
        """Total VP including hidden VP dev cards."""
        p = self.players[player_id]
        vp = (
            self.settlements_on_board(player_id)
            + self.cities_on_board(player_id) * 2
            + p.dev_cards.get(DevCard.VICTORY_POINT, 0)
            + p.dev_cards_new.get(DevCard.VICTORY_POINT, 0)
        )
        if self.longest_road_player == player_id:
            vp += 2
        if self.largest_army_player == player_id:
            vp += 2
        return vp

    def public_victory_points(self, player_id: int) -> int:
        """VP visible to all players (VP dev cards are hidden)."""
        p = self.players[player_id]
        return (
            self.victory_points(player_id)
            - p.dev_cards.get(DevCard.VICTORY_POINT, 0)
            - p.dev_cards_new.get(DevCard.VICTORY_POINT, 0)
        )

    @property
    def winner(self) -> Optional[int]:
        """Return player_id of the winner, or None if game is ongoing."""
        for pid in range(len(self.players)):
            if self.victory_points(pid) >= WIN_VP:
                return pid
        return None

    # ----------------------------------------------------------------
    # Board-occupation helpers
    # ----------------------------------------------------------------

    def occupied_by(self, vertex_id: int) -> Optional[int]:
        """Player who has a settlement or city at vertex_id, or None."""
        return self.settlements.get(vertex_id) or self.cities.get(vertex_id)

    def has_road_at(self, edge_id: int) -> bool:
        return edge_id in self.roads

    def road_owner(self, edge_id: int) -> Optional[int]:
        return self.roads.get(edge_id)

    def player_vertices(self, player_id: int) -> List[int]:
        """All vertices where player_id has a settlement or city."""
        return [
            v for v, pid in {**self.settlements, **self.cities}.items()
            if pid == player_id
        ]

    def player_edges(self, player_id: int) -> List[int]:
        """All edges where player_id has a road."""
        return [e for e, pid in self.roads.items() if pid == player_id]

    # ----------------------------------------------------------------
    # Port helpers
    # ----------------------------------------------------------------

    def player_ports(self, player_id: int) -> List[Optional[Resource]]:
        """Port types accessible to player_id (via any settlement or city)."""
        ports = []
        for vid in self.player_vertices(player_id):
            if vid in self.board.vertex_ports:
                ports.append(self.board.vertex_ports[vid])
        return ports

    def best_trade_ratio(self, player_id: int, resource: Resource) -> int:
        """Best bank/port trade ratio for giving *resource*. Returns 2, 3, or 4."""
        ports = self.player_ports(player_id)
        if resource in ports:
            return 2
        if None in ports:  # 3:1 generic port
            return 3
        return 4

    # ----------------------------------------------------------------
    # Initial placement helpers
    # ----------------------------------------------------------------

    @property
    def in_initial_placement(self) -> bool:
        return self.phase in (Phase.INITIAL_SETTLEMENT, Phase.INITIAL_ROAD)

    @property
    def initial_placement_done(self) -> bool:
        return self.initial_placement_index >= len(self.initial_placement_order)

    @property
    def is_second_initial_settlement(self) -> bool:
        """True when placing the second round of settlements (reverse order)."""
        return self.initial_placement_index >= len(self.players)

    # ----------------------------------------------------------------
    # Dev deck
    # ----------------------------------------------------------------

    def draw_dev_card(self) -> Optional[DevCard]:
        """Draw and return the top card, or None if deck is empty."""
        return self.dev_deck.pop(0) if self.dev_deck else None

    @property
    def dev_deck_remaining(self) -> int:
        return len(self.dev_deck)
