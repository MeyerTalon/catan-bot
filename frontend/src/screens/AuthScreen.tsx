import React from "react";

export const AuthScreen: React.FC = () => {
  const handlePlayClick = () => {
    // Placeholder – later this can navigate to auth or game lobby.
    // For now it just logs so you can see the click is working.
    // eslint-disable-next-line no-console
    console.log("Play Catan clicked");
  };

  return (
    <div className="min-h-screen flex items-center justify-center catan-bg">
      <div className="landing-card">
        <h1 className="landing-title">Catan Online</h1>
        <p className="landing-subtitle">
          Build, trade, and settle the island of Catan with smart AI opponents.
        </p>

        <button type="button" className="landing-play-button" onClick={handlePlayClick}>
          Play Catan
        </button>

        <p className="landing-hint">Sign in and game screens coming next.</p>
      </div>
    </div>
  );
};
