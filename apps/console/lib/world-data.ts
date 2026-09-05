"use client";

import { api, type OfficeSnapshot, type Room } from "@/lib/api";
import { WORLD_REFRESH_MS, WORLD_SLOW_REFRESH_MS } from "@/lib/world-refresh";

export type WorldStatus = Awaited<ReturnType<typeof api.status>>;

export type WorldGlass = {
  proofs: Awaited<ReturnType<typeof api.proof>>;
  liveWork: Awaited<ReturnType<typeof api.liveWork>>;
};

type Cache<T> = {
  value: T | null;
  fetchedAt: number;
  inflight: Promise<T> | null;
};

function createCache<T>(): Cache<T> {
  return { value: null, fetchedAt: 0, inflight: null };
}

const roomsCache = createCache<Room[]>();
const officeCache = createCache<OfficeSnapshot>();
const statusCache = createCache<WorldStatus>();
const glassCache = createCache<WorldGlass>();

async function cachedFetch<T>(cache: Cache<T>, ttlMs: number, fetcher: () => Promise<T>): Promise<T> {
  const now = Date.now();
  if (cache.value !== null && now - cache.fetchedAt < ttlMs) {
    return cache.value;
  }
  if (cache.inflight) return cache.inflight;
  cache.inflight = fetcher()
    .then((value) => {
      cache.value = value;
      cache.fetchedAt = Date.now();
      cache.inflight = null;
      return value;
    })
    .catch((err) => {
      cache.inflight = null;
      throw err;
    });
  return cache.inflight;
}

/** Coalesced GET /api/rooms — one in-flight request per debounce window. */
export function fetchWorldRooms(): Promise<Room[]> {
  return cachedFetch(roomsCache, WORLD_REFRESH_MS, async () => {
    const r = await api.rooms();
    return r.rooms;
  });
}

/** Coalesced GET /api/office. */
export function fetchWorldOffice(): Promise<OfficeSnapshot> {
  return cachedFetch(officeCache, WORLD_SLOW_REFRESH_MS, () => api.office());
}

/** Coalesced GET /api/status. */
export function fetchWorldStatus(): Promise<WorldStatus> {
  return cachedFetch(statusCache, WORLD_SLOW_REFRESH_MS, () => api.status());
}

/** Coalesced proof + live-work pair (home glass box). */
export function fetchWorldGlass(): Promise<WorldGlass> {
  return cachedFetch(glassCache, WORLD_SLOW_REFRESH_MS, async () => {
    const [proofs, liveWork] = await Promise.all([api.proof(), api.liveWork()]);
    return { proofs, liveWork };
  });
}

/** Drop cached snapshots after navigation mutations (optional). */
export function invalidateWorldCache(): void {
  for (const cache of [roomsCache, officeCache, statusCache, glassCache]) {
    cache.value = null;
    cache.fetchedAt = 0;
    cache.inflight = null;
  }
}
