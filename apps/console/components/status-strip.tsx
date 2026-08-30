"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/** SalesShortcut dashboard counters — light pulse, not a CRUD board. */
export function StatusStrip() {
  const [s, setS] = useState<{
    rooms?: { open?: number; total?: number };
    approvals_pending?: number;
    presence?: { agents?: number };
    funnel?: { approve?: number; learn?: number };
    workspace?: { connected?: boolean };
  } | null>(null);

  useEffect(() => {
    api
      .status()
      .then(setS)
      .catch(() => setS(null));
    const id = window.setInterval(() => {
      api.status().then(setS).catch(() => undefined);
    }, 12000);
    return () => window.clearInterval(id);
  }, []);

  if (!s) return null;

  const cells = [
    { label: "Open rooms", value: s.rooms?.open ?? 0 },
    { label: "Waiting on you", value: s.approvals_pending ?? s.funnel?.approve ?? 0 },
    { label: "Agents live", value: s.presence?.agents ?? 0 },
    { label: "Lessons", value: s.funnel?.learn ?? 0 },
    { label: "Workspace", value: s.workspace?.connected ? "on" : "off" },
  ];

  return (
    <div className="flex flex-wrap gap-x-6 gap-y-2">
      {cells.map((c) => (
        <div key={c.label} className="min-w-[4.5rem]">
          <p className="text-[11px] text-[var(--faint)]">{c.label}</p>
          <p className="text-[15px] font-semibold tracking-tight text-foreground">{c.value}</p>
        </div>
      ))}
    </div>
  );
}
