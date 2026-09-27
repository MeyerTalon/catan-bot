"""the random bot: picks uniformly among its legal actions."""

from __future__ import annotations

import random

from .actions import Action
from .engine import GameEngine


def choose_action(
    engine: GameEngine, player_id: int, rng: random.Random
) -> Action | None:
    """picks a random legal action for a player, or None when it should wait.

    a bot that proposed a trade waits until every other player has answered
    rather than withdrawing it at random before humans get a say.

    Args:
        engine: the game.
        player_id: the bot's seat.
        rng: source of randomness.

    Returns:
        the chosen action, or None when the bot has nothing to do yet.
    """
    offer = engine.state.trade_offer
    if (
        offer is not None
        and offer.proposer_id == player_id
        and len(engine.actors()) > 1
    ):
        return None
    actions = engine.legal_actions(player_id)
    return rng.choice(actions) if actions else None
