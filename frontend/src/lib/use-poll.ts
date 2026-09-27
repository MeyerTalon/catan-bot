import { useEffect, useRef } from "react";

/**
 * Calls `tick` now and then every `intervalMs` while the tab is visible.
 * The latest `tick` is always used, so callers need not memoise it.
 */
export function usePoll(tick: () => void, intervalMs: number): void {
  const latest = useRef(tick);
  useEffect(() => {
    latest.current = tick;
  });

  useEffect(() => {
    const run = () => {
      if (document.visibilityState === "visible") latest.current();
    };
    run();
    const id = window.setInterval(run, intervalMs);
    document.addEventListener("visibilitychange", run);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", run);
    };
  }, [intervalMs]);
}
