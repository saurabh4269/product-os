"use client";

import Link from "next/link";
import { AgentBadge } from "@/components/agent-badge";
import { agentHref, shortName } from "@/lib/names";

/** product-os-v2 handoff moment — from → to with a brief flash. */
export function HandoffPacket({
  from,
  to,
  summary,
  at,
  fresh = false,
}: {
  from: string;
  to: string;
  summary: string;
  at?: string;
  fresh?: boolean;
}) {
  return (
    <div
      className={
        "my-3 flex flex-col gap-2 rounded-2xl border border-border bg-[var(--elev)] px-4 py-3 sm:flex-row sm:flex-wrap sm:items-center " +
        (fresh ? "animate-[handoff_0.6s_ease-out]" : "")
      }
    >
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-[var(--faint)]">
          Handoff
        </span>
        <Link href={agentHref(from)} className="flex items-center gap-1.5 hover:opacity-80">
          <AgentBadge name={from} size={24} variant="face" />
          <span className="text-[13px] font-medium">{shortName(from)}</span>
        </Link>
        <span className="text-[13px] text-[var(--faint)]">→</span>
        <Link href={agentHref(to)} className="flex items-center gap-1.5 hover:opacity-80">
          <AgentBadge name={to} size={24} variant="face" />
          <span className="text-[13px] font-medium text-accent">{shortName(to)}</span>
        </Link>
      </div>
      <p className="min-w-0 flex-1 text-[13px] leading-5 text-[var(--dim)]">{summary}</p>
      {at ? <span className="shrink-0 text-[11px] text-[var(--faint)]">{at}</span> : null}
    </div>
  );
}
