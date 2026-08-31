export const DISTRICTS = ["Incidents", "Ideas", "Reviews", "Research", "Ops", "Office"] as const;
export type District = (typeof DISTRICTS)[number];

/** Pin / building centers as % of the 1350×900 campus image box. */
export const SLOTS: Record<string, { x: number; y: number }> = {
  Incidents: { x: 24, y: 48 },
  Ideas: { x: 50, y: 56 },
  Reviews: { x: 40, y: 42 },
  Research: { x: 84, y: 42 },
  Ops: { x: 72, y: 44 },
  Office: { x: 48, y: 52 },
};

export const LANDMARKS = [
  { href: "/memory", label: "Memory", x: 28, y: 72 },
  { href: "/approvals", label: "Approvals", x: 50, y: 80 },
] as const;

/** Clickable building footprints — ellipses in image-box %. */
export const BUILDINGS = [
  { id: "Incidents", label: "Incidents", x: 22, y: 46, rx: 9, ry: 8 },
  { id: "Reviews", label: "Reviews", x: 39, y: 40, rx: 7.5, ry: 7 },
  { id: "Ideas", label: "Ideas", x: 51, y: 54, rx: 8.5, ry: 7.5 },
  { id: "Ops", label: "Ops", x: 69, y: 42, rx: 8, ry: 7 },
  { id: "Research", label: "Research", x: 84, y: 40, rx: 8.5, ry: 8 },
] as const;

export function districtOf(title: string | null | undefined, fallback: District = "Ops"): District {
  const t = (title || "").toLowerCase();
  if (t.includes("safari") || t.includes("3ds") || t.includes("timeout") || t.includes("denied")) return "Incidents";
  if (t.includes("review") || t.includes("activation") || t.includes("onboarding")) return "Reviews";
  if (t.includes("research")) return "Research";
  if (t.includes("android") || t.includes("apple pay") || t.includes("shipping")) return "Ideas";
  if (DISTRICTS.includes(fallback)) return fallback;
  return "Ops";
}

export function slotFor<T extends { district?: string | null; room_id?: string | null; room_title?: string | null }>(
  desk: T | undefined,
  rooms: Array<{ id: string; title: string }>
) {
  if (desk?.district && SLOTS[desk.district]) return SLOTS[desk.district];
  const room = rooms.find((r) => r.id === desk?.room_id);
  return SLOTS[districtOf(room?.title ?? desk?.room_title, "Ops")] || SLOTS.Ops;
}

export type RoomCluster<T> = { key: string; people: T[]; x: number; y: number };

export function cluster<T extends { district?: string | null; room_id?: string | null; room_title?: string | null }>(
  desks: T[],
  rooms: Array<{ id: string; title: string }>
): RoomCluster<T>[] {
  const groups = new Map<string, T[]>();
  for (const d of desks) {
    if (!d.room_id) continue;
    groups.set(d.room_id, [...(groups.get(d.room_id) || []), d]);
  }
  const raw = [...groups.entries()].map(([key, people]) => {
    const s = slotFor(people[0], rooms);
    return { key, people, x: s.x, y: s.y };
  });
  const bySlot = new Map<string, typeof raw>();
  for (const g of raw) {
    const k = `${g.x}:${g.y}`;
    bySlot.set(k, [...(bySlot.get(k) || []), g]);
  }
  for (const list of bySlot.values()) {
    const n = list.length;
    list.forEach((g, i) => {
      const spread = (i - (n - 1) / 2) * 5.2;
      g.x += spread;
      g.y += Math.abs(spread) * 0.18;
    });
  }
  return raw;
}

export type DistrictPod<T> = {
  id: District;
  x: number;
  y: number;
  working: T[];
  total: T[];
};

/** Working agents grouped by district — for campus building overlays. */
export function districtPods<T extends { id: string; district?: string | null; status?: string }>(
  desks: T[]
): DistrictPod<T>[] {
  return DISTRICTS.map((id) => {
    const slot = SLOTS[id] ?? SLOTS.Office;
    const total = desks.filter((d) => d.district === id);
    const working = total.filter((d) => d.status && d.status !== "idle");
    return { id, x: slot.x, y: slot.y - 4, working, total };
  }).filter((p) => p.working.length > 0);
}

export function busiestRoom<T extends { room_id?: string | null; district?: string | null }>(
  district: string,
  desks: T[],
  rooms: Array<{ id: string; title?: string | null; kind?: string }>
) {
  const inDistrict = desks.filter((d) => d.district === district && d.room_id);
  const counts = new Map<string, number>();
  for (const d of inDistrict) counts.set(d.room_id as string, (counts.get(d.room_id as string) || 0) + 1);
  let best = rooms.find((r) => inDistrict.some((d) => d.room_id === r.id))?.id ?? null;
  let n = 0;
  for (const [id, c] of counts) {
    if (c > n) {
      n = c;
      best = id;
    }
  }
  return best;
}
