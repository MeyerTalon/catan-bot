from __future__ import annotations

import typer

from .models import (
    BoardState,
    GameState,
    HexTile,
    Player,
    Resource,
    RobberState,
    TurnPhase,
)
from .ollama_client import OllamaClient

app = typer.Typer(help="Catan bot driven by gpt-oss via Ollama.")


def _sample_initial_game_state() -> GameState:
    """Construct a tiny example game state intended to exercise the model."""

    players = [
        Player(
            id=1,
            name="You",
            victory_points=2,
            resources={
                Resource.BRICK: 1,
                Resource.LUMBER: 1,
                Resource.WOOL: 1,
                Resource.GRAIN: 0,
                Resource.ORE: 0,
            },
            roads=[(1, 2)],
            settlements=[2],
            cities=[],
        ),
        Player(
            id=2,
            name="Opponent",
            victory_points=2,
            resources={
                Resource.BRICK: 0,
                Resource.LUMBER: 0,
                Resource.WOOL: 0,
                Resource.GRAIN: 0,
                Resource.ORE: 0,
            },
            roads=[(5, 6)],
            settlements=[5],
            cities=[],
        ),
    ]

    board = BoardState(
        hexes=[
            HexTile(id=1, resource=Resource.BRICK, number_token=6),
            HexTile(id=2, resource=Resource.LUMBER, number_token=8),
            HexTile(id=3, resource=None, number_token=None),  # desert
        ],
        robber=RobberState(hex_id=3),
    )

    return GameState(
        players=players,
        current_player_id=1,
        board=board,
        turn_number=1,
        phase=TurnPhase.MAIN_ACTION,
    )


@app.command()
def choose_move() -> None:
    """
    Ask gpt-oss (via Ollama) to choose a move for the current player
    from a built-in sample game state and print the result.
    """

    game_state = _sample_initial_game_state()
    client = OllamaClient()

    typer.echo("Sending game state to gpt-oss via Ollama...")
    move = client.choose_move(game_state)

    typer.echo("\n=== Model reasoning ===")
    typer.echo(move.reasoning)
    typer.echo("\n=== Model action ===")
    typer.echo(move.action.model_dump_json(indent=2))


if __name__ == "__main__":
    app()

