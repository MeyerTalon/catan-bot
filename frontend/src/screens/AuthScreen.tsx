import React, { useState } from "react";
import { LoginScreen } from "./LoginScreen";
import { SignUpScreen } from "./SignUpScreen";

type View = "landing" | "login" | "signup";

export const AuthScreen: React.FC = () => {
  const [view, setView] = useState<View>("landing");

  if (view === "login") {
    return (
      <LoginScreen
        onSwitchToSignUp={() => setView("signup")}
        onBack={() => setView("landing")}
      />
    );
  }

  if (view === "signup") {
    return (
      <SignUpScreen
        onSwitchToLogin={() => setView("login")}
        onBack={() => setView("landing")}
      />
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center catan-bg">
      <div className="landing-card">
        <h1 className="landing-title">Catan Online</h1>
        <p className="landing-subtitle">
          Build, trade, and settle the island of Catan with smart AI opponents.
        </p>

        <button
          type="button"
          className="landing-play-button"
          onClick={() => setView("login")}
        >
          Log in
        </button>
        <button
          type="button"
          className="landing-play-button landing-play-button-secondary"
          onClick={() => setView("signup")}
        >
          Sign up
        </button>

        <p className="landing-hint">Create an account or log in to play.</p>
      </div>
    </div>
  );
};
