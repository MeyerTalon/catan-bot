import React from "react";
import { Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import { playerColor, type GameSummary } from "@/lib/game";

type SeatListProps = {
  game: GameSummary;
  /** Show empty seats as placeholders (lobby view). */
  showEmpty?: boolean;
  /** Rendered at the end of each occupied row (e.g. a remove button). */
  renderAction?: (seat: GameSummary["seats"][number]) => React.ReactNode;
};

/** Seats in order with a colour dot, name, and bot/you markers. */
export const SeatList: React.FC<SeatListProps> = ({
  game,
  showEmpty = false,
  renderAction,
}) => {
  const empty = showEmpty ? game.max_players - game.seats.length : 0;
  return (
    <ul className="flex flex-col gap-1.5">
      {game.seats.map((seat) => (
        <li
          key={seat.seat}
          className="flex items-center gap-2 rounded-md bg-muted/50 px-2.5 py-1.5"
        >
          <span
            className="size-2.5 shrink-0 rounded-full"
            style={{
              backgroundColor:
                game.status === "waiting"
                  ? "var(--muted-foreground)"
                  : playerColor(seat.seat),
            }}
          />
          {seat.is_bot ? (
            <Bot className="size-4 text-muted-foreground" />
          ) : (
            <User className="size-4 text-muted-foreground" />
          )}
          <span className={cn("truncate", seat.is_you && "font-medium")}>
            {seat.name}
          </span>
          {seat.is_you && (
            <span className="text-xs text-muted-foreground">(you)</span>
          )}
          <span className="ml-auto">{renderAction?.(seat)}</span>
        </li>
      ))}
      {Array.from({ length: empty }, (_, i) => (
        <li
          key={`empty-${i}`}
          className="rounded-md border border-dashed px-2.5 py-1.5 text-sm text-muted-foreground"
        >
          Open seat
        </li>
      ))}
    </ul>
  );
};
