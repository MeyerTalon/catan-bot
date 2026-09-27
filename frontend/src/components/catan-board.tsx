import React from "react";
import {
  edgeKey,
  playerColor,
  RESOURCE_COLOR,
  type Action,
  type BoardTargets,
  type GameView,
} from "@/lib/game";

type CatanBoardProps = {
  view: GameView;
  targets: BoardTargets;
  onAction: (action: Action) => void;
  onHex: (hexId: number) => void;
};

type Point = [number, number];

// geometry matches engine/src/engine/board.py: unit-size pointy-top hexes
const SQRT3 = Math.sqrt(3);
const PORT_OFFSET = 0.62;

function hexCenter(q: number, r: number): Point {
  return [SQRT3 * (q + r / 2), 1.5 * r];
}

function hexPoints([cx, cy]: Point, radius = 1): string {
  return Array.from({ length: 6 }, (_, i) => {
    const angle = ((60 * i - 90) * Math.PI) / 180;
    return `${cx + radius * Math.cos(angle)},${cy + radius * Math.sin(angle)}`;
  }).join(" ");
}

/** x offsets of the dots under a number token, one per way to roll it. */
function pipOffsets(n: number): number[] {
  const count = 6 - Math.abs(7 - n);
  return Array.from({ length: count }, (_, i) => (i - (count - 1) / 2) * 0.07);
}

function lerp([ax, ay]: Point, [bx, by]: Point, t: number): Point {
  return [ax + (bx - ax) * t, ay + (by - ay) * t];
}

const SETTLEMENT_PATH =
  "M-0.17 0.14 L-0.17 -0.04 L0 -0.19 L0.17 -0.04 L0.17 0.14 Z";
const CITY_PATH =
  "M-0.27 0.17 L-0.27 -0.06 L-0.12 -0.21 L0.03 -0.06 L0.03 -0.02 L0.27 -0.02 L0.27 0.17 Z";

