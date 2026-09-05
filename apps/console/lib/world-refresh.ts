"use client";

import { useEffect, useRef, useState } from "react";

/** Minimum gap between light list refetches driven by WS ticks (rooms). */
export const WORLD_REFRESH_MS = 45_000;

/** Heavier endpoints (office, status, proof) — avoid hammering 2Gi Cloud Run. */
export const WORLD_SLOW_REFRESH_MS = 90_000;

/**
 * Coalesce rapid WS ticks so list/office/status endpoints are not refetched on
 * every event. The first tick value is passed through immediately (mount).
 */
export function useDebouncedWorldTick(tick: number, delayMs = WORLD_REFRESH_MS): number {
  const [debounced, setDebounced] = useState(tick);
  const primed = useRef(false);

  useEffect(() => {
    if (!primed.current) {
      primed.current = true;
      setDebounced(tick);
      return;
    }
    const t = window.setTimeout(() => setDebounced(tick), delayMs);
    return () => clearTimeout(t);
  }, [tick, delayMs]);

  return debounced;
}

/** Debounced WS tick for office / status / glass-box — half the poll rate of rooms. */
export function useSlowWorldTick(tick: number): number {
  return useDebouncedWorldTick(tick, WORLD_SLOW_REFRESH_MS);
}
