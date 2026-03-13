"""Vertex feature extraction for the starting-placement ML model.

Each of the 54 vertices on a Catan board gets a fixed-length feature vector
that captures everything relevant for evaluating it as a first/second
settlement location.

Feature layout (14 dimensions)
--------------------------------
 0   total_pips          – sum of pip counts across adjacent resource hexes
 1   unique_resources    – number of distinct resource types adjacent (0-3)
 2   has_port            – 1.0 if the vertex has any port
 3   port_is_2to1        – 1.0 if the port is a 2:1 (resource-specific) port
 4   res_brick           – 1.0 if BRICK is adjacent
 5   res_grain           – 1.0 if GRAIN is adjacent
 6   res_lumber          – 1.0 if LUMBER is adjacent
 7   res_ore             – 1.0 if ORE is adjacent
 8   res_wool            – 1.0 if WOOL is adjacent
 9   pip_brick           – total pip count from BRICK hexes
10   pip_grain           – total pip count from GRAIN hexes
11   pip_lumber          – total pip count from LUMBER hexes
12   pip_ore             – total pip count from ORE hexes
13   pip_wool            – total pip count from WOOL hexes
"""

from __future__ import annotations

from typing import Dict, List

from catan_bot.board import CatanBoard
from catan_bot.models import Resource

# Stable ordering so feature indices are deterministic.
_RESOURCE_ORDER: List[Resource] = [
    Resource.BRICK,
    Resource.GRAIN,
    Resource.LUMBER,
    Resource.ORE,
    Resource.WOOL,
]

FEATURE_DIM = 14
FEATURE_NAMES = (
    ["total_pips", "unique_resources", "has_port", "port_is_2to1"]
    + [f"res_{r.value}" for r in _RESOURCE_ORDER]
    + [f"pip_{r.value}" for r in _RESOURCE_ORDER]
)


def vertex_features(board: CatanBoard, vertex_id: int) -> List[float]:
    """Return a length-14 feature vector for *vertex_id* on *board*."""
    resource_pips = board.adjacent_resources(vertex_id)

    total_pips = float(sum(resource_pips.values()))
    unique_res = float(len(resource_pips))

    has_port = 1.0 if vertex_id in board.vertex_ports else 0.0
    port_is_2to1 = (
        1.0
        if vertex_id in board.vertex_ports and board.vertex_ports[vertex_id] is not None
        else 0.0
    )

    res_flags = [1.0 if r in resource_pips else 0.0 for r in _RESOURCE_ORDER]
    pip_counts = [float(resource_pips.get(r, 0)) for r in _RESOURCE_ORDER]

    return [total_pips, unique_res, has_port, port_is_2to1] + res_flags + pip_counts


def all_vertex_features(board: CatanBoard) -> Dict[int, List[float]]:
    """Return {vertex_id: feature_vector} for all 54 vertices."""
    return {vid: vertex_features(board, vid) for vid in board.vertex_positions}
