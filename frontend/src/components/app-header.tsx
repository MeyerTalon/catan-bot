import React, { useState } from "react";
import { LogOut } from "lucide-react";
import { api } from "@/api/client";
import { HexMark } from "@/components/hex-mark";
import { Button } from "@/components/ui/button";
import { goToLobby } from "@/lib/route";
import { clearSession, getSession } from "@/lib/session";

type AppHeaderProps = {
  children?: React.ReactNode;
};

/** Top bar with the logo (back to the lobby), optional extras, and log out. */
export const AppHeader: React.FC<AppHeaderProps> = ({ children }) => {
  const [loggingOut, setLoggingOut] = useState(false);

  const handleLogout = async () => {
    setLoggingOut(true);
    const refreshToken = getSession()?.refresh_token;
    if (refreshToken) {
      // best effort: the local session is cleared either way
      await api
        .POST("/auth/logout", { body: { refresh_token: refreshToken } })
        .catch(() => undefined);
    }
    goToLobby();
    clearSession();
  };

  return (
    <header className="flex items-center justify-between gap-3 border-b px-4 py-2.5 sm:px-6">
      <button
        type="button"
        onClick={goToLobby}
        className="flex items-center gap-2 font-heading font-semibold"
      >
        <HexMark className="size-5 text-primary" />
        Catan
      </button>
      <div className="flex min-w-0 items-center gap-2">
        {children}
        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          disabled={loggingOut}
        >
          <LogOut data-icon="inline-start" />
          {loggingOut ? "Logging out…" : "Log out"}
        </Button>
      </div>
    </header>
  );
};
