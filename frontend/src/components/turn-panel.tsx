import React, { useState } from "react";
import { Dices, Hammer, Handshake, Landmark, SkipForward } from "lucide-react";
import { ResourceChoice, ResourcePicker } from "@/components/resource-picker";
import { Button } from "@/components/ui/button";
import {
  actionsOfType,
  COSTS,
  formatHand,
  handTotal,
  playerName,
  RESOURCES,
  type Action,
  type BuildMode,
  type GameView,
  type Hand,
  type PlayerView,
  type Resource,
  type TradeOffer,
} from "@/lib/game";

type Act = (action: Action) => Promise<boolean>;

type TurnPanelProps = {
  view: GameView;
  me: PlayerView;
  busy: boolean;
  act: Act;
  mode: BuildMode;
  setMode: (mode: BuildMode) => void;
  robberHex: number | null;
  setRobberHex: (hexId: number | null) => void;
};

/** Everything the viewer can do right now, or who the game is waiting on. */
export const TurnPanel: React.FC<TurnPanelProps> = (props) => {
  const { view, me } = props;
  const owed = view.discards_owed[me.id] ?? 0;

  if (view.phase === "game_over") {
    return (
      <Prompt>
        {view.winner_id === me.id
          ? "You won! 🎉"
          : `${playerName(view, view.winner_id)} won the game.`}
      </Prompt>
    );
  }
  if (owed > 0) return <DiscardForm {...props} owed={owed} />;
  if (view.phase === "discard") {
    return <Waiting view={view} what="to discard" />;
  }
  if (view.trade_offer) {
    return <TradeOfferPanel {...props} offer={view.trade_offer} />;
  }
  if (view.current_player_id !== me.id || view.legal_actions.length === 0) {
    return <Waiting view={view} />;
  }

  switch (view.phase) {
    case "setup_settlement":
      return <Prompt>Click a highlighted spot to place a settlement.</Prompt>;
    case "setup_road":
      return <Prompt>Click a highlighted edge to place a road.</Prompt>;
    case "road_building":
      return (
        <Prompt>
          Place {view.free_roads} free road{view.free_roads === 1 ? "" : "s"} on
          the highlighted edges.
        </Prompt>
      );
    case "move_robber":
      return <RobberPrompt {...props} />;
    case "roll":
      return <RollActions {...props} />;
    default:
      return <MainActions {...props} />;
  }
};

const Prompt: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <p className="text-sm">{children}</p>
);

const Waiting: React.FC<{ view: GameView; what?: string }> = ({
  view,
  what,
}) => {
  const names = view.waiting_on.map((id) => playerName(view, id));
  return (
    <p className="text-sm text-muted-foreground">
      Waiting for {names.join(", ") || "the next move"}
      {what ? ` ${what}` : ""}…
    </p>
  );
};

const RollActions: React.FC<TurnPanelProps> = ({ view, busy, act }) => {
  const knight = actionsOfType(view.legal_actions, "play_knight")[0];
  return (
    <div className="flex flex-wrap gap-2">
      <Button onClick={() => act({ type: "roll_dice" })} disabled={busy}>
        <Dices data-icon="inline-start" />
        Roll dice
      </Button>
      {knight && (
        <Button variant="outline" onClick={() => act(knight)} disabled={busy}>
          Play knight first
        </Button>
      )}
    </div>
  );
};

const RobberPrompt: React.FC<TurnPanelProps> = ({
  view,
  busy,
  act,
  robberHex,
  setRobberHex,
}) => {
  if (robberHex === null) {
    return (
      <Prompt>
        Click a highlighted hex to move the robber. You will steal a card from a
        player next to it.
      </Prompt>
    );
  }
  const moves = actionsOfType(view.legal_actions, "move_robber").filter(
    (a) => a.hex_id === robberHex,
  );
  return (
    <div className="flex flex-col gap-2">
      <Prompt>Who do you rob?</Prompt>
      <div className="flex flex-wrap gap-2">
        {moves.map((move) => (
          <Button
            key={move.victim_id ?? "none"}
            size="sm"
            disabled={busy}
            onClick={() => act(move)}
          >
            {playerName(view, move.victim_id)}
          </Button>
        ))}
        <Button size="sm" variant="ghost" onClick={() => setRobberHex(null)}>
          Pick another hex
        </Button>
      </div>
    </div>
  );
};

