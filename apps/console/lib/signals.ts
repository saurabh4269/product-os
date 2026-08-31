/** Dedupe signal cards for display — same metric+segment shows once. */
export function dedupeSignals<T extends Record<string, unknown>>(signals: T[]): T[] {
  const best = new Map<string, T>();
  for (const s of signals) {
    const metric = String(s.metric ?? "");
    const segs =
      (s.affected_segments as Array<{ browser?: string; os?: string; platform?: string; geo?: string }>) ?? [];
    const seg = segs[0];
    const key = [metric, seg?.browser ?? "", seg?.os ?? "", seg?.platform ?? "", seg?.geo ?? ""].join("|");
    const prev = best.get(key);
    if (!prev) {
      best.set(key, s);
      continue;
    }
    const prevAt = String(prev.detected_at ?? "");
    const curAt = String(s.detected_at ?? "");
    if (curAt >= prevAt) best.set(key, s);
  }
  return [...best.values()];
}

export function signalSegmentLabel(s: Record<string, unknown>) {
  const segs =
    (s.affected_segments as Array<{ browser?: string; os?: string; platform?: string; geo?: string }>) ?? [];
  const seg = segs[0];
  return seg?.browser || seg?.os || seg?.platform || seg?.geo || "all";
}
