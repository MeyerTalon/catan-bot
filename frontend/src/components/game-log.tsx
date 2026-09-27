import React, { useEffect, useRef } from "react";
import { playerColor, type GameView } from "@/lib/game";

/** Newest-last game log that keeps itself scrolled to the bottom. */
export const GameLog: React.FC<{ view: GameView }> = ({ view }) => {
  const box = useRef<HTMLDivElement>(null);
  const lastSeq = view.log.at(-1)?.seq;

  useEffect(() => {
    // scroll the box, not the page, so a poll never moves the viewport
    if (box.current && lastSeq !== undefined) {
      box.current.scrollTop = box.current.scrollHeight;
    }
  }, [lastSeq]);

  return (
    <div ref={box} className="max-h-64 overflow-y-auto pr-1 text-xs">
      <ol className="flex flex-col gap-1">
        {view.log.map((entry) => (
          <li key={entry.seq} className="flex gap-2">
            <span
              className="mt-1 size-1.5 shrink-0 rounded-full"
              style={{
                backgroundColor:
                  entry.player_id != null
                    ? playerColor(entry.player_id)
                    : "var(--muted-foreground)",
              }}
            />
            <span className="text-muted-foreground">{entry.message}</span>
          </li>
        ))}
      </ol>
    </div>
  );
};
