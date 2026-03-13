"""Catan board topology and generation.

Coordinate system
-----------------
Hexes use axial (q, r) coordinates with a pointy-top orientation.
The 19 standard Catan hexes satisfy max(|q|, |r|, |q+r|) <= 2.

Vertex positions are computed from the Cartesian corners of each hex and
deduplicated by rounding, yielding 54 unique settlement spots.

Edges connect pairs of adjacent vertices, yielding 72 road spots.

Corner numbering for a pointy-top hex (counterclockwise from top-right):
  k=0  30°  top-right
  k=1  90°  top
  k=2 150°  top-left
  k=3 210°  bottom-left
  k=4 270°  bottom
  k=5 330°  bottom-right

Edge k faces the neighbor in direction:
  edge(0,1) → NE  neighbor (q+1, r-1)
  edge(1,2) → NW  neighbor (q,   r-1)
  edge(2,3) → W   neighbor (q-1, r  )
  edge(3,4) → SW  neighbor (q-1, r+1)
  edge(4,5) → SE  neighbor (q,   r+1)
  edge(5,0) → E   neighbor (q+1, r  )
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple

from catan_bot.models import Resource

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# All 19 axial (q, r) positions, sorted for a stable hex-ID assignment.
HEX_COORDS: List[Tuple[int, int]] = sorted(
    [
        (q, r)
        for q in range(-2, 3)
        for r in range(-2, 3)
        if max(abs(q), abs(r), abs(q + r)) <= 2
    ]
)
assert len(HEX_COORDS) == 19

# Standard tile distribution: 18 resource hexes + 1 desert.
TILE_DISTRIBUTION: List[Optional[Resource]] = (
    [Resource.ORE] * 3
    + [Resource.GRAIN] * 4
    + [Resource.LUMBER] * 4
    + [Resource.BRICK] * 3
    + [Resource.WOOL] * 4
    + [None]  # desert
)

# 18 number tokens (one per non-desert hex).
TOKEN_DISTRIBUTION: List[int] = [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]

# Probability pips per token (number of ways to roll that sum on 2d6).
PIPS: Dict[int, int] = {2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}

# Port definitions: (resource, q, r, k1, k2)
#   resource = None  →  3:1 generic port
#   k1, k2           →  two corner indices of the outer-facing edge of that hex
PORT_SPECS: List[Tuple[Optional[Resource], int, int, int, int]] = [
    (None,            0, -2, 1, 2),  # top:          3:1   (NW edge of  (0,-2))
    (Resource.ORE,    1, -2, 0, 1),  # top-right:    2:1 ore  (NE edge of  (1,-2))
    (Resource.GRAIN,  2, -1, 0, 1),  # right-upper:  2:1 grain (NE edge of  (2,-1))
    (None,            2,  0, 5, 0),  # right-lower:  3:1   (E  edge of  (2, 0))
    (Resource.LUMBER, 1,  1, 4, 5),  # bottom-right: 2:1 lumber (SE edge of  (1, 1))
    (None,            0,  2, 3, 4),  # bottom:       3:1   (SW edge of  (0, 2))
    (Resource.WOOL,  -1,  2, 3, 4),  # bottom-left:  2:1 wool (SW edge of (-1, 2))
    (None,           -2,  2, 2, 3),  # left-lower:   3:1   (W  edge of (-2, 2))
    (Resource.BRICK, -2,  0, 2, 3),  # left-upper:   2:1 brick (W  edge of (-2, 0))
]

# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------


def _hex_center(q: int, r: int) -> Tuple[float, float]:
    """Cartesian centre of a unit pointy-top hex at axial (q, r)."""
    x = math.sqrt(3) * q + math.sqrt(3) / 2.0 * r
    y = 1.5 * r
    return x, y


def _hex_corners(q: int, r: int) -> List[Tuple[float, float]]:
    """6 corners of hex (q, r), indexed 0-5 counterclockwise from top-right."""
    cx, cy = _hex_center(q, r)
    return [
        (
            round(cx + math.cos(math.radians(30 + 60 * k)), 6),
            round(cy + math.sin(math.radians(30 + 60 * k)), 6),
        )
        for k in range(6)
    ]


# ---------------------------------------------------------------------------
# Board dataclass
# ---------------------------------------------------------------------------


@dataclass
class CatanBoard:
    """Full topology and resource state of a Catan board.

    Attributes
    ----------
    hex_coords      : {hex_id -> (q, r)}
    hex_resources   : {hex_id -> Resource or None}  (None = desert)
    hex_tokens      : {hex_id -> int or None}        (None = desert)
    vertex_positions: {vertex_id -> (x, y)} Cartesian, for reference
    hex_vertices    : {hex_id -> [6 vertex_ids, CCW from top-right]}
    vertex_hexes    : {vertex_id -> [hex_ids]}
    vertex_neighbors: {vertex_id -> [adjacent vertex_ids]}
    vertex_ports    : {vertex_id -> Resource or None}
                      Resource = 2:1 port for that resource
                      None     = 3:1 generic port
                      absent   = no port
    edge_vertices   : {edge_id -> (v1, v2)}
    vertex_edges    : {vertex_id -> [edge_ids]}
    """

    hex_coords: Dict[int, Tuple[int, int]]
    hex_resources: Dict[int, Optional[Resource]]
    hex_tokens: Dict[int, Optional[int]]
    vertex_positions: Dict[int, Tuple[float, float]]
    hex_vertices: Dict[int, List[int]]
    vertex_hexes: Dict[int, List[int]]
    vertex_neighbors: Dict[int, List[int]]
    vertex_ports: Dict[int, Optional[Resource]]
    edge_vertices: Dict[int, Tuple[int, int]]
    vertex_edges: Dict[int, List[int]]

    # ------------------------------------------------------------------
    # Convenience queries
    # ------------------------------------------------------------------

    def adjacent_resources(self, vertex_id: int) -> Dict[Resource, int]:
        """Return {resource: total_pips} for hexes adjacent to vertex_id."""
        result: Dict[Resource, int] = {}
        for hid in self.vertex_hexes[vertex_id]:
            res = self.hex_resources[hid]
            tok = self.hex_tokens[hid]
            if res is not None and tok is not None:
                result[res] = result.get(res, 0) + PIPS[tok]
        return result

    def total_pips(self, vertex_id: int) -> int:
        """Sum of pip counts across all adjacent resource hexes."""
        return sum(self.adjacent_resources(vertex_id).values())

    def unique_resources(self, vertex_id: int) -> int:
        """Number of distinct resource types adjacent to vertex_id."""
        return len(self.adjacent_resources(vertex_id))

    def port_at(self, vertex_id: int) -> Optional[Optional[Resource]]:
        """
        Returns:
          Resource  – 2:1 port for that resource
          None      – 3:1 generic port
          sentinel  – vertex_id not in vertex_ports (use `in` check first)
        """
        return self.vertex_ports.get(vertex_id)


# ---------------------------------------------------------------------------
# Internal builder
# ---------------------------------------------------------------------------


def _build_topology(
    resources: List[Optional[Resource]],
    tokens: List[Optional[int]],
    port_specs: List[Tuple[Optional[Resource], int, int, int, int]] = PORT_SPECS,
) -> CatanBoard:
    """Build a CatanBoard from given resource and token lists.

    resources[i] and tokens[i] correspond to HEX_COORDS[i].
    tokens[i] is None for the desert.
    """
    # --- Hex coordinates & state ---
    hex_coords = {i: HEX_COORDS[i] for i in range(19)}
    hex_resources = {i: resources[i] for i in range(19)}
    hex_tokens = {i: tokens[i] for i in range(19)}

    # --- Vertices ---
    # Compute all 6 corner positions per hex and deduplicate by Cartesian position.
    pos_to_vid: Dict[Tuple[float, float], int] = {}
    hex_vertices: Dict[int, List[int]] = {}

    for hid in range(19):
        q, r = hex_coords[hid]
        corners = _hex_corners(q, r)
        vids: List[int] = []
        for pos in corners:
            if pos not in pos_to_vid:
                pos_to_vid[pos] = len(pos_to_vid)
            vids.append(pos_to_vid[pos])
        hex_vertices[hid] = vids

    n_vertices = len(pos_to_vid)
    vertex_positions: Dict[int, Tuple[float, float]] = {
        vid: pos for pos, vid in pos_to_vid.items()
    }

    # vertex -> hexes
    vertex_hexes: Dict[int, List[int]] = {v: [] for v in range(n_vertices)}
    for hid, vids in hex_vertices.items():
        for vid in vids:
            vertex_hexes[vid].append(hid)

    # --- Edges ---
    # Within each hex, each consecutive pair of corners forms an edge.
    edge_set: Dict[FrozenSet[int], int] = {}
    for hid, vids in hex_vertices.items():
        for k in range(6):
            pair: FrozenSet[int] = frozenset((vids[k], vids[(k + 1) % 6]))
            if pair not in edge_set:
                edge_set[pair] = len(edge_set)

    edge_vertices: Dict[int, Tuple[int, int]] = {
        eid: tuple(sorted(pair))  # type: ignore[assignment]
        for pair, eid in edge_set.items()
    }

    # vertex -> adjacent vertices and edges
    vertex_neighbors: Dict[int, List[int]] = {v: [] for v in range(n_vertices)}
    vertex_edges: Dict[int, List[int]] = {v: [] for v in range(n_vertices)}
    for pair, eid in edge_set.items():
        v1, v2 = tuple(pair)
        if v2 not in vertex_neighbors[v1]:
            vertex_neighbors[v1].append(v2)
        if v1 not in vertex_neighbors[v2]:
            vertex_neighbors[v2].append(v1)
        vertex_edges[v1].append(eid)
        vertex_edges[v2].append(eid)

    # --- Ports ---
    vertex_ports: Dict[int, Optional[Resource]] = {}
    for port_resource, q, r, k1, k2 in port_specs:
        corners = _hex_corners(q, r)
        for k in (k1, k2):
            pos = corners[k]
            vid = pos_to_vid.get(pos)
            if vid is not None:
                vertex_ports[vid] = port_resource

    return CatanBoard(
        hex_coords=hex_coords,
        hex_resources=hex_resources,
        hex_tokens=hex_tokens,
        vertex_positions=vertex_positions,
        hex_vertices=hex_vertices,
        vertex_hexes=vertex_hexes,
        vertex_neighbors=vertex_neighbors,
        vertex_ports=vertex_ports,
        edge_vertices=edge_vertices,
        vertex_edges=vertex_edges,
    )


# ---------------------------------------------------------------------------
# Public generators
# ---------------------------------------------------------------------------


def generate_random_board(seed: Optional[int] = None) -> CatanBoard:
    """Generate a random valid Catan board by shuffling tiles and tokens."""
    rng = random.Random(seed)

    resources = TILE_DISTRIBUTION[:]
    rng.shuffle(resources)

    token_pool = TOKEN_DISTRIBUTION[:]
    rng.shuffle(token_pool)

    tokens: List[Optional[int]] = []
    ti = 0
    for res in resources:
        if res is None:
            tokens.append(None)
        else:
            tokens.append(token_pool[ti])
            ti += 1

    return _build_topology(resources, tokens)


def generate_standard_board() -> CatanBoard:
    """Generate the fixed beginner layout from the official Catan rules.

    HEX_COORDS sorted order (q then r):
      idx  (q,  r)
       0   (-2,  0)
       1   (-2,  1)
       2   (-2,  2)
       3   (-1, -1)
       4   (-1,  0)
       5   (-1,  1)
       6   (-1,  2)
       7   ( 0, -2)
       8   ( 0, -1)
       9   ( 0,  0)
      10   ( 0,  1)
      11   ( 0,  2)
      12   ( 1, -2)
      13   ( 1, -1)
      14   ( 1,  0)
      15   ( 1,  1)
      16   ( 2, -2)
      17   ( 2, -1)
      18   ( 2,  0)
    """
    standard_resources: List[Optional[Resource]] = [
        Resource.ORE,      # 0  (-2, 0)
        Resource.WOOL,     # 1  (-2, 1)
        Resource.LUMBER,   # 2  (-2, 2)
        Resource.GRAIN,    # 3  (-1,-1)
        Resource.BRICK,    # 4  (-1, 0)
        Resource.WOOL,     # 5  (-1, 1)
        Resource.BRICK,    # 6  (-1, 2)
        Resource.ORE,      # 7  ( 0,-2)
        Resource.LUMBER,   # 8  ( 0,-1)
        None,              # 9  ( 0, 0)  desert
        Resource.LUMBER,   # 10 ( 0, 1)
        Resource.ORE,      # 11 ( 0, 2)
        Resource.LUMBER,   # 12 ( 1,-2)
        Resource.GRAIN,    # 13 ( 1,-1)
        Resource.WOOL,     # 14 ( 1, 0)
        Resource.GRAIN,    # 15 ( 1, 1)
        Resource.GRAIN,    # 16 ( 2,-2)
        Resource.BRICK,    # 17 ( 2,-1)
        Resource.WOOL,     # 18 ( 2, 0)
    ]
    standard_tokens: List[Optional[int]] = [
        10,   # 0  ORE
        2,    # 1  WOOL
        9,    # 2  LUMBER
        12,   # 3  GRAIN
        6,    # 4  BRICK
        4,    # 5  WOOL
        10,   # 6  BRICK
        9,    # 7  ORE
        11,   # 8  LUMBER
        None, # 9  desert
        3,    # 10 LUMBER
        8,    # 11 ORE
        8,    # 12 LUMBER
        3,    # 13 GRAIN
        4,    # 14 WOOL
        5,    # 15 GRAIN
        5,    # 16 GRAIN
        6,    # 17 BRICK
        11,   # 18 WOOL
    ]
    return _build_topology(standard_resources, standard_tokens)
