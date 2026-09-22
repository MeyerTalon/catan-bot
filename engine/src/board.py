"""board construction."""

from __future__ import annotations

from .models import Board


def standard_board(seed: int | None = None) -> Board:
    """builds the standard 19-hex layout with shuffled resources and tokens.

    Args:
        seed: rng seed for a reproducible layout; random when None.

    Returns:
        the generated board with the robber on the desert.
    """
    raise NotImplementedError
