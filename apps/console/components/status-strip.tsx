"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { AnimatedStat } from "@/components/animated-stat";
import { cn } from "@/lib/utils";

const CONN_LABEL = {
  connecting: "connecting",
  live: "live",
  reconnecting: "reconnecting",
  offline: "offline",
} as const;

const CONN_DOT = {
  connecting: "bg-warn animate-pulse",
  live: "bg-ok",
  reconnecting: "bg-warn animate-pulse",
  offline: "bg-danger",
};

/** Live dashboard counters — via global WS + fallback poll. */
export function StatusStrip({ compact }: { compact?: boolean }) {
  const { tick, connection } = useGlobalWs();
  const [s, setS] = useState<{
    rooms?: { open?: number; total?: number };
    approvals_pending?: number;
    engaged?: number;
    verified?: number;
    presence?: { agents?: number };
    funnel?: { approve?: number; learn?: number };
    workspace?: { connected?: boolean };
  } | null>(null);
  const prev = useRef<{ waiting?: number; open?: number }>({});

  useEffect(() => {
    api
      .status()
      .then(setS)
      .catch(() => setS(null));
  }, [tick]);

  if (!s) return null;

  const open = s.rooms?.open ?? 0;
  const waiting = s.approvals_pending ?? s.funnel?.approve ?? 0;
  const flashWaiting = waiting !== prev.current.waiting;
  const flashOpen = open !== prev.current.open;
  prev.current = { waiting, open };

  const shortLabels: Record<string, string> = {
    "Open investigations": "Open",
    "Waiting on you": "You",
    "In flight": "Flight",
    Verified: "Done",
    "Agents live": "Agents",
    Lessons: "Learn",
    Workspace: "Wire",
  };

  const stats = [
    { label: "Open investigations", value: open, flash: flashOpen },
    { label: "Waiting on you", value: waiting, hot: waiting > 0, flash: flashWaiting },
    { label: "In flight", value: s.engaged ?? 0 },
    ...(compact
      ? []
      : [
          { label: "Verified", value: s.verified ?? 0 },
          { label: "Agents live", value: s.presence?.agents ?? 0 },
          { label: "Lessons", value: s.funnel?.learn ?? 0 },
          { label: "Workspace", value: s.workspace?.connected ? "on" : "off" },
        ]),
  ];

  if (compact) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${CONN_DOT[connection]}`} title={CONN_LABEL[connection]} />
        {stats.map((st) => (
          <span
            key={st.label}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-2.5 py-1 text-[12px]",
              st.hot && "border-accent/40 text-accent"
            )}
          >
            <span className="text-[var(--faint)]">{shortLabels[st.label] || st.label}</span>
            <span className="font-semibold text-foreground">{st.value}</span>
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-3">
      <div className="flex items-center gap-2 pt-1">
        <span className={`h-2 w-2 rounded-full ${CONN_DOT[connection]}`} title={CONN_LABEL[connection]} />
        <span className="text-[11px] text-[var(--faint)]">{CONN_LABEL[connection]}</span>
      </div>
      <AnimatedStat label="Open investigations" value={open} flash={flashOpen} />
      <AnimatedStat label="Waiting on you" value={waiting} hot={waiting > 0} flash={flashWaiting} />
      <AnimatedStat label="In flight" value={s.engaged ?? 0} />
      <AnimatedStat label="Verified" value={s.verified ?? 0} />
      <AnimatedStat label="Agents live" value={s.presence?.agents ?? 0} />
      <AnimatedStat label="Lessons" value={s.funnel?.learn ?? 0} />
      <AnimatedStat label="Workspace" value={s.workspace?.connected ? "on" : "off"} />
    </div>
  );
}