type Panel = "year_of_plenty" | "monopoly" | "bank" | "trade" | null;

const MainActions: React.FC<TurnPanelProps> = (props) => {
  const { view, busy, act, mode, setMode } = props;
  const [panel, setPanel] = useState<Panel>(null);
  const legal = view.legal_actions;

  const counts = {
    road: actionsOfType(legal, "build_road").length,
    settlement: actionsOfType(legal, "build_settlement").length,
    city: actionsOfType(legal, "build_city").length,
  };
  const buy = actionsOfType(legal, "buy_dev_card")[0];
  const knight = actionsOfType(legal, "play_knight")[0];
  const roadBuilding = actionsOfType(legal, "play_road_building")[0];
  const hasYearOfPlenty =
    actionsOfType(legal, "play_year_of_plenty").length > 0;
  const hasMonopoly = actionsOfType(legal, "play_monopoly").length > 0;
  const canBankTrade = actionsOfType(legal, "maritime_trade").length > 0;
  const canOffer = actionsOfType(legal, "propose_trade").length > 0;

  const toggle = (next: Panel) => setPanel(panel === next ? null : next);
  const run = async (action: Action) => {
    if (await act(action)) setPanel(null);
  };

  return (
    <div className="flex flex-col gap-3">
      <div>
        <SectionLabel>
          <Hammer className="size-3.5" /> Build
        </SectionLabel>
        <div className="grid grid-cols-2 gap-1.5">
          {(["road", "settlement", "city"] as const).map((kind) => (
            <Button
              key={kind}
              size="sm"
              variant={mode === kind ? "default" : "outline"}
              disabled={busy || counts[kind] === 0}
              onClick={() => setMode(mode === kind ? null : kind)}
              title={`Costs ${formatHand(COSTS[kind])}`}
            >
              {kind[0].toUpperCase() + kind.slice(1)}
            </Button>
          ))}
          <Button
            size="sm"
            variant="outline"
            disabled={busy || !buy}
            onClick={() => buy && act(buy)}
            title={`Costs ${formatHand(COSTS.dev)}`}
          >
            Dev card
          </Button>
        </div>
        {mode && (
          <p className="mt-1.5 text-xs text-muted-foreground">
            Click a highlighted spot on the board. Costs{" "}
            {formatHand(COSTS[mode])}.
          </p>
        )}
      </div>

      {(knight || roadBuilding || hasYearOfPlenty || hasMonopoly) && (
        <div>
          <SectionLabel>Play a development card</SectionLabel>
          <div className="flex flex-wrap gap-1.5">
            {knight && (
              <Button size="sm" variant="outline" onClick={() => run(knight)}>
                Knight
              </Button>
            )}
            {roadBuilding && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => run(roadBuilding)}
              >
                Road building
              </Button>
            )}
            {hasYearOfPlenty && (
              <Button
                size="sm"
                variant={panel === "year_of_plenty" ? "default" : "outline"}
                onClick={() => toggle("year_of_plenty")}
              >
                Year of plenty
              </Button>
            )}
            {hasMonopoly && (
              <Button
                size="sm"
                variant={panel === "monopoly" ? "default" : "outline"}
                onClick={() => toggle("monopoly")}
              >
                Monopoly
              </Button>
            )}
          </div>
        </div>
      )}

      <div>
        <SectionLabel>
          <Handshake className="size-3.5" /> Trade
        </SectionLabel>
        <div className="flex flex-wrap gap-1.5">
          <Button
            size="sm"
            variant={panel === "bank" ? "default" : "outline"}
            disabled={!canBankTrade}
            onClick={() => toggle("bank")}
          >
            <Landmark data-icon="inline-start" />
            With the bank
          </Button>
          <Button
            size="sm"
            variant={panel === "trade" ? "default" : "outline"}
            disabled={!canOffer}
            onClick={() => toggle("trade")}
          >
            With players ({view.trades_left} left)
          </Button>
        </div>
      </div>

      {panel === "year_of_plenty" && (
        <YearOfPlentyForm view={view} busy={busy} run={run} />
      )}
      {panel === "monopoly" && <MonopolyForm busy={busy} run={run} />}
      {panel === "bank" && <BankTradeForm {...props} run={run} />}
      {panel === "trade" && <OfferForm {...props} run={run} />}

      <Button
        className="mt-1"
        onClick={() => act({ type: "end_turn" })}
        disabled={busy}
      >
        <SkipForward data-icon="inline-start" />
        End turn
      </Button>
    </div>
  );
};

