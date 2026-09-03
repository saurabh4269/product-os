"use client";

import { useEffect, useRef, useState } from "react";

/** Minimum gap between world-list refetches driven by WS ticks. */
export const WORLD_REFRESH_MS = 15_000;

/**
 * Coalesce rapid WS ticks so list/office/status endpoints are not refetched on
 * every event. The first tick value is passed through immediately (mount).
 */
export function useDebouncedWorldTick(tick: number): number {
  const [debounced, setDebounced] = useState(tick);
  const primed = useRef(false);

  useEffect(() => {
    if (!primed.current) {
      primed.current = true;
      setDebounced(tick);
      return;
    }
    const t = window.setTimeout(() => setDebounced(tick), WORLD_REFRESH_MS);
    return () => clearTimeout(t);
  }, [tick]);

  return debounced;
}
