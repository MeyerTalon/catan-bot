/**
 * Game types (from the generated OpenAPI schema) plus display constants and
 * small helpers shared by the lobby and the board.
 */

import type { components } from "@/api/schema";

type Schemas = components["schemas"];

export type GameDetail = Schemas["GameDetail"];
export type GameSummary = Schemas["GameSummary"];
export type GameView = Schemas["GameView"];
export type PlayerView = Schemas["PlayerView"];
export type TradeOffer = Schemas["TradeOffer"];
export type Action = Schemas["GameActionRequest"]["action"];
export type Resource = Schemas["Resource"];
export type DevCard = Schemas["DevCard"];
export type Hand = Partial<Record<Resource, number>>;

export type ActionOf<T extends Action["type"]> = Extract<Action, { type: T }>;

export const RESOURCES: Resource[] = [
  "brick",
  "lumber",
  "wool",
  "grain",
  "ore",
];

export const RESOURCE_LABEL: Record<Resource, string> = {
  brick: "Brick",
  lumber: "Lumber",
  wool: "Wool",
  grain: "Grain",
  ore: "Ore",
};

/** Theme tokens for each resource's tile and card colour. */
export const RESOURCE_COLOR: Record<Resource, string> = {
  brick: "var(--chart-2)",
  lumber: "var(--chart-3)",
  wool: "var(--chart-5)",
  grain: "var(--chart-1)",
  ore: "var(--chart-4)",
};

export const DEV_CARD_LABEL: Record<DevCard, string> = {
  knight: "Knight",
  victory_point: "Victory point",
  road_building: "Road building",
  year_of_plenty: "Year of plenty",
  monopoly: "Monopoly",
};

export const COSTS: Record<"road" | "settlement" | "city" | "dev", Hand> = {
  road: { brick: 1, lumber: 1 },
  settlement: { brick: 1, lumber: 1, wool: 1, grain: 1 },
  city: { grain: 2, ore: 3 },
  dev: { wool: 1, grain: 1, ore: 1 },
};

/** Seat colour token; seats are 1-4. */
export function playerColor(seat: number): string {
  return `var(--player-${((seat - 1) % 4) + 1})`;
}

export function edgeKey(a: number, b: number): string {
  return a < b ? `${a}-${b}` : `${b}-${a}`;
}

export function handTotal(hand: Hand): number {
  return RESOURCES.reduce((sum, r) => sum + (hand[r] ?? 0), 0);
}

export function formatHand(hand: Hand): string {
  const parts = RESOURCES.filter((r) => (hand[r] ?? 0) > 0).map(
    (r) => `${hand[r]} ${RESOURCE_LABEL[r].toLowerCase()}`,
  );
  return parts.length ? parts.join(", ") : "nothing";
}

export function actionsOfType<T extends Action["type"]>(
  actions: Action[],
  type: T,
): ActionOf<T>[] {
  return actions.filter((a): a is ActionOf<T> => a.type === type);
}

export function playerName(view: GameView, seat: number | null | undefined) {
  return view.players.find((p) => p.id === seat)?.name ?? "Someone";
}

/** One-line description of what the game is waiting for. */
export function phaseText(view: GameView): string {
  const current = playerName(view, view.current_player_id);
  switch (view.phase) {
    case "setup_settlement":
      return `${current} is placing a settlement`;
    case "setup_road":
      return `${current} is placing a road`;
    case "roll":
      return `${current} is about to roll`;
    case "discard":
      return "Players with more than 7 cards are discarding";
    case "move_robber":
      return `${current} is moving the robber`;
    case "road_building":
      return `${current} is placing free roads`;
    case "main":
      return view.trade_offer
        ? `${playerName(view, view.trade_offer.proposer_id)} offered a trade`
        : `${current} is building and trading`;
    case "game_over":
      return `${playerName(view, view.winner_id)} won the game`;
  }
}

export type BuildMode = "road" | "settlement" | "city" | null;

/** Clickable board spots, each mapped to the action a click submits. */
export type BoardTargets = {
  nodes: Map<number, Action>;
  edges: Map<string, Action>;
  hexes: Set<number>;
};

/**
 * Which board spots are clickable given the phase and chosen build mode;
 * none while `enabled` is false (e.g. a move is in flight).
 */
export function boardTargets(
  view: GameView,
  mode: BuildMode,
  enabled = true,
): BoardTargets {
  const legal = enabled ? view.legal_actions : [];
  const phase = view.phase;
  const targets: BoardTargets = {
    nodes: new Map(),
    edges: new Map(),
    hexes: new Set(),
  };
  if (phase === "setup_road" || phase === "road_building" || mode === "road") {
    for (const a of actionsOfType(legal, "build_road")) {
      targets.edges.set(edgeKey(a.edge[0], a.edge[1]), a);
    }
  }
  if (phase === "setup_settlement" || mode === "settlement") {
    for (const a of actionsOfType(legal, "build_settlement")) {
      targets.nodes.set(a.node, a);
    }
  }
  if (mode === "city") {
    for (const a of actionsOfType(legal, "build_city")) {
      targets.nodes.set(a.node, a);
    }
  }
  for (const a of actionsOfType(legal, "move_robber")) {
    targets.hexes.add(a.hex_id);
  }
  return targets;
}
