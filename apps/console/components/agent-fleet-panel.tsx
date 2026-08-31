"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Handoff, OfficeDesk } from "@/lib/api";
import { AgentBadge } from "@/components/agent-badge";
import { agentHref, shortName } from "@/lib/names";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

function statusKind(desk: OfficeDesk): "working" | "handing_off" | "idle" {
  if (desk.status === "handing_off") return "handing_off";
  if (desk.status !== "idle") return "working";
  return "idle";
}

function AgentRow({ desk }: { desk: OfficeDesk }) {
  const kind = statusKind(desk);
  const busy = kind !== "idle";

  return (
    <Link
      href={desk.room_id ? `/rooms/${desk.room_id}` : agentHref(desk.id)}
      className="group interactive row-link flex items-center gap-3 px-4 py-3 sm:px-5"
    >
      <AgentBadge name={desk.id} status={kind} size={32} variant="face" />
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-2">
          <span className="truncate text-[14px] font-medium">{desk.display_name}</span>
          {busy ? (
            <span
              className={cn(
                "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                kind === "handing_off" ? "bg-warn/10 text-warn" : "bg-accent/10 text-accent"
              )}
            >
              {kind === "handing_off" ? "Handoff" : "Active"}
            </span>
          ) : null}
        </span>
        <span className="mt-0.5 block truncate text-[12px] text-[var(--faint)]">
          {busy ? desk.doing : desk.role}
        </span>
        {desk.room_title && busy ? (
          <span className="mt-0.5 block truncate text-[11px] text-accent">{desk.room_title}</span>
        ) : null}
      </span>
      <span className="shrink-0 text-[var(--faint)]">→</span>
    </Link>
  );
}

/** Manager view — active agents first, idle collapsed (SalesShortcut / pixel-agents energy). */
export function AgentFleetPanel({
  desks,
  handoffs,
  className,
}: {
  desks: OfficeDesk[];
  handoffs: Handoff[];
  className?: string;
}) {
  const [showIdle, setShowIdle] = useState(false);

  const { active, idle } = useMemo(() => {
    const a = desks.filter((d) => d.status !== "idle");
    const i = desks.filter((d) => d.status === "idle");
    return { active: a, idle: i };
  }, [desks]);

  const recentHandoffs = handoffs.slice(-3).reverse();

  return (
    <section id="team" className={cn("scroll-mt-6", className)}>
      <div className="flex flex-wrap items-end justify-between gap-2">
        <h2 className="text-[20px] font-semibold tracking-tight">
          {active.length} active
          <span className="ml-2 text-[15px] font-normal text-[var(--faint)]">· {idle.length} idle</span>
        </h2>
        <Link href="/registry" className="text-[13px] text-accent">
          All agents
        </Link>
      </div>

      <div className="surface-lg mt-4 divide-y divide-border">
        {active.length === 0 ? (
          <p className="px-5 py-8 text-center text-[14px] text-[var(--faint)]">No one working</p>
        ) : (
          active.map((desk) => <AgentRow key={desk.id} desk={desk} />)
        )}
      </div>

      {recentHandoffs.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {recentHandoffs.map((h) => (
            <Link
              key={h.id}
              href={h.room_id ? `/rooms/${h.room_id}` : agentHref(h.to_agent)}
              className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-3 py-1.5 text-[12px] text-[var(--dim)] transition hover:border-accent/30"
            >
              <span className="font-medium text-foreground">{shortName(h.from_agent)}</span>
              <span className="text-[var(--faint)]">→</span>
              <span className="font-medium text-foreground">{shortName(h.to_agent)}</span>
            </Link>
          ))}
        </div>
      ) : null}

      {idle.length > 0 ? (
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setShowIdle((o) => !o)}
            className="interactive flex w-full items-center justify-between gap-2 rounded-xl border border-border bg-white px-4 py-2.5 text-left text-[13px] text-[var(--dim)] press"
          >
            <span>{idle.length} agents on standby</span>
            <ChevronDown className={cn("h-4 w-4 shrink-0 transition-transform", showIdle && "rotate-180")} />
          </button>
          {showIdle ? (
            <div className="mt-2 grid grid-cols-3 gap-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
              {idle.map((desk) => (
                <Link
                  key={desk.id}
                  href={agentHref(desk.id)}
                  className="flex flex-col items-center rounded-xl px-1 py-2 transition hover:bg-white"
                >
                  <AgentBadge name={desk.id} status="idle" size={28} variant="face" />
                  <span className="mt-1 w-full truncate text-center text-[10px] text-[var(--faint)]">
                    {shortName(desk.id)}
                  </span>
                </Link>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
