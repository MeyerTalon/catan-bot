import React, { useState } from "react";
import { supabase } from "../lib/supabaseClient";

export const GameScreen: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const handleLogout = async () => {
    setLoading(true);
    try {
      await supabase.auth.signOut();
      // onAuthStateChange in App.tsx will handle redirect to AuthScreen
    } catch (err) {
      console.error("Logout failed:", err);
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center catan-bg">
      <div className="game-screen-card">
        <button
          type="button"
          onClick={handleLogout}
          className="logout-button"
          disabled={loading}
          aria-label="Log out"
        >
          {loading ? "LOGGING OUT..." : "DISCONNECT"}
        </button>
        <div className="under-construction-banner">Under Construction</div>
        <p className="game-screen-message">
          The Catan game is coming soon. Check back later!
        </p>
      </div>
    </div>
  );
};
