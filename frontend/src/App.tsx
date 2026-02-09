import React, { useEffect, useState } from "react";
import { Session } from "@supabase/supabase-js";
import { supabase } from "./lib/supabaseClient";
import { AuthScreen } from "./screens/AuthScreen";
import { GameScreen } from "./screens/GameScreen";

export const App: React.FC = () => {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center catan-bg">
        <p className="auth-subtitle">Loading…</p>
      </div>
    );
  }

  if (session) {
    return <GameScreen />;
  }

  return <AuthScreen />;
};
