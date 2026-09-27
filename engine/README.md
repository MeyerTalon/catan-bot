# Catan rules engine

Pure-Python rules for the base game of Catan (2-4 players). No I/O: the backend loads a `GameState` from JSON, applies one move, and stores it back.

## Layout

```
engine/src/engine/
├── models.py   # GameState, Player, Board, TradeOffer, ... (pydantic, JSON round-trippable)
├── actions.py  # Action: a discriminated union on `type` (roll_dice, build_road, propose_trade, ...)
├── board.py    # fixed node/edge topology + standard_board(seed)
├── engine.py   # GameEngine: actors(), legal_actions(player), apply(player, action)
├── views.py    # game_view(engine, seat): one seat's redacted view + its legal actions
└── bot.py      # choose_action: the random bot
```

## Usage

```python
from engine import GameEngine, choose_action, game_view

engine = GameEngine.new_game(['Ada', 'Bot 1'])
seat = engine.actors()[0]                 # who the game is waiting on
engine.apply(seat, engine.legal_actions(seat)[0])
view = game_view(engine, viewer_id=1)     # hides other hands and the deck order
```

Several players can be asked to act at once (discarding after a 7, answering a trade offer), so every call names the acting seat; `actors()` lists who the game is waiting on. Illegal moves raise `IllegalActionError` with a message fit to show a player.

## Rules covered

- Snake-order setup; the second settlement pays one card per adjacent resource hex
- Production with bank limits (a short resource goes to nobody unless only one player is owed it)
- Rolling 7: players with more than 7 cards discard half, then the robber moves and steals
- Roads, settlements (distance rule, road connection), cities; piece limits 15 / 5 / 4
- Development cards (14 knights, 5 victory points, 2 each of road building, year of plenty, monopoly): one per turn, not on the turn bought; knights may be played before rolling
- Longest road (5+, blocked by opponents' buildings; ties keep the holder) and largest army (3+)
- Bank trades at 4:1, 3:1 and 2:1 harbours; domestic trade offers to the table (at most 3 per turn) that other players accept or reject and the proposer confirms with one of them
- 10 victory points wins, only on your own turn; hidden victory point cards count

`legal_actions` lists every legal move, except that domestic offers are limited to one-for-one trades so bots have a finite list; any valid bundle can still be applied.

## Checks

```bash
mise run ge:check   # ruff format --check, ruff check, mypy, pytest
```
