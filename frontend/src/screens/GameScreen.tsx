import React, { useState } from "react";
import { clearSession } from "../lib/session";

export const GameScreen: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const handleLogout = () => {
    setLoading(true);
    clearSession();
  };

  return (
    <div className="min-h-screen flex items-center justify-center catan-bg">
      <div className="game-screen-card">
        <div className="under-construction-banner">Under Construction</div>
        <p className="game-screen-message">
          The Catan game is coming soon. Check back later!
        </p>
        <button
          type="button"
          onClick={handleLogout}
          className="logout-button"
          disabled={loading}
          aria-label="Log out"
        >
          {loading ? "LOGGING OUT..." : "DISCONNECT"}
        </button>
      </div>
    </div>
  );
};
