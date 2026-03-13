"""Sanity checks for CatanBoard topology and feature extraction."""

import pytest

from catan_bot.board import (
    generate_random_board,
    generate_standard_board,
    PIPS,
)
from catan_bot.features import all_vertex_features, FEATURE_DIM, FEATURE_NAMES
from catan_bot.models import Resource


# ---------------------------------------------------------------------------
# Topology invariants
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def board():
    return generate_standard_board()


def test_hex_count(board):
    assert len(board.hex_coords) == 19


def test_vertex_count(board):
    assert len(board.vertex_positions) == 54, (
        f"Expected 54 vertices, got {len(board.vertex_positions)}"
    )


def test_edge_count(board):
    assert len(board.edge_vertices) == 72, (
        f"Expected 72 edges, got {len(board.edge_vertices)}"
    )


def test_each_hex_has_six_vertices(board):
    for hid, vids in board.hex_vertices.items():
        assert len(vids) == 6, f"Hex {hid} has {len(vids)} vertices"
        assert len(set(vids)) == 6, f"Hex {hid} has duplicate vertex ids"


def test_vertex_hex_adjacency_symmetric(board):
    """If vertex v is in hex h's list, then h must be in v's list."""
    for hid, vids in board.hex_vertices.items():
        for vid in vids:
            assert hid in board.vertex_hexes[vid], (
                f"Hex {hid} lists vertex {vid} but vertex doesn't list the hex back"
            )


def test_each_vertex_adjacent_to_1_to_3_hexes(board):
    for vid, hexes in board.vertex_hexes.items():
        assert 1 <= len(hexes) <= 3, (
            f"Vertex {vid} is adjacent to {len(hexes)} hexes (expected 1–3)"
        )


def test_each_vertex_has_2_to_3_neighbors(board):
    for vid, neighbors in board.vertex_neighbors.items():
        assert 2 <= len(neighbors) <= 3, (
            f"Vertex {vid} has {len(neighbors)} neighbors (expected 2–3)"
        )


def test_neighbor_symmetry(board):
    for vid, neighbors in board.vertex_neighbors.items():
        for nb in neighbors:
            assert vid in board.vertex_neighbors[nb], (
                f"Vertex {vid} lists {nb} as neighbor but not vice-versa"
            )


def test_edge_vertex_consistency(board):
    """Every edge's two endpoints must list that edge."""
    for eid, (v1, v2) in board.edge_vertices.items():
        assert eid in board.vertex_edges[v1]
        assert eid in board.vertex_edges[v2]


# ---------------------------------------------------------------------------
# Resource / token invariants
# ---------------------------------------------------------------------------


def test_resource_counts(board):
    resources = list(board.hex_resources.values())
    assert resources.count(Resource.ORE) == 3
    assert resources.count(Resource.GRAIN) == 4
    assert resources.count(Resource.LUMBER) == 4
    assert resources.count(Resource.BRICK) == 3
    assert resources.count(Resource.WOOL) == 4
    assert resources.count(None) == 1  # desert


def test_token_counts(board):
    tokens = [t for t in board.hex_tokens.values() if t is not None]
    assert len(tokens) == 18
    assert sorted(tokens) == sorted(
        [2, 3, 3, 4, 4, 5, 5, 6, 6, 8, 8, 9, 9, 10, 10, 11, 11, 12]
    )


def test_desert_has_no_token(board):
    for hid, res in board.hex_resources.items():
        if res is None:
            assert board.hex_tokens[hid] is None


# ---------------------------------------------------------------------------
# Port invariants
# ---------------------------------------------------------------------------


def test_port_count(board):
    # 9 ports × 2 vertices each = 18 port vertices (no overlaps expected)
    assert len(board.vertex_ports) == 18, (
        f"Expected 18 port vertices, got {len(board.vertex_ports)}"
    )


def test_port_resources(board):
    port_resources = list(board.vertex_ports.values())
    # 4 generic (None) ports × 2 vertices = 8
    assert port_resources.count(None) == 8
    # 5 specific ports × 2 vertices = 10
    specific = [r for r in port_resources if r is not None]
    assert len(specific) == 10
    for r in [Resource.ORE, Resource.GRAIN, Resource.LUMBER, Resource.BRICK, Resource.WOOL]:
        assert specific.count(r) == 2


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


def test_feature_vector_length(board):
    features = all_vertex_features(board)
    assert len(features) == 54
    for vid, fvec in features.items():
        assert len(fvec) == FEATURE_DIM, (
            f"Vertex {vid} has feature vector of length {len(fvec)}, expected {FEATURE_DIM}"
        )


def test_feature_names_length():
    assert len(FEATURE_NAMES) == FEATURE_DIM


def test_total_pips_non_negative(board):
    features = all_vertex_features(board)
    for vid, fvec in features.items():
        assert fvec[0] >= 0


def test_unique_resources_range(board):
    features = all_vertex_features(board)
    for vid, fvec in features.items():
        assert 0 <= fvec[1] <= 3


def test_port_flags_consistent(board):
    features = all_vertex_features(board)
    for vid, fvec in features.items():
        has_port, port_is_2to1 = fvec[2], fvec[3]
        if port_is_2to1:
            assert has_port, f"Vertex {vid}: port_is_2to1=1 but has_port=0"


# ---------------------------------------------------------------------------
# Random board smoke test
# ---------------------------------------------------------------------------


def test_random_board_same_invariants():
    for seed in range(5):
        b = generate_random_board(seed=seed)
        assert len(b.vertex_positions) == 54
        assert len(b.edge_vertices) == 72
        assert len(b.hex_coords) == 19


def test_random_board_deterministic():
    b1 = generate_random_board(seed=42)
    b2 = generate_random_board(seed=42)
    assert b1.hex_resources == b2.hex_resources
    assert b1.hex_tokens == b2.hex_tokens
