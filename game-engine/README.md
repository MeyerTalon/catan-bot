# game-engine

Pure-Python rules engine for Catan. It owns the board, the serialisable `GameState`, the `Action` types, and the `GameEngine` that validates and applies them. No I/O: the backend stores `GameState` as JSON in `game_sessions.state`, and any bot or UI drives the engine through `legal_actions()` / `apply()`.

```
game_engine/
  models.py    Resource, TurnPhase, HexTile, Board, Player, GameState
  actions.py   BuildRoad, BuildSettlement, BuildCity, EndTurn → Action
  board.py     standard_board()
  engine.py    GameEngine, IllegalActionError
tests/
```

It is a member of the repo-root uv workspace (one `uv.lock`, one `.venv` at the root). Add dependencies with `uv add <package>` from this directory.

```bash
mise run ge:check     # ruff format --check, ruff check, mypy, pytest
mise run ge:format
mise run ge:test
```
