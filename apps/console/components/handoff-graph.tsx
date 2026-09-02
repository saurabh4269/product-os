"use client";

import Link from "next/link";
import { useMemo } from "react";
import type { Handoff, OfficeDesk } from "@/lib/api";
import { AgentBadge } from "@/components/agent-badge";
import { agentHref, shortName } from "@/lib/names";
import { cn } from "@/lib/utils";

const COL_W = 108;
const ROW_H = 72;
const PAD = 24;

function layoutAgents(handoffs: Handoff[]) {
  const order: string[] = [];
  const seen = new Set<string>();
  for (const h of handoffs) {
    for (const id of [h.from_agent, h.to_agent]) {
      if (!id || seen.has(id)) continue;
      seen.add(id);
      order.push(id);
    }
  }
  const positions: Record<string, { x: number; y: number; col: number }> = {};
  order.forEach((id, i) => {
    const col = i;
    positions[id] = { x: PAD + col * COL_W, y: PAD + 28, col };
  });
  return { order, positions };
}

export function HandoffGraph({
  desks,
  handoffs,
  live = false,
  className,
}: {
  desks: OfficeDesk[];
  handoffs: Handoff[];
  live?: boolean;
  className?: string;
}) {
  const recent = handoffs.slice(-12);
  const deskById = useMemo(() => Object.fromEntries(desks.map((d) => [d.id, d])), [desks]);
  const { order, positions } = useMemo(() => layoutAgents(recent), [recent]);

  const width = Math.max(320, PAD * 2 + Math.max(order.length, 1) * COL_W);
  const height = ROW_H + PAD * 2 + 40;

  if (!recent.length) {
    const working = desks.filter((d) => d.status !== "idle");
    return (
      <section className={cn("rounded-2xl border border-border bg-white px-4 py-4 sm:px-5", className)}>
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-[15px] font-semibold tracking-tight">Agent handoffs</h2>
          {live ? (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-ok/10 px-2 py-0.5 text-[11px] font-medium text-ok">
              <span className="h-1.5 w-1.5 rounded-full bg-ok animate-pulse" />
              Watching
            </span>
          ) : null}
        </div>
        {working.length > 0 ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {working.slice(0, 8).map((d) => (
              <Link
                key={d.id}
                href={d.room_id ? `/rooms/${d.room_id}` : agentHref(d.id)}
                className="inline-flex items-center gap-2 rounded-full border border-border bg-[var(--elev)] px-2.5 py-1.5 text-[12px] hover:border-accent/30"
              >
                <AgentBadge
                  name={d.id}
                  status={d.status === "handing_off" ? "handing_off" : "working"}
                  size={22}
                  variant="face"
                />
                <span className="font-medium text-foreground">{shortName(d.id)}</span>
                <span className="max-w-[8rem] truncate text-[var(--faint)]">{d.doing}</span>
              </Link>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-[13px] leading-5 text-[var(--dim)]">
            Signal agent is watching telemetry. When a case opens, Commander handoffs appear here as structured A2A packets.
          </p>
        )}
      </section>
    );
  }

  return (
    <section className={cn("overflow-hidden rounded-2xl border border-border bg-white", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-3 sm:px-5">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight">Agent handoffs</h2>
          <p className="mt-0.5 text-[12px] text-[var(--faint)]">Incident Commander → specialists · structured A2A</p>
        </div>
        {live ? (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-ok/10 px-2 py-0.5 text-[11px] font-medium text-ok">
            <span className="h-1.5 w-1.5 rounded-full bg-ok animate-pulse" />
            Live
          </span>
        ) : null}
      </div>

      <div className="overflow-x-auto px-2 py-3">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="min-w-full"
          style={{ minWidth: width }}
          role="img"
          aria-label="Agent handoff graph"
        >
          {recent.map((h, i) => {
            const a = positions[h.from_agent];
            const b = positions[h.to_agent];
            if (!a || !b) return null;
            const x1 = a.x + 20;
            const y1 = a.y;
            const x2 = b.x - 4;
            const y2 = b.y;
            const mid = (x1 + x2) / 2;
            return (
              <g key={`${h.id}-${i}`}>
                <path
                  d={`M ${x1} ${y1} C ${mid} ${y1 - 18}, ${mid} ${y2 - 18}, ${x2} ${y2}`}
                  fill="none"
                  stroke={live ? "rgba(0,113,227,0.35)" : "rgba(29,29,31,0.14)"}
                  strokeWidth="1.5"
                  strokeDasharray={live ? undefined : "4 3"}
                />
                {live ? (
                  <circle r="3" fill="#0071e3">
                    <animateMotion dur="3.2s" repeatCount="indefinite" path={`M ${x1} ${y1} C ${mid} ${y1 - 18}, ${mid} ${y2 - 18}, ${x2} ${y2}`} />
                  </circle>
                ) : null}
              </g>
            );
          })}
          {order.map((id) => {
            const pos = positions[id];
            const desk = deskById[id];
            const busy = desk && desk.status !== "idle";
            return (
              <g key={id}>
                <foreignObject x={pos.x - 28} y={pos.y - 22} width="56" height="56">
                  <Link
                    href={desk?.room_id ? `/rooms/${desk.room_id}` : agentHref(id)}
                    className="flex flex-col items-center gap-0.5"
                  >
                    <AgentBadge
                      name={id}
                      status={desk?.status === "handing_off" ? "handing_off" : busy ? "working" : "idle"}
                      size={32}
                      variant="face"
                    />
                    <span className="max-w-[4.5rem] truncate text-center text-[9px] font-medium text-[#1d1d1f]">
                      {shortName(id)}
                    </span>
                  </Link>
                </foreignObject>
              </g>
            );
          })}
        </svg>
      </div>

      <ul className="divide-y divide-border border-t border-border">
        {recent
          .slice()
          .reverse()
          .slice(0, 4)
          .map((h) => (
            <li key={h.id}>
              <Link
                href={h.room_id ? `/rooms/${h.room_id}` : agentHref(h.to_agent)}
                className="flex items-start gap-3 px-4 py-2.5 transition hover:bg-[var(--elev)] sm:px-5"
              >
                <div className="flex shrink-0 items-center gap-1 pt-0.5">
                  <AgentBadge name={h.from_agent} size={20} variant="face" />
                  <span className="text-[11px] text-[var(--faint)]">→</span>
                  <AgentBadge name={h.to_agent} size={20} variant="face" />
                </div>
                <p className="min-w-0 flex-1 text-[13px] leading-5 text-[var(--dim)]">
                  <span className="font-medium text-foreground">
                    {shortName(h.from_agent)} → {shortName(h.to_agent)}
                  </span>
                  {h.summary ? <span className="text-[var(--faint)]"> · {h.summary}</span> : null}
                </p>
              </Link>
            </li>
          ))}
      </ul>
    </section>
  );
}
