"""catan rules engine.

`GameState` is the serialisable snapshot of a game; `GameEngine` validates and
applies `Action`s to it. nothing here talks to a network, database, or model.
"""

from game_engine.actions import Action
from game_engine.engine import GameEngine, IllegalActionError
from game_engine.models import GameState

__all__ = ['Action', 'GameEngine', 'GameState', 'IllegalActionError']
