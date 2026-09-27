import React, { useMemo, useState } from "react";
import { CatanBoard } from "@/components/catan-board";
import { GameLog } from "@/components/game-log";
import { PlayerHand } from "@/components/player-hand";
import { PlayerList } from "@/components/player-list";
import { TurnPanel } from "@/components/turn-panel";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  actionsOfType,
  boardTargets,
  phaseText,
  type Action,
  type BuildMode,
  type GameDetail,
  type GameView,
} from "@/lib/game";

type GameTableProps = {
  game: GameDetail;
  view: GameView;
  busy: boolean;
  error: React.ReactNode;
  act: (action: Action) => Promise<boolean>;
};

/** A half-made choice (build mode, robber hex) and the moment it belongs to. */
type Choice = { moment: string; mode: BuildMode; robberHex: number | null };

export const GameTable: React.FC<GameTableProps> = ({
  game,
  view,
  busy,
  error,
  act,
}) => {
  // a new phase or turn silently drops any half-made choice
  const moment = `${view.phase}:${view.turn_number}:${view.current_player_id}`;
  const [choice, setChoice] = useState<Choice | null>(null);
  const current = choice?.moment === moment ? choice : null;
  const mode = current?.mode ?? null;
  const robberHex = current?.robberHex ?? null;
  const setMode = (next: BuildMode) =>
    setChoice({ moment, mode: next, robberHex: null });
  const setRobberHex = (hexId: number | null) =>
    setChoice({ moment, mode: null, robberHex: hexId });

  const me = view.players.find((p) => p.id === view.viewer_id);
  const targets = useMemo(
    () => boardTargets(view, mode, !busy),
    [view, mode, busy],
  );

  const submit = async (action: Action): Promise<boolean> => {
    const ok = await act(action);
    if (ok) setChoice(null);
    return ok;
  };

  const onHex = (hexId: number) => {
    const moves = actionsOfType(view.legal_actions, "move_robber").filter(
      (a) => a.hex_id === hexId,
    );
    if (moves.length === 1) {
      void submit(moves[0]);
    } else {
      setRobberHex(hexId);
    }
  };

  return (
    <main className="mx-auto grid w-full max-w-7xl gap-4 px-3 py-4 sm:px-4 lg:grid-cols-[minmax(0,1fr)_380px]">
      <div className="flex min-w-0 flex-col gap-4">
        <Card className="py-0">
          <CatanBoard
            view={view}
            targets={targets}
            onAction={submit}
            onHex={onHex}
          />
        </Card>
        {me && (
          <Card size="sm">
            <CardHeader>
              <CardTitle>Your hand</CardTitle>
            </CardHeader>
            <CardContent>
              <PlayerHand me={me} />
            </CardContent>
          </Card>
        )}
      </div>

      <aside className="flex min-w-0 flex-col gap-4">
        <Card size="sm">
          <CardHeader>
            <CardTitle className="flex items-center justify-between gap-2">
              <span>{phaseText(view)}</span>
              {view.dice && <Dice dice={view.dice} />}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {me ? (
              <TurnPanel
                view={view}
                me={me}
                busy={busy}
                act={submit}
                mode={mode}
                setMode={setMode}
                robberHex={robberHex}
                setRobberHex={setRobberHex}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                You are watching this game.
              </p>
            )}
            {error}
          </CardContent>
        </Card>

        <Card size="sm">
          <CardHeader>
            <CardTitle>Players</CardTitle>
          </CardHeader>
          <CardContent>
            <PlayerList view={view} seats={game.seats} />
            <p className="mt-2 text-xs text-muted-foreground">
              Turn {view.turn_number} · {view.dev_deck_count} development cards
              left · first to 10 points wins
            </p>
          </CardContent>
        </Card>

        <Card size="sm">
          <CardHeader>
            <CardTitle>Log</CardTitle>
          </CardHeader>
          <CardContent>
            <GameLog view={view} />
          </CardContent>
        </Card>
      </aside>
    </main>
  );
};

const Dice: React.FC<{ dice: [number, number] }> = ({ dice }) => (
  <span
    className="flex items-center gap-1"
    aria-label={`Rolled ${dice[0] + dice[1]}`}
  >
    <Die value={dice[0]} />
    <Die value={dice[1]} />
  </span>
);

const Die: React.FC<{ value: number }> = ({ value }) => (
  <span className="flex size-7 items-center justify-center rounded-md bg-foreground font-heading text-base font-bold text-background">
    {value}
  </span>
);
