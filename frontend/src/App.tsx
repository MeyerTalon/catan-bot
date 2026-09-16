import React, { useEffect, useState } from "react";
import { getSession, subscribeToSession } from "./lib/session";
import { AuthScreen } from "./screens/AuthScreen";
import { GameScreen } from "./screens/GameScreen";

export const App: React.FC = () => {
  const [session, setSessionState] = useState(() => getSession());

  useEffect(() => {
    return subscribeToSession(() => setSessionState(getSession()));
  }, []);

  if (session?.access_token) {
    return <GameScreen />;
  }

  return <AuthScreen />;
};