const SectionLabel: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => (
  <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium tracking-wide text-muted-foreground uppercase">
    {children}
  </div>
);

const SubPanel: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div className="flex flex-col gap-2.5 rounded-md border bg-muted/40 p-2.5">
    {children}
  </div>
);

type Run = (action: Action) => Promise<void>;

const YearOfPlentyForm: React.FC<{
  view: GameView;
  busy: boolean;
  run: Run;
}> = ({ view, busy, run }) => {
  const [pick, setPick] = useState<Hand>({});
  const chosen = RESOURCES.flatMap((r) =>
    Array.from({ length: pick[r] ?? 0 }, () => r),
  );
  const action = actionsOfType(view.legal_actions, "play_year_of_plenty").find(
    (a) =>
      chosen.length === 2 &&
      a.resources.toSorted().join() === chosen.toSorted().join(),
  );
  return (
    <SubPanel>
      <p className="text-xs text-muted-foreground">
        Take any two resources from the bank.
      </p>
      <ResourcePicker
        value={pick}
        onChange={setPick}
        max={view.bank}
        totalMax={2}
      />
      <Button
        size="sm"
        disabled={busy || !action}
        onClick={() => action && run(action)}
      >
        Take {formatHand(pick)}
      </Button>
    </SubPanel>
  );
};

const MonopolyForm: React.FC<{ busy: boolean; run: Run }> = ({ busy, run }) => {
  const [resource, setResource] = useState<Resource | null>(null);
  return (
    <SubPanel>
      <p className="text-xs text-muted-foreground">
        Every other player hands you all of one resource.
      </p>
      <ResourceChoice
        options={RESOURCES}
        value={resource}
        onChange={setResource}
      />
      <Button
        size="sm"
        disabled={busy || !resource}
        onClick={() => resource && run({ type: "play_monopoly", resource })}
      >
        Claim all {resource ?? "…"}
      </Button>
    </SubPanel>
  );
};

const BankTradeForm: React.FC<TurnPanelProps & { run: Run }> = ({
  view,
  busy,
  run,
}) => {
  const [give, setGive] = useState<Resource | null>(null);
  const [receive, setReceive] = useState<Resource | null>(null);
  const trades = actionsOfType(view.legal_actions, "maritime_trade");
  const giveOptions = RESOURCES.filter((r) => trades.some((t) => t.give === r));
  const receiveOptions = RESOURCES.filter((r) =>
    trades.some((t) => t.give === give && t.receive === r),
  );
  const action = trades.find((t) => t.give === give && t.receive === receive);
  const me = view.players.find((p) => p.id === view.viewer_id);
  const rate = (r: Resource) => ` ${me?.trade_ratios?.[r] ?? 4}:1`;

  return (
    <SubPanel>
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground">Give</span>
        <ResourceChoice
          options={giveOptions}
          value={give}
          onChange={(r) => {
            setGive(r);
            if (r === receive) setReceive(null);
          }}
          suffix={rate}
        />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground">Receive 1</span>
        <ResourceChoice
          options={receiveOptions}
          value={receive}
          onChange={setReceive}
        />
      </div>
      <Button
        size="sm"
        disabled={busy || !action}
        onClick={() => action && run(action)}
      >
        Trade with the bank
      </Button>
    </SubPanel>
  );
};

