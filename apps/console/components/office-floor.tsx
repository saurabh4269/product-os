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

function DeskTile({ desk }: { desk: OfficeDesk }) {
  const kind = statusKind(desk);
  const busy = kind !== "idle";

  return (
    <Link
      href={desk.room_id ? `/rooms/${desk.room_id}` : agentHref(desk.id)}
      className="group flex min-w-0 flex-col items-center rounded-2xl px-1.5 py-3 text-center transition-colors hover:bg-white"
    >
      {busy ? (
        <span className="mb-1.5 max-w-full truncate rounded-full bg-white px-2 py-0.5 text-[11px] leading-4 text-[var(--dim)] shadow-sm">
          <span className="hidden sm:inline">{desk.doing}</span>
          <span className="sm:hidden">{kind === "handing_off" ? "Handoff" : "Active"}</span>
        </span>
      ) : (
        <span className="mb-1.5 h-5" aria-hidden />
      )}
      <AgentBadge name={desk.id} status={kind} size={36} variant="face" />
      <p className="mt-2 w-full truncate text-[13px] font-medium leading-4">{desk.display_name}</p>
      <p className="mt-0.5 line-clamp-1 w-full text-[11px] leading-4 text-[var(--faint)]">
        {busy ? desk.room_title ?? desk.doing : "Standby"}
      </p>
    </Link>
  );
}

export function OfficeFloor({
  desks,
  handoffs,
  working,
  activeOnlyDefault = false,
}: {
  desks: OfficeDesk[];
  handoffs: Handoff[];
  working: number;
  activeOnlyDefault?: boolean;
}) {
  const [showAll, setShowAll] = useState(!activeOnlyDefault);
  const recent = handoffs.slice(-4).reverse();

  const visibleDesks = useMemo(() => {
    if (showAll) return desks;
    return desks.filter((d) => d.status !== "idle");
  }, [desks, showAll]);

  const idleCount = desks.length - working;

  return (
    <section className="surface-lg">
      <div className="flex flex-col gap-1 px-5 pt-5 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <h2 className="text-[18px] font-semibold tracking-tight">Office</h2>
        <div className="flex items-center gap-3">
          <p className="text-[12px] text-[var(--faint)]">{working} active</p>
          {idleCount > 0 ? (
            <button
              type="button"
              onClick={() => setShowAll((o) => !o)}
              className="text-[12px] text-accent"
            >
              {showAll ? "Active only" : `+${idleCount} standby`}
            </button>
          ) : null}
        </div>
      </div>

      {visibleDesks.length === 0 ? (
        <p className="px-6 py-10 text-center text-[14px] text-[var(--faint)]">No active agents on the floor</p>
      ) : (
        <div className="mt-5 space-y-3 px-3 pb-5 sm:px-4">
          {["Incidents", "Ideas", "Reviews", "Research", "Ops", "Office"].map((district) => {
            const group = visibleDesks.filter((d) => d.district === district);
            if (!group.length) return null;
            return (
              <div key={district} className="rounded-[20px] bg-[var(--floor)] px-2 py-4 sm:px-3">
                <p className="px-2 pb-2 text-[12px] text-[var(--faint)]">{district}</p>
                <div className="grid grid-cols-2 gap-x-2 gap-y-3 sm:grid-cols-3 lg:grid-cols-5 xl:grid-cols-6">
                  {group.map((desk) => (
                    <DeskTile key={desk.id} desk={desk} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {recent.length ? (
        <div className="border-t border-border px-5 py-5 sm:px-6">
          <p className="text-[12px] text-[var(--faint)]">Handoffs</p>
          <div className="mt-3 space-y-3">
            {recent.map((h) => (
              <div key={h.id} className="text-[14px] leading-6 text-[var(--dim)]">
                <p>
                  <Link href={agentHref(h.from_agent)} className="font-medium text-foreground hover:text-accent">
                    {shortName(h.from_agent)}
                  </Link>
                  <span className="mx-1.5 text-[var(--faint)]">→</span>
                  <Link href={agentHref(h.to_agent)} className="font-medium text-foreground hover:text-accent">
                    {shortName(h.to_agent)}
                  </Link>
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
