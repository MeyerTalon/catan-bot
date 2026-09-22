"""catan rules engine.

`GameState` is the serialisable snapshot of a game; `GameEngine` validates and
applies `Action`s to it. nothing here talks to a network, database, or model.
"""

from .actions import Action
from .engine import GameEngine, IllegalActionError
from .models import GameState

__all__ = ['Action', 'GameEngine', 'GameState', 'IllegalActionError']
