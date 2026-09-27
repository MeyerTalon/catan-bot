import React, { useCallback, useState } from "react";
import { Bot, CircleAlert, Copy, LogOut, Play, X } from "lucide-react";
import { api, apiErrorMessage } from "@/api/client";
import { AppHeader } from "@/components/app-header";
import { SeatList } from "@/components/seat-list";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Action, GameDetail } from "@/lib/game";
import { goToLobby } from "@/lib/route";
import { usePoll } from "@/lib/use-poll";
import { GameTable } from "./GameTable";

const GAME_POLL_MS = 1500;

/** Loads one game, keeps it fresh by polling, and shows its lobby or table. */
export const GameRoomScreen: React.FC<{ gameId: number }> = ({ gameId }) => {
  const [game, setGame] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // a slow poll can land after a newer action response; never go backwards.
  // openapi-fetch widens tuples in response types, so narrow to GameDetail here
  const accept = useCallback((data: unknown) => {
    const next = data as GameDetail;
    setGame((prev) =>
      prev && prev.id === next.id && prev.version >= next.version ? prev : next,
    );
  }, []);

  usePoll(async () => {
    const {
      data,
      error: apiError,
      response,
    } = await api.GET("/games/{game_id}", {
      params: { path: { game_id: gameId } },
    });
    if (data) {
      accept(data);
    } else if (response.status === 404) {
      goToLobby();
    } else {
      setError(apiErrorMessage(apiError, "Could not load the game"));
    }
  }, GAME_POLL_MS);

  /** Runs a request that returns the game; reports errors; true on success. */
  const run = async (
    request: () => Promise<{ data?: unknown; error?: unknown }>,
  ): Promise<boolean> => {
    setBusy(true);
    setError(null);
    try {
      const { data, error: apiError } = await request();
      if (data) {
        accept(data);
        return true;
      }
      setError(apiErrorMessage(apiError, "That did not work"));
      return false;
    } finally {
      setBusy(false);
    }
  };

  const path = { params: { path: { game_id: gameId } } };
  const act = (action: Action) =>
    run(() =>
      api.POST("/games/{game_id}/actions", { ...path, body: { action } }),
    );

  const leave = async () => {
    const running = game?.status === "active";
    const message = running
      ? "Leave this game? A bot will take over your seat."
      : game?.is_host
        ? "Close this table for everyone?"
        : "Leave this table?";
    if (!window.confirm(message)) return;
    const { error: apiError } = await api.POST("/games/{game_id}/leave", path);
    if (apiError) {
      setError(apiErrorMessage(apiError, "Could not leave"));
      return;
    }
    goToLobby();
  };

  const header = (
    <AppHeader>
      <span className="hidden truncate text-sm text-muted-foreground sm:inline">
        Game #{gameId}
      </span>
      {game?.your_seat != null && (
        <Button variant="ghost" size="sm" onClick={leave}>
          <LogOut data-icon="inline-start" />
          Leave
        </Button>
      )}
    </AppHeader>
  );

  const errorAlert = error && (
    <Alert variant="destructive">
      <CircleAlert />
      <AlertDescription>{error}</AlertDescription>
    </Alert>
  );

  if (!game) {
    return (
      <div className="flex min-h-screen flex-col">
        {header}
        <main className="px-6 py-16 text-center text-muted-foreground">
          {errorAlert || "Loading game…"}
        </main>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col">
      {header}
      {game.status === "waiting" || !game.view ? (
        <WaitingRoom
          game={game}
          busy={busy}
          error={errorAlert}
          run={run}
          path={path}
        />
      ) : (
        <GameTable
          game={game}
          view={game.view}
          busy={busy}
          error={errorAlert}
          act={act}
        />
      )}
    </div>
  );
};

type WaitingRoomProps = {
  game: GameDetail;
  busy: boolean;
  error: React.ReactNode;
  run: (
    request: () => Promise<{ data?: unknown; error?: unknown }>,
  ) => Promise<boolean>;
  path: { params: { path: { game_id: number } } };
};

const WaitingRoom: React.FC<WaitingRoomProps> = ({
  game,
  busy,
  error,
  run,
  path,
}) => {
  const [copied, setCopied] = useState(false);
  const full = game.seats.length >= game.max_players;
  const seated = game.your_seat != null;

  const copyLink = async () => {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <main className="mx-auto flex w-full max-w-md flex-col gap-4 px-4 py-10">
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Game #{game.id}</CardTitle>
          <CardDescription>
            {game.is_host
              ? "Share the link, add bots, and start when everyone is here."
              : `Waiting for ${game.host_name} to start the game.`}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <SeatList
            game={game}
            showEmpty
            renderAction={(seat) =>
              game.is_host &&
              !seat.is_you && (
                <Button
                  size="icon-xs"
                  variant="ghost"
                  aria-label={`Remove ${seat.name}`}
                  disabled={busy}
                  onClick={() =>
                    run(() =>
                      api.DELETE("/games/{game_id}/seats/{seat}", {
                        params: {
                          path: { game_id: game.id, seat: seat.seat },
                        },
                      }),
                    )
                  }
                >
                  <X />
                </Button>
              )
            }
          />
          <div className="flex flex-wrap gap-2">
            {!seated && (
              <Button
                disabled={busy || full}
                onClick={() =>
                  run(() => api.POST("/games/{game_id}/join", path))
                }
              >
                {full ? "Table is full" : "Join this game"}
              </Button>
            )}
            {game.is_host && (
              <>
                <Button
                  variant="outline"
                  disabled={busy || full}
                  onClick={() =>
                    run(() => api.POST("/games/{game_id}/bots", path))
                  }
                >
                  <Bot data-icon="inline-start" />
                  Add bot
                </Button>
                <Button
                  disabled={busy || game.seats.length < 2}
                  onClick={() =>
                    run(() => api.POST("/games/{game_id}/start", path))
                  }
                >
                  <Play data-icon="inline-start" />
                  Start game
                </Button>
              </>
            )}
            <Button variant="ghost" onClick={copyLink}>
              <Copy data-icon="inline-start" />
              {copied ? "Copied" : "Copy invite link"}
            </Button>
          </div>
          {game.is_host && game.seats.length < 2 && (
            <p className="text-xs text-muted-foreground">
              At least two players are needed to start.
            </p>
          )}
        </CardContent>
      </Card>
      {error}
    </main>
  );
};
