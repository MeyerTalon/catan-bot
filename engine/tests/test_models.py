"""game state serialisation."""

from engine.models import Board, GameState, HexTile, Player, Resource


def test_game_state_round_trips_through_json() -> None:
    """the state stored in `game_sessions.state` must load back unchanged."""
    state = GameState(
        players=[Player(id=1, name='a', resources={Resource.ORE: 2}, roads=[(1, 2)])],
        board=Board(
            hexes=[
                HexTile(id=1),
                HexTile(id=2, resource=Resource.WOOL, number_token=8),
            ],
            robber_hex_id=1,
        ),
        current_player_id=1,
    )
    assert GameState.model_validate_json(state.model_dump_json()) == state
