import React from "react";
import {
  DEV_CARD_LABEL,
  RESOURCE_COLOR,
  RESOURCE_LABEL,
  RESOURCES,
  type DevCard,
  type PlayerView,
} from "@/lib/game";

function countCards(cards: DevCard[]): [DevCard, number][] {
  const counts = new Map<DevCard, number>();
  for (const card of cards) counts.set(card, (counts.get(card) ?? 0) + 1);
  return [...counts];
}

/** The viewer's resource cards and development cards. */
export const PlayerHand: React.FC<{ me: PlayerView }> = ({ me }) => {
  const resources = me.resources ?? {};
  const ready = countCards(me.dev_cards ?? []);
  const fresh = countCards(me.new_dev_cards ?? []);

  return (
    <div className="flex flex-col gap-3">
      <div className="grid grid-cols-5 gap-1.5">
        {RESOURCES.map((r) => (
          <div
            key={r}
            className="flex flex-col items-center rounded-md px-1 py-1.5 text-primary-foreground"
            style={{ backgroundColor: RESOURCE_COLOR[r] }}
          >
            <span className="font-heading text-xl font-bold tabular-nums">
              {resources[r] ?? 0}
            </span>
            <span className="text-[0.7rem] font-medium">
              {RESOURCE_LABEL[r]}
            </span>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap gap-1.5 text-xs">
        {ready.length === 0 && fresh.length === 0 && (
          <span className="text-muted-foreground">No development cards.</span>
        )}
        {ready.map(([card, n]) => (
          <span key={card} className="rounded-md bg-secondary px-2 py-1">
            {DEV_CARD_LABEL[card]} ×{n}
          </span>
        ))}
        {fresh.map(([card, n]) => (
          <span
            key={`new-${card}`}
            className="rounded-md border border-dashed px-2 py-1 text-muted-foreground"
            title="Bought this turn; playable from your next turn"
          >
            {DEV_CARD_LABEL[card]} ×{n} (new)
          </span>
        ))}
      </div>
    </div>
  );
};
