"""the rules engine: validates and applies actions to a `GameState`."""

from __future__ import annotations

from typing import List

from .actions import Action
from .board import standard_board
from .models import GameState, Player


class IllegalActionError(Exception):
    """raised when an action is not legal in the current state."""


class GameEngine:
    """wraps a `GameState` and enforces the rules that move it forward."""

    def __init__(self, state: GameState) -> None:
        """starts from an existing state, e.g. one loaded from the database."""
        self.state = state

    @classmethod
    def new_game(cls, player_names: List[str], seed: int | None = None) -> GameEngine:
        """creates a fresh game in the setup phase.

        Args:
            player_names: seat order; ids are assigned from 1 in this order.
            seed: rng seed forwarded to the board generator.
        """
        players = [Player(id=i, name=n) for i, n in enumerate(player_names, start=1)]
        state = GameState(
            players=players, board=standard_board(seed), current_player_id=1
        )
        return cls(state)

    def legal_actions(self) -> List[Action]:
        """lists every action the current player may take right now."""
        raise NotImplementedError

    def apply(self, action: Action) -> GameState:
        """applies an action and returns the resulting state.

        Raises:
            IllegalActionError: if the action is not legal in the current state.
        """
        raise NotImplementedError
