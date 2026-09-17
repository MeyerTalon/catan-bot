import React, { useState } from "react";
import { LogOut } from "lucide-react";
import { HexMark } from "@/components/hex-mark";
import { Button } from "@/components/ui/button";
import { clearSession } from "@/lib/session";

export const GameScreen: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const handleLogout = () => {
    setLoading(true);
    clearSession();
  };

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-2 font-heading font-semibold">
          <HexMark className="size-5 text-primary" />
          Catan
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          disabled={loading}
        >
          <LogOut data-icon="inline-start" />
          {loading ? "Logging out…" : "Log out"}
        </Button>
      </header>
      <main className="flex flex-1 items-center justify-center px-6 py-16">
        <div className="max-w-md text-center">
          <h1 className="text-2xl font-semibold">The board is coming soon</h1>
          <p className="mt-2 text-muted-foreground">
            You’re logged in. The game screen is still under construction —
            check back later.
          </p>
        </div>
      </main>
    </div>
  );
};