export const CatanBoard: React.FC<CatanBoardProps> = ({
  view,
  targets,
  onAction,
  onHex,
}) => {
  const nodes = view.node_positions as Point[];
  const robberHex = view.board.robber_hex_id;

  return (
    <svg
      viewBox="-5.6 -5 11.2 10"
      className="h-auto w-full select-none"
      role="img"
      aria-label="Game board"
    >
      <rect
        x={-5.5}
        y={-4.9}
        width={11}
        height={9.8}
        rx={0.6}
        fill="var(--sea)"
      />

      {(view.board.ports ?? []).map((port) => {
        const a = nodes[port.nodes[0]];
        const b = nodes[port.nodes[1]];
        const mid = lerp(a, b, 0.5);
        const len = Math.hypot(mid[0], mid[1]);
        const at: Point = [
          mid[0] + (mid[0] / len) * PORT_OFFSET,
          mid[1] + (mid[1] / len) * PORT_OFFSET,
        ];
        return (
          <g key={`port-${edgeKey(port.nodes[0], port.nodes[1])}`}>
            {[a, b].map((n) => (
              <line
                key={`${n[0]},${n[1]}`}
                x1={n[0]}
                y1={n[1]}
                x2={at[0]}
                y2={at[1]}
                stroke="var(--muted-foreground)"
                strokeWidth={0.06}
              />
            ))}
            <circle
              cx={at[0]}
              cy={at[1]}
              r={0.3}
              fill={
                port.resource ? RESOURCE_COLOR[port.resource] : "var(--card)"
              }
              stroke="var(--foreground)"
              strokeWidth={0.03}
            />
            <text
              x={at[0]}
              y={at[1]}
              textAnchor="middle"
              dominantBaseline="central"
              fontSize={0.2}
              fontWeight={700}
              fill={
                port.resource
                  ? "var(--primary-foreground)"
                  : "var(--foreground)"
              }
            >
              {port.resource ? "2:1" : "3:1"}
            </text>
            <title>
              {port.resource
                ? `2:1 ${port.resource} harbour`
                : "3:1 harbour (any resource)"}
            </title>
          </g>
        );
      })}

      {view.board.hexes.map((hex) => {
        const center = hexCenter(hex.q, hex.r);
        const clickable = targets.hexes.has(hex.id);
        const token = hex.number_token;
        const hot = token === 6 || token === 8;
        return (
          <g
            key={`hex-${hex.id}`}
            onClick={clickable ? () => onHex(hex.id) : undefined}
            className={clickable ? "cursor-pointer" : undefined}
          >
            <polygon
              points={hexPoints(center)}
              fill={
                hex.resource ? RESOURCE_COLOR[hex.resource] : "var(--desert)"
              }
              stroke="var(--sea)"
              strokeWidth={0.06}
            />
            {token != null && (
              <g>
                <circle
                  cx={center[0]}
                  cy={center[1]}
                  r={0.34}
                  fill="var(--card)"
                  stroke="var(--border)"
                  strokeWidth={0.02}
                />
                <text
                  x={center[0]}
                  y={center[1] - 0.04}
                  textAnchor="middle"
                  dominantBaseline="central"
                  fontSize={hot ? 0.34 : 0.3}
                  fontWeight={700}
                  fill={hot ? "var(--destructive)" : "var(--foreground)"}
                >
                  {token}
                </text>
                {pipOffsets(token).map((dx) => (
                  <circle
                    key={dx}
                    cx={center[0] + dx}
                    cy={center[1] + 0.2}
                    r={0.022}
                    fill={hot ? "var(--destructive)" : "var(--foreground)"}
                  />
                ))}
              </g>
            )}
            {clickable && (
              <polygon
                points={hexPoints(center, 0.9)}
                fill="var(--primary)"
                fillOpacity={0.18}
                stroke="var(--primary)"
                strokeWidth={0.08}
                className="animate-pulse"
              />
            )}
            {hex.id === robberHex && (
              <Robber
                at={token != null ? [center[0] - 0.55, center[1]] : center}
              />
            )}
          </g>
        );
      })}

      {view.players.flatMap((player) =>
        player.roads.map(([a, b]) => {
          const from = lerp(nodes[a], nodes[b], 0.14);
          const to = lerp(nodes[a], nodes[b], 0.86);
          return (
            <g key={`road-${edgeKey(a, b)}`}>
              <line
                x1={from[0]}
                y1={from[1]}
                x2={to[0]}
                y2={to[1]}
                stroke="var(--background)"
                strokeWidth={0.2}
                strokeLinecap="round"
              />
              <line
                x1={from[0]}
                y1={from[1]}
                x2={to[0]}
                y2={to[1]}
                stroke={playerColor(player.id)}
                strokeWidth={0.13}
                strokeLinecap="round"
              />
            </g>
          );
        }),
      )}

      {view.edges.map(([a, b]) => {
        const action = targets.edges.get(edgeKey(a, b));
        if (!action) return null;
        const from = lerp(nodes[a], nodes[b], 0.18);
        const to = lerp(nodes[a], nodes[b], 0.82);
        return (
          <g
            key={`edge-target-${edgeKey(a, b)}`}
            className="cursor-pointer"
            onClick={() => onAction(action)}
          >
            <line
              x1={from[0]}
              y1={from[1]}
              x2={to[0]}
              y2={to[1]}
              stroke="var(--primary)"
              strokeWidth={0.1}
              strokeDasharray="0.12 0.08"
              strokeLinecap="round"
              className="animate-pulse"
            />
            <line
              x1={from[0]}
              y1={from[1]}
              x2={to[0]}
              y2={to[1]}
              stroke="transparent"
              strokeWidth={0.34}
            >
              <title>Build a road here</title>
            </line>
          </g>
        );
      })}

      {view.players.flatMap((player) => [
        ...player.settlements.map((node) => (
          <Building
            key={`s-${node}`}
            at={nodes[node]}
            path={SETTLEMENT_PATH}
            seat={player.id}
          />
        )),
        ...player.cities.map((node) => (
          <Building
            key={`c-${node}`}
            at={nodes[node]}
            path={CITY_PATH}
            seat={player.id}
          />
        )),
      ])}

      {[...targets.nodes].map(([node, action]) => {
        const [x, y] = nodes[node];
        return (
          <g
            key={`node-target-${node}`}
            className="cursor-pointer"
            onClick={() => onAction(action)}
          >
            <circle
              cx={x}
              cy={y}
              r={action.type === "build_city" ? 0.3 : 0.14}
              fill={action.type === "build_city" ? "none" : "var(--primary)"}
              stroke="var(--primary)"
              strokeWidth={0.06}
              className="animate-pulse"
            />
            <circle cx={x} cy={y} r={0.3} fill="transparent">
              <title>
                {action.type === "build_city"
                  ? "Upgrade to a city"
                  : "Build a settlement here"}
              </title>
            </circle>
          </g>
        );
      })}
    </svg>
  );
};

const Building: React.FC<{ at: Point; path: string; seat: number }> = ({
  at,
  path,
  seat,
}) => (
  <path
    d={path}
    transform={`translate(${at[0]} ${at[1]})`}
    fill={playerColor(seat)}
    stroke="var(--background)"
    strokeWidth={0.04}
    strokeLinejoin="round"
  />
);

const Robber: React.FC<{ at: Point }> = ({ at: [x, y] }) => (
  <g transform={`translate(${x} ${y})`} pointerEvents="none">
    <title>Robber</title>
    <path
      d="M-0.16 0.24 Q-0.16 -0.02 0 -0.06 Q0.16 -0.02 0.16 0.24 Z"
      fill="var(--background)"
      stroke="var(--foreground)"
      strokeWidth={0.03}
    />
    <circle
      cy={-0.14}
      r={0.1}
      fill="var(--background)"
      stroke="var(--foreground)"
      strokeWidth={0.03}
    />
  </g>
);
