import React, { useEffect, useState } from "react";
import { getSession, subscribeToSession } from "./lib/session";
import { useRoute } from "./lib/route";
import { AuthScreen } from "./screens/AuthScreen";
import { GameRoomScreen } from "./screens/GameRoomScreen";
import { LobbyScreen } from "./screens/LobbyScreen";

export const App: React.FC = () => {
  const [session, setSessionState] = useState(() => getSession());
  const route = useRoute();

  useEffect(() => {
    return subscribeToSession(() => setSessionState(getSession()));
  }, []);

  if (!session?.access_token) {
    return <AuthScreen />;
  }

  if (route.name === "game") {
    return <GameRoomScreen key={route.gameId} gameId={route.gameId} />;
  }

  return <LobbyScreen />;
};
