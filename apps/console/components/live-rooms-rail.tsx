"use client";

import Link from "next/link";
import type { OfficeDesk, Room } from "@/lib/api";
import { AgentStack } from "@/components/agent-badge";
import { PixelOffice } from "@/components/pixel-office";
import { cn } from "@/lib/utils";

function roomActivity(room: Room, desks: OfficeDesk[]) {
  const working = desks.filter((d) => d.room_id === room.id && d.status !== "idle");
  return working.length;
}

export function LiveRoomsRail({
  rooms,
  desks,
  className,
}: {
  rooms: Room[];
  desks: OfficeDesk[];
  className?: string;
}) {
  const open = rooms
    .filter((r) => r.status === "open" || !r.status)
    .sort((a, b) => roomActivity(b, desks) - roomActivity(a, desks));

  if (!open.length) {
    return (
      <section className={cn("rounded-2xl border border-dashed border-border bg-white/60 px-5 py-8 text-center", className)}>
        <p className="text-[15px] font-medium text-foreground">No open rooms</p>
        <p className="mt-1 text-[13px] text-[var(--dim)]">
          When a signal opens work, rooms appear here. Walk in to see specialist handoffs and tool embeds.
        </p>
      </section>
    );
  }

  return (
    <section className={className} id="rooms">
      <div className="mb-3 flex items-end justify-between gap-2">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight">Open rooms</h2>
          <p className="mt-0.5 text-[12px] text-[var(--faint)]">{open.length} active · tap to enter</p>
        </div>
      </div>
      <div className="flex gap-3 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {open.map((room) => {
          const active = roomActivity(room, desks);
          const working = new Set(
            desks.filter((d) => d.room_id === room.id && d.status !== "idle").map((d) => d.id)
          );
          const loopLabel =
            room.loop_type === "type_a"
              ? "Type A · fix"
              : room.loop_type === "type_b"
                ? "Type B · improve"
                : null;
          return (
            <Link
              key={room.id}
              href={`/rooms/${room.id}`}
              className={cn(
                "flex w-[min(17rem,78vw)] shrink-0 flex-col overflow-hidden rounded-2xl border bg-white shadow-sm transition hover:border-accent/35 hover:shadow-md",
                active > 0 ? "border-accent/25" : "border-border"
              )}
            >
              <div className="border-b border-border/60 bg-[#eef2ee]/80 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-[13px] font-semibold text-foreground">{room.title}</span>
                  {active > 0 ? (
                    <span className="shrink-0 rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-medium text-accent">
                      {active} active
                    </span>
                  ) : null}
                </div>
                {loopLabel ? (
                  <p className="mt-0.5 text-[11px] text-[var(--faint)]">{loopLabel}</p>
                ) : (
                  <p className="mt-0.5 truncate text-[11px] text-[var(--faint)]">{room.topic || room.kind}</p>
                )}
              </div>
              <div className="flex min-h-[4.5rem] items-end justify-center px-2 py-3">
                <PixelOffice members={room.members} working={working} compact link={false} />
              </div>
              <div className="flex items-center justify-between gap-2 border-t border-border/50 px-3 py-2">
                <AgentStack names={room.members.filter((m) => m !== "you").slice(0, 5)} size={20} />
                <span className="text-[11px] font-medium text-accent">Enter →</span>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
