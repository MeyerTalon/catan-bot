from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests

from .models import GameState, ModelMoveResponse


@dataclass
class OllamaConfig:
    """Configuration for talking to Ollama."""

    model: str = "gpt-oss"
    base_url: str = "http://localhost:11434"
    timeout_seconds: int = 60


SYSTEM_PROMPT = """You are an AI agent that plays the board game Catan.

You will receive a JSON object describing the current game state.
You must respond with a SINGLE JSON object that matches this Pydantic
model (no extra keys, no commentary outside JSON):

ModelMoveResponse:
- reasoning: str  # short explanation of the move
- action: one of:
  - BuildAction:
      { "type": "build",
        "build_type": "road" | "settlement" | "city" | "development_card",
        "location": "<symbolic location id like 'node_12' or 'edge_5_6'>" }
  - TradeAction:
      { "type": "trade",
        "trade_type": "player" | "bank" | "port",
        "target_player_id": <int or null>,
        "give": { "<resource>": int, ... },
        "receive": { "<resource>": int, ... } }
  - RobberAction:
      { "type": "move_robber",
        "target_hex_id": <int>,
        "steal_from_player_id": <int or null> }
  - EndTurnAction:
      { "type": "end_turn" }

Resources are: "brick", "lumber", "wool", "grain", "ore".

Rules:
- ALWAYS respond with valid JSON that can be parsed directly, with double quotes.
- NEVER wrap JSON in backticks or explanation text.
- Prefer strong, strategically reasonable moves given the current resources and board.
- If no beneficial move exists, choose an appropriate 'end_turn' action.
"""


class OllamaClient:
    """Thin wrapper around Ollama's OpenAI-compatible chat endpoint."""

    def __init__(self, config: Optional[OllamaConfig] = None) -> None:
        self.config = config or OllamaConfig()

    def choose_move(self, game_state: GameState) -> ModelMoveResponse:
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Given the following Catan game state, choose a single move.\n"
                        "Return only the JSON for ModelMoveResponse.\n"
                        f"game_state_json: {game_state.model_dump_json()}"
                    ),
                },
            ],
        }

        url = f"{self.config.base_url}/v1/chat/completions"
        resp = requests.post(url, json=payload, timeout=self.config.timeout_seconds)
        resp.raise_for_status()
        data = resp.json()

        # Ollama's OpenAI-compatible API returns choices[0].message.content
        choices: List[Dict[str, Any]] = data.get("choices", [])
        if not choices:
            raise RuntimeError("No choices returned from Ollama.")

        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise RuntimeError("Unexpected response content from Ollama.")

        json_str = _extract_json_object(content)
        parsed = json.loads(json_str)
        return ModelMoveResponse.model_validate(parsed)


def _extract_json_object(text: str) -> str:
    """Heuristic to pull out the first top-level JSON object from a string."""

    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        raise ValueError("No JSON object found in model response.")
    return text[first : last + 1]

