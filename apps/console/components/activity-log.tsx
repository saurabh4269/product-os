"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useGlobalWs, type ActivityEvent } from "@/lib/use-global-ws";
import { shortName } from "@/lib/names";
import { cn } from "@/lib/utils";
import { AgentBadge } from "@/components/agent-badge";

function relTime(ts?: string) {
  if (!ts) return "";
  const t = new Date(ts).getTime();
  if (Number.isNaN(t)) return "";
  const sec = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (sec < 8) return "just now";
  if (sec < 60) return `${sec}s ago`;
  const m = Math.floor(sec / 60);
  if (m < 60) return `${m}m ago`;
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function Row({ e, fresh, hideRoom }: { e: ActivityEvent; fresh?: boolean; hideRoom?: boolean }) {
  const who = shortName(e.agent_id || "system");
  const room = e.room_id;
  return (
    <div
      className={cn(
        "flex gap-2 text-[12px] leading-5 transition-opacity duration-500 text-[var(--dim)]",
        fresh ? "opacity-100" : "opacity-90"
      )}
    >
      <span className="w-14 shrink-0 text-[var(--faint)]">{relTime(e.ts)}</span>
      <AgentBadge name={e.agent_id || "system"} status="working" size={20} variant="initial" className="mt-0.5 shrink-0" />
      <span className="w-20 shrink-0 truncate font-medium text-foreground/80">{who}</span>
      <span className="min-w-0 flex-1 truncate">{e.message}</span>
      {room && !hideRoom ? (
        <Link href={`/rooms/${room}`} className="shrink-0 text-accent">
          →
        </Link>
      ) : null}
    </div>
  );
}

export function ActivityLog({
  roomId,
  compact,
  defaultScope,
  defaultOpen = true,
  className,
}: {
  roomId?: string;
  compact?: boolean;
  defaultScope?: "all" | "room";
  defaultOpen?: boolean;
  className?: string;
}) {
  const { activity: live, tick } = useGlobalWs();
  const [seed, setSeed] = useState<ActivityEvent[]>([]);
  const [open, setOpen] = useState(defaultOpen);
  const [scope, setScope] = useState<"all" | "room">(defaultScope || (roomId ? "room" : "all"));

  useEffect(() => {
    if (roomId && defaultScope === "room") setScope("room");
  }, [roomId, defaultScope]);

  useEffect(() => {
    api
      .activity()
      .then((r) => setSeed(r.events))
      .catch(() => setSeed([]));
  }, [tick]);

  const rows = useMemo(() => {
    const merged = [...live, ...seed].slice(0, 80);
    if (!roomId || scope === "all") return merged.slice(0, compact ? 24 : 40);
    return merged.filter((e) => e.room_id === roomId).slice(0, compact ? 24 : 40);
  }, [live, seed, roomId, scope, compact]);

  return (
    <div className={cn("surface-lg px-4 py-3", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          className="flex items-center gap-2 text-left"
          onClick={() => setOpen((o) => !o)}
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">Live feed</p>
          {rows.length ? (
            <span className="rounded-full bg-[var(--elev)] px-2 py-0.5 text-[10px] font-medium text-[var(--dim)]">
              {rows.length}
            </span>
          ) : null}
        </button>
        <div className="flex items-center gap-3">
          {roomId ? (
            <div className="flex rounded-full border border-border bg-[#eef2ee] p-0.5 text-[11px]">
              <button
                type="button"
                onClick={() => setScope("room")}
                className={cn(
                  "rounded-full px-2 py-0.5 font-medium",
                  scope === "room" ? "bg-white text-accent shadow-sm" : "text-[var(--dim)]"
                )}
              >
                This room
              </button>
              <button
                type="button"
                onClick={() => setScope("all")}
                className={cn(
                  "rounded-full px-2 py-0.5 font-medium",
                  scope === "all" ? "bg-white text-accent shadow-sm" : "text-[var(--dim)]"
                )}
              >
                Fleet
              </button>
            </div>
          ) : null}
          <button
            type="button"
            className="text-[12px] text-[var(--dim)] hover:text-foreground"
            onClick={() => setOpen((o) => !o)}
          >
            {open ? "Hide" : "Show"}
          </button>
        </div>
      </div>
      {open ? (
        <div className={cn("mt-2 space-y-1 overflow-y-auto", compact ? "max-h-32" : "max-h-52")}>
          {rows.length ? (
            rows.map((e, i) => (
              <Row key={`${e.ts}-${e.agent_id}-${i}`} e={e} fresh={i === 0 && live.length > 0} hideRoom={Boolean(roomId)} />
            ))
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
