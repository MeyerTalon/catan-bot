/**
 * Minimal hash routing: `#/games/<id>` opens a game, anything else is the
 * lobby. Hash URLs need no server rewrites and can be shared as invite links.
 */

import { useEffect, useState } from "react";

export type Route = { name: "lobby" } | { name: "game"; gameId: number };

function parse(hash: string): Route {
  const match = /^#\/games\/(\d+)$/.exec(hash);
  return match ? { name: "game", gameId: Number(match[1]) } : { name: "lobby" };
}

export function useRoute(): Route {
  const [route, setRoute] = useState(() => parse(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parse(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}

export function gameHref(gameId: number): string {
  return `#/games/${gameId}`;
}

export function goToGame(gameId: number): void {
  window.location.hash = gameHref(gameId);
}

export function goToLobby(): void {
  window.location.hash = "";
}
