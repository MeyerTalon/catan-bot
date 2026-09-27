"""board geometry and construction.

the 19-hex layout never changes, only what sits on it, so the node/edge graph
is computed once (`topology()`) and shared by every game. hexes are pointy-top
at axial coordinates (q, r) of radius 2; with unit hex size, a hex's centre is
(sqrt(3) * (q + r / 2), 1.5 * r) and its corners are one unit away.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from functools import cache
from typing import Dict, List, Tuple

from .models import Board, HexTile, Port, Resource

Edge = Tuple[int, int]

RESOURCE_TILES: List[Resource | None] = (
    [Resource.LUMBER] * 4
    + [Resource.WOOL] * 4
    + [Resource.GRAIN] * 4
    + [Resource.BRICK] * 3
    + [Resource.ORE] * 3
    + [None]
)
NUMBER_TOKENS: List[int] = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
PORT_TYPES: List[Resource | None] = [None, None, None, None, *Resource]
# positions of the 9 harbours among the 30 coastal edges, walking round the coast
PORT_EDGE_SLOTS: List[int] = [0, 3, 6, 10, 13, 16, 20, 23, 26]


@dataclass(frozen=True)
class Topology:
    """the fixed node/edge graph of the standard board.

    Attributes:
        hex_coords: axial (q, r) per hex id.
        hex_centers: cartesian centre per hex id.
        hex_nodes: the six corner node ids per hex, clockwise from the top.
        hex_neighbors: ids of hexes sharing an edge, per hex id.
        node_positions: cartesian position per node id.
        node_hexes: ids of hexes touching each node.
        node_neighbors: ids of nodes one edge away from each node.
        edges: every edge as a sorted (node_a, node_b) pair.
        node_edges: edges touching each node.
        coastal_edges: edges on the outer rim, in order round the coast.
    """

    hex_coords: List[Tuple[int, int]]
    hex_centers: List[Tuple[float, float]]
    hex_nodes: List[List[int]]
    hex_neighbors: List[List[int]]
    node_positions: List[Tuple[float, float]]
    node_hexes: List[List[int]]
    node_neighbors: List[List[int]]
    edges: List[Edge]
    node_edges: List[List[Edge]]
    coastal_edges: List[Edge]


def edge_key(a: int, b: int) -> Edge:
    """normalises an edge to (smaller id, larger id)."""
    return (a, b) if a < b else (b, a)


@cache
def topology() -> Topology:
    """builds (once) the node/edge graph of the standard board."""
    sqrt3 = math.sqrt(3)
    hex_coords = [
        (q, r) for r in range(-2, 3) for q in range(max(-2, -r - 2), min(2, -r + 2) + 1)
    ]
    hex_centers = [(sqrt3 * (q + r / 2), 1.5 * r) for q, r in hex_coords]

    # corners of every hex, deduplicated by rounded position
    corner_points: Dict[Tuple[float, float], Tuple[float, float]] = {}
    hex_corner_keys: List[List[Tuple[float, float]]] = []
    for cx, cy in hex_centers:
        keys = []
        for i in range(6):
            angle = math.radians(60 * i - 90)
            point = (cx + math.cos(angle), cy + math.sin(angle))
            key = (round(point[0], 3), round(point[1], 3))
            corner_points.setdefault(key, point)
            keys.append(key)
        hex_corner_keys.append(keys)

    ordered_keys = sorted(corner_points, key=lambda k: (k[1], k[0]))
    node_id = {key: i for i, key in enumerate(ordered_keys)}
    node_positions = [
        (round(corner_points[k][0], 4), round(corner_points[k][1], 4))
        for k in ordered_keys
    ]
    hex_nodes = [[node_id[k] for k in keys] for keys in hex_corner_keys]

    node_hexes: List[List[int]] = [[] for _ in node_positions]
    edge_hexes: Dict[Edge, List[int]] = {}
    for hex_id, nodes in enumerate(hex_nodes):
        for i, node in enumerate(nodes):
            node_hexes[node].append(hex_id)
            edge_hexes.setdefault(edge_key(node, nodes[(i + 1) % 6]), []).append(hex_id)

    edges = sorted(edge_hexes)
    node_neighbors: List[List[int]] = [[] for _ in node_positions]
    node_edges: List[List[Edge]] = [[] for _ in node_positions]
    for a, b in edges:
        node_neighbors[a].append(b)
        node_neighbors[b].append(a)
        node_edges[a].append((a, b))
        node_edges[b].append((a, b))

    hex_neighbors: List[List[int]] = [[] for _ in hex_coords]
    for touching in edge_hexes.values():
        if len(touching) == 2:
            hex_neighbors[touching[0]].append(touching[1])
            hex_neighbors[touching[1]].append(touching[0])

    def _angle(edge: Edge) -> float:
        """angle of an edge's midpoint around the board centre."""
        (ax, ay), (bx, by) = node_positions[edge[0]], node_positions[edge[1]]
        return math.atan2((ay + by) / 2, (ax + bx) / 2)

    coastal_edges = sorted(
        (e for e, h in edge_hexes.items() if len(h) == 1), key=_angle
    )

    return Topology(
        hex_coords=hex_coords,
        hex_centers=hex_centers,
        hex_nodes=hex_nodes,
        hex_neighbors=hex_neighbors,
        node_positions=node_positions,
        node_hexes=node_hexes,
        node_neighbors=node_neighbors,
        edges=edges,
        node_edges=node_edges,
        coastal_edges=coastal_edges,
    )


def _red_numbers_adjacent(tokens: List[int | None]) -> bool:
    """whether two hexes showing 6 or 8 share an edge."""
    neighbors = topology().hex_neighbors
    return any(
        tokens[h] in (6, 8) and tokens[n] in (6, 8)
        for h in range(len(tokens))
        for n in neighbors[h]
    )


def standard_board(seed: int | None = None) -> Board:
    """builds the standard 19-hex layout with shuffled resources, tokens, and ports.

    number tokens are reshuffled until no 6 and 8 sit next to each other.

    Args:
        seed: rng seed for a reproducible layout; random when None.

    Returns:
        the generated board with the robber on the desert.
    """
    rng = random.Random(seed)
    topo = topology()
    resources = list(RESOURCE_TILES)
    rng.shuffle(resources)

    while True:
        numbers = list(NUMBER_TOKENS)
        rng.shuffle(numbers)
        tokens: List[int | None] = [
            None if resource is None else numbers.pop() for resource in resources
        ]
        if not _red_numbers_adjacent(tokens):
            break

    hexes = [
        HexTile(id=i, q=q, r=r, resource=resources[i], number_token=tokens[i])
        for i, (q, r) in enumerate(topo.hex_coords)
    ]
    port_types = list(PORT_TYPES)
    rng.shuffle(port_types)
    ports = [
        Port(resource=kind, nodes=topo.coastal_edges[slot])
        for kind, slot in zip(port_types, PORT_EDGE_SLOTS, strict=True)
    ]
    desert = resources.index(None)
    return Board(hexes=hexes, ports=ports, robber_hex_id=desert)
