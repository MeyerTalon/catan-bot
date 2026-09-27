import React from "react";
import { Award, Bot, Hourglass, Route, Swords } from "lucide-react";
import { cn } from "@/lib/utils";
import { playerColor, type GameSummary, type GameView } from "@/lib/game";

type PlayerListProps = {
  view: GameView;
  seats: GameSummary["seats"];
};

/** Scoreboard: points, card counts, and awards for every seat. */
export const PlayerList: React.FC<PlayerListProps> = ({ view, seats }) => (
  <ul className="flex flex-col gap-1.5">
    {view.players.map((p) => {
      const seat = seats.find((s) => s.seat === p.id);
      const current = p.id === view.current_player_id;
      const waiting = view.waiting_on.includes(p.id);
      return (
        <li
          key={p.id}
          className={cn(
            "rounded-md border px-2.5 py-2",
            current ? "border-primary/60 bg-muted" : "border-transparent",
          )}
        >
          <div className="flex items-center gap-2">
            <span
              className="size-3 shrink-0 rounded-full"
              style={{ backgroundColor: playerColor(p.id) }}
            />
            <span className="truncate font-medium">{p.name}</span>
            {seat?.is_bot && (
              <Bot
                className="size-3.5 text-muted-foreground"
                aria-label="bot"
              />
            )}
            {seat?.is_you && (
              <span className="text-xs text-muted-foreground">(you)</span>
            )}
            {waiting && view.phase !== "game_over" && (
              <Hourglass
                className="size-3.5 text-primary"
                aria-label="waiting on this player"
              />
            )}
            <span className="ml-auto font-heading text-lg font-semibold tabular-nums">
              {p.victory_points}
              <span className="ml-0.5 text-xs font-normal text-muted-foreground">
                VP
              </span>
            </span>
          </div>
          <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
            <span>{p.resource_count} cards</span>
            <span>{p.dev_card_count} dev</span>
            <span>
              {p.knights_played} knight{p.knights_played === 1 ? "" : "s"}
            </span>
            <span>road {p.longest_road_length}</span>
            {view.longest_road_player_id === p.id && (
              <span className="flex items-center gap-1 text-primary">
                <Route className="size-3" /> Longest road
              </span>
            )}
            {view.largest_army_player_id === p.id && (
              <span className="flex items-center gap-1 text-primary">
                <Swords className="size-3" /> Largest army
              </span>
            )}
            {view.winner_id === p.id && (
              <span className="flex items-center gap-1 text-primary">
                <Award className="size-3" /> Winner
              </span>
            )}
          </div>
        </li>
      );
    })}
  </ul>
);
