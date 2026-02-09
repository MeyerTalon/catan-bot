import React from "react";

export const GameScreen: React.FC = () => {
  return (
    <div className="min-h-screen flex items-center justify-center catan-bg">
      <div className="game-screen-card">
        <div className="under-construction-banner">Under Construction</div>
        <p className="game-screen-message">
          The Catan game is coming soon. Check back later!
        </p>
      </div>
    </div>
  );
};
