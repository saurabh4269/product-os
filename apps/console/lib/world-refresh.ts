"use client";

import { useEffect, useRef, useState } from "react";

/** Minimum gap between light list refetches driven by WS ticks (rooms). */
export const WORLD_REFRESH_MS = 60_000;

/** Heavier endpoints (office, status, proof) — avoid hammering 2Gi Cloud Run. */
export const WORLD_SLOW_REFRESH_MS = 120_000;

/** When /ws is live, events already push — stretch HTTP fallback further. */
export const WORLD_REFRESH_WS_LIVE_MS = 90_000;
export const WORLD_SLOW_REFRESH_WS_LIVE_MS = 180_000;

/** Skip HTTP polls while the tab is in the background (saves 2Gi host RAM). */
export function useWorldPollEnabled(): boolean {
  const [enabled, setEnabled] = useState(
    () => typeof document === "undefined" || document.visibilityState !== "hidden"
  );

  useEffect(() => {
    const sync = () => setEnabled(document.visibilityState !== "hidden");
    sync();
    document.addEventListener("visibilitychange", sync);
    return () => document.removeEventListener("visibilitychange", sync);
  }, []);

  return enabled;
}

/**
 * Coalesce rapid WS ticks so list/office/status endpoints are not refetched on
 * every event. The first tick value is passed through immediately (mount).
 */
export function useDebouncedWorldTick(
  tick: number,
  delayMs = WORLD_REFRESH_MS,
  wsLive = false
): number {
  const effective = wsLive ? Math.max(delayMs, WORLD_REFRESH_WS_LIVE_MS) : delayMs;
  const [debounced, setDebounced] = useState(tick);
  const primed = useRef(false);

  useEffect(() => {
    if (!primed.current) {
      primed.current = true;
      setDebounced(tick);
      return;
    }
    const t = window.setTimeout(() => setDebounced(tick), effective);
    return () => clearTimeout(t);
  }, [tick, effective]);

  return debounced;
}

/** Debounced WS tick for office / status / glass-box — slower than rooms. */
export function useSlowWorldTick(tick: number, wsLive = false): number {
  const delayMs = wsLive ? WORLD_SLOW_REFRESH_WS_LIVE_MS : WORLD_SLOW_REFRESH_MS;
  return useDebouncedWorldTick(tick, delayMs, wsLive);
}
