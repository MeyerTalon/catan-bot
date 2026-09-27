import React, { useState } from "react";
import { CircleAlert, Plus } from "lucide-react";
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
import { Label } from "@/components/ui/label";
import type { GameSummary } from "@/lib/game";
import { goToGame } from "@/lib/route";
import { usePoll } from "@/lib/use-poll";

const LOBBY_POLL_MS = 4000;

type Lists = { mine: GameSummary[]; open: GameSummary[] };

const STATUS_LABEL: Record<GameSummary["status"], string> = {
  waiting: "Waiting for players",
  active: "In progress",
  finished: "Finished",
};

export const LobbyScreen: React.FC = () => {
  const [lists, setLists] = useState<Lists | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    const { data, error: apiError } = await api.GET("/games");
    if (data) {
      setLists(data);
      setError(null);
    } else {
      setError(apiErrorMessage(apiError, "Could not load games"));
    }
  };
  usePoll(load, LOBBY_POLL_MS);

  const join = async (gameId: number) => {
    const { error: apiError } = await api.POST("/games/{game_id}/join", {
      params: { path: { game_id: gameId } },
    });
    if (apiError) {
      setError(apiErrorMessage(apiError, "Could not join"));
      void load();
      return;
    }
    goToGame(gameId);
  };

  const active = lists?.mine.filter((g) => g.status !== "finished") ?? [];
  const finished = lists?.mine.filter((g) => g.status === "finished") ?? [];

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <main className="mx-auto grid w-full max-w-5xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[320px_1fr]">
        <div className="flex flex-col gap-6">
          <NewGameCard onError={setError} />
          {error && (
            <Alert variant="destructive">
              <CircleAlert />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
        <div className="flex flex-col gap-8">
          <GameSection
            title="Your games"
            empty="You are not in any games yet. Start one or join an open table."
            games={active}
            loading={lists === null}
            renderAction={(g) => (
              <Button
                size="sm"
                variant={g.your_turn ? "default" : "outline"}
                onClick={() => goToGame(g.id)}
              >
                {g.your_turn ? "Your move" : "Open"}
              </Button>
            )}
          />
          <GameSection
            title="Open tables"
            empty="No open tables right now."
            games={lists?.open ?? []}
            loading={lists === null}
            renderAction={(g) => (
              <Button size="sm" onClick={() => join(g.id)}>
                Join
              </Button>
            )}
          />
          {finished.length > 0 && (
            <GameSection
              title="Finished"
              empty=""
              games={finished}
              loading={false}
              renderAction={(g) => (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => goToGame(g.id)}
                >
                  View
                </Button>
              )}
            />
          )}
        </div>
      </main>
    </div>
  );
};

type GameSectionProps = {
  title: string;
  empty: string;
  games: GameSummary[];
  loading: boolean;
  renderAction: (game: GameSummary) => React.ReactNode;
};

const GameSection: React.FC<GameSectionProps> = ({
  title,
  empty,
  games,
  loading,
  renderAction,
}) => (
  <section>
    <h2 className="mb-3 text-lg font-semibold">{title}</h2>
    {loading ? (
      <p className="text-sm text-muted-foreground">Loading…</p>
    ) : games.length === 0 ? (
      <p className="text-sm text-muted-foreground">{empty}</p>
    ) : (
      <div className="grid gap-3 sm:grid-cols-2">
        {games.map((game) => (
          <Card key={game.id} size="sm">
            <CardHeader>
              <CardTitle className="flex items-center justify-between gap-2">
                <span>
                  Game #{game.id}
                  <span className="ml-2 text-xs font-normal text-muted-foreground">
                    {game.seats.length}/{game.max_players} seated
                  </span>
                </span>
                {renderAction(game)}
              </CardTitle>
              <CardDescription>
                {game.status === "active" && game.current_player_name
                  ? `${game.current_player_name}'s turn`
                  : game.status === "finished" && game.winner_name
                    ? `${game.winner_name} won`
                    : `${STATUS_LABEL[game.status]} · host ${game.host_name}`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <SeatList game={game} />
            </CardContent>
          </Card>
        ))}
      </div>
    )}
  </section>
);

type NewGameCardProps = {
  onError: (message: string | null) => void;
};

const NewGameCard: React.FC<NewGameCardProps> = ({ onError }) => {
  const [maxPlayers, setMaxPlayers] = useState(4);
  const [bots, setBots] = useState(0);
  const [creating, setCreating] = useState(false);

  const create = async () => {
    setCreating(true);
    onError(null);
    const { data, error } = await api.POST("/games", {
      body: { max_players: maxPlayers, bots },
    });
    setCreating(false);
    if (data) {
      goToGame(data.id);
    } else {
      onError(apiErrorMessage(error, "Could not create the game"));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">New game</CardTitle>
        <CardDescription>
          Open a table, fill seats with bots, and wait for friends to join.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <ChoiceRow
          label="Players"
          options={[2, 3, 4]}
          value={maxPlayers}
          onChange={(n) => {
            setMaxPlayers(n);
            setBots((b) => Math.min(b, n - 1));
          }}
        />
        <ChoiceRow
          label="Bots"
          options={Array.from({ length: maxPlayers }, (_, i) => i)}
          value={bots}
          onChange={setBots}
        />
        <p className="text-xs text-muted-foreground">
          Bots pick a random legal move every time.
          {bots === maxPlayers - 1
            ? " The game can start right away."
            : ` ${maxPlayers - 1 - bots} seat${maxPlayers - 1 - bots === 1 ? "" : "s"} left for other players.`}
        </p>
        <Button onClick={create} disabled={creating}>
          <Plus data-icon="inline-start" />
          {creating ? "Creating…" : "Create game"}
        </Button>
      </CardContent>
    </Card>
  );
};

type ChoiceRowProps = {
  label: string;
  options: number[];
  value: number;
  onChange: (value: number) => void;
};

const ChoiceRow: React.FC<ChoiceRowProps> = ({
  label,
  options,
  value,
  onChange,
}) => (
  <div className="flex items-center justify-between gap-3">
    <Label>{label}</Label>
    <div className="flex gap-1" role="radiogroup" aria-label={label}>
      {options.map((n) => (
        <Button
          key={n}
          size="sm"
          role="radio"
          aria-checked={n === value}
          variant={n === value ? "default" : "outline"}
          className="w-9"
          onClick={() => onChange(n)}
        >
          {n}
        </Button>
      ))}
    </div>
  </div>
);
