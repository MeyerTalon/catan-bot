import React, { useState } from "react";
import { HexMark } from "@/components/hex-mark";
import { Button } from "@/components/ui/button";
import { ConfirmScreen } from "./ConfirmScreen";
import { LoginScreen } from "./LoginScreen";
import { SignUpScreen } from "./SignUpScreen";

type View = "landing" | "login" | "signup" | "confirm";

export const AuthScreen: React.FC = () => {
  const [view, setView] = useState<View>("landing");
  const [pendingEmail, setPendingEmail] = useState("");

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
        onConfirmationRequired={(email) => {
          setPendingEmail(email);
          setView("confirm");
        }}
        onBack={() => setView("landing")}
      />
    );
  }

  if (view === "confirm") {
    return (
      <ConfirmScreen
        email={pendingEmail}
        onConfirmed={() => setView("login")}
        onBack={() => setView("signup")}
      />
    );
  }

  return (
    <div className="flex min-h-screen items-center px-6 py-16">
      <div className="mx-auto w-full max-w-3xl">
        <HexMark className="mb-6 text-primary" />
        <h1 className="text-5xl font-bold tracking-tight">Catan</h1>
        <p className="mt-3 max-w-md text-lg text-muted-foreground">
          Build, trade, and settle the island against AI opponents.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Button size="lg" onClick={() => setView("login")}>
            Log in
          </Button>
          <Button size="lg" variant="outline" onClick={() => setView("signup")}>
            Create account
          </Button>
        </div>
      </div>
    </div>
  );
};