const OfferForm: React.FC<TurnPanelProps & { run: Run }> = ({
  view,
  me,
  busy,
  run,
}) => {
  const [give, setGive] = useState<Hand>({});
  const [receive, setReceive] = useState<Hand>({});
  const overlap = RESOURCES.some((r) => (give[r] ?? 0) && (receive[r] ?? 0));
  const valid =
    handTotal(give) > 0 && handTotal(receive) > 0 && !overlap && !busy;

  return (
    <SubPanel>
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground">You give</span>
        <ResourcePicker
          value={give}
          onChange={setGive}
          max={me.resources ?? {}}
        />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted-foreground">You want</span>
        <ResourcePicker value={receive} onChange={setReceive} />
      </div>
      {overlap && (
        <p className="text-xs text-destructive">
          Don’t give and ask for the same resource.
        </p>
      )}
      <Button
        size="sm"
        disabled={!valid || view.trades_left === 0}
        onClick={() => run({ type: "propose_trade", give, receive })}
      >
        Offer to the table
      </Button>
    </SubPanel>
  );
};

const TradeOfferPanel: React.FC<TurnPanelProps & { offer: TradeOffer }> = ({
  view,
  me,
  busy,
  act,
  offer,
}) => {
  const proposer = playerName(view, offer.proposer_id);
  const accepted = offer.accepted ?? [];
  const rejected = offer.rejected ?? [];
  const legal = view.legal_actions;
  const canAccept = actionsOfType(legal, "respond_trade").some((a) => a.accept);
  const mine = offer.proposer_id === me.id;

  return (
    <div className="flex flex-col gap-2.5">
      <p className="text-sm">
        {mine ? "You offer" : `${proposer} offers`}{" "}
        <strong>{formatHand(offer.give)}</strong> for{" "}
        <strong>{formatHand(offer.receive)}</strong>.
      </p>
      {mine ? (
        <>
          <ul className="flex flex-col gap-1 text-sm">
            {view.players
              .filter((p) => p.id !== me.id)
              .map((p) => (
                <li key={p.id} className="flex items-center gap-2">
                  <span className="flex-1 truncate">{p.name}</span>
                  {accepted.includes(p.id) ? (
                    <Button
                      size="xs"
                      disabled={busy}
                      onClick={() =>
                        act({ type: "confirm_trade", partner_id: p.id })
                      }
                    >
                      Trade with {p.name}
                    </Button>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      {rejected.includes(p.id) ? "declined" : "thinking…"}
                    </span>
                  )}
                </li>
              ))}
          </ul>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => act({ type: "cancel_trade" })}
          >
            Withdraw offer
          </Button>
        </>
      ) : accepted.includes(me.id) || rejected.includes(me.id) ? (
        <p className="text-sm text-muted-foreground">
          You {accepted.includes(me.id) ? "accepted" : "declined"}. Waiting for{" "}
          {proposer}…
        </p>
      ) : (
        <div className="flex gap-2">
          <Button
            size="sm"
            disabled={busy || !canAccept}
            title={canAccept ? undefined : "You don’t have those cards"}
            onClick={() => act({ type: "respond_trade", accept: true })}
          >
            Accept
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => act({ type: "respond_trade", accept: false })}
          >
            Decline
          </Button>
        </div>
      )}
    </div>
  );
};

const DiscardForm: React.FC<TurnPanelProps & { owed: number }> = ({
  me,
  busy,
  act,
  owed,
}) => {
  const [pick, setPick] = useState<Hand>({});
  const picked = handTotal(pick);
  return (
    <div className="flex flex-col gap-2.5">
      <Prompt>
        A 7 was rolled and you hold more than 7 cards. Discard {owed}.
      </Prompt>
      <ResourcePicker
        value={pick}
        onChange={setPick}
        max={me.resources ?? {}}
        totalMax={owed}
      />
      <Button
        size="sm"
        disabled={busy || picked !== owed}
        onClick={async () => {
          if (await act({ type: "discard", resources: pick })) setPick({});
        }}
      >
        Discard {picked}/{owed}
      </Button>
    </div>
  );
};
