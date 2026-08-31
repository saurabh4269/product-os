"use client";

import Link from "next/link";
import { PixelSprite } from "@/components/pixel-office";
import { shortName } from "@/lib/names";

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
        "my-3 flex flex-col gap-2 rounded-2xl border border-border bg-[var(--elev)] px-4 py-3 sm:flex-row sm:items-center " +
        (fresh ? "animate-[handoff_0.6s_ease-out]" : "")
      }
    >
      <div className="flex items-center gap-2">
        <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-[var(--faint)]">
          Handoff
        </span>
        <Link href={`/agents/${from}`} className="flex items-center gap-1.5 hover:opacity-80">
          <PixelSprite name={from} scale={2} />
          <span className="text-[13px] font-medium">{shortName(from)}</span>
        </Link>
        <span className="text-[13px] text-[var(--faint)]">→</span>
        <Link href={`/agents/${to}`} className="flex items-center gap-1.5 hover:opacity-80">
          <PixelSprite name={to} scale={2} />
          <span className="text-[13px] font-medium text-accent">{shortName(to)}</span>
        </Link>
      </div>
      <p className="min-w-0 flex-1 text-[13px] leading-5 text-[var(--dim)]">{summary}</p>
      {at ? <span className="shrink-0 text-[11px] text-[var(--faint)]">{at}</span> : null}
    </div>
  );
}
