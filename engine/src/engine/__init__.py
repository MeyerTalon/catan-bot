"""catan rules engine.

`GameState` is the serialisable snapshot of a game; `GameEngine` validates and
applies `Action`s to it; `game_view` is what one seat may see; `choose_action`
is the random bot. nothing here talks to a network, database, or model.
"""

from .actions import Action, action_adapter
from .bot import choose_action
from .engine import MAX_PLAYERS, MIN_PLAYERS, GameEngine, IllegalActionError
from .models import GameState, TurnPhase
from .views import GameView, game_view

__all__ = [
    'MAX_PLAYERS',
    'MIN_PLAYERS',
    'Action',
    'GameEngine',
    'GameState',
    'GameView',
    'IllegalActionError',
    'TurnPhase',
    'action_adapter',
    'choose_action',
    'game_view',
]
