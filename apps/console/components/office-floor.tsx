"use client";

import Link from "next/link";
import type { Handoff, OfficeDesk } from "@/lib/api";
import { shortName } from "@/lib/names";
import { PixelSprite } from "@/components/pixel-office";
import { cn } from "@/lib/utils";

const DISTRICTS = ["Incidents", "Ideas", "Reviews", "Research", "Ops", "Office"];

function DeskTile({ desk }: { desk: OfficeDesk }) {
  const busy = desk.status !== "idle";
  return (
    <Link
      href={`/agents/${desk.id}`}
      className="group flex w-[132px] flex-col items-center rounded-2xl px-2 py-3 text-center transition-colors hover:bg-white"
    >
      <div className="relative">
        {busy ? (
          <span className="absolute -top-5 left-1/2 z-10 max-w-[120px] -translate-x-1/2 truncate rounded-full bg-white px-2 py-0.5 text-[10px] leading-4 text-[var(--dim)] shadow-sm">
            {desk.doing}
          </span>
        ) : null}
        <PixelSprite name={desk.id} scale={3} working={busy} />
      </div>
      <p className="mt-1 text-[13px] font-medium leading-4">{desk.display_name}</p>
      <p className="mt-0.5 line-clamp-2 min-h-[32px] text-[11px] leading-4 text-[var(--faint)]">
        {desk.room_title ?? (busy ? "Working" : "Around the office")}
      </p>
    </Link>
  );
}

export function OfficeFloor({
  desks,
  handoffs,
  working,
}: {
  desks: OfficeDesk[];
  handoffs: Handoff[];
  working: number;
}) {
  const recent = handoffs.slice(-4).reverse();
  return (
    <section className="overflow-hidden rounded-[24px] border border-border bg-white">
      <div className="flex flex-wrap items-end justify-between gap-3 px-4 pt-5 sm:px-6 sm:pt-6">
        <div>
          <p className="text-[13px] text-[var(--faint)]">The office</p>
          <h2 className="mt-1 text-[22px] font-semibold tracking-tight">Who’s up to what</h2>
        </div>
        <p className="text-[13px] text-[var(--dim)]">
          {working} working · tap anyone to read their chat
        </p>
      </div>

      <div className="mt-4 space-y-2 px-4 pb-2">
        {DISTRICTS.map((district) => {
          const group = desks.filter((d) => d.district === district);
          if (!group.length) return null;
          return (
            <div key={district} className="rounded-[20px] bg-[var(--floor)] px-3 py-3">
              <p className="px-2 pb-1 text-[12px] text-[var(--faint)]">{district}</p>
              <div className="flex flex-wrap justify-start">
                {group.map((desk) => (
                  <DeskTile key={desk.id} desk={desk} />
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {recent.length ? (
        <div className="border-t border-border px-4 py-4 sm:px-6">
          <p className="text-[12px] text-[var(--faint)]">Handing work across the room</p>
          <div className="mt-2 space-y-2">
            {recent.map((h) => (
              <p key={h.id} className="text-[13px] leading-5 text-[var(--dim)]">
                <Link href={`/agents/${h.from_agent}`} className="font-medium text-foreground hover:text-accent">
                  {shortName(h.from_agent)}
                </Link>
                <span className="mx-1.5 text-[var(--faint)]">→</span>
                <Link href={`/agents/${h.to_agent}`} className="font-medium text-foreground hover:text-accent">
                  {shortName(h.to_agent)}
                </Link>
                <span className="mx-2 text-[var(--faint)]">·</span>
                {h.summary}
                {h.room_id ? (
                  <>
                    <span className="mx-2 text-[var(--faint)]">·</span>
                    <Link href={`/rooms/${h.room_id}`} className="text-accent">
                      {h.room_title ?? "room"}
                    </Link>
                  </>
                ) : null}
              </p>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function RoomHandoff({
  from,
  to,
  summary,
  at,
}: {
  from: string;
  to: string;
  summary: string;
  at?: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 py-2 pl-4 text-[13px] text-[var(--dim)] sm:pl-10">
      <span className={cn("rounded-full bg-[var(--elev)] px-2 py-0.5 text-[12px]")}>handed off</span>
      <Link href={`/agents/${from}`} className="font-medium text-foreground hover:text-accent">
        {shortName(from)}
      </Link>
      <span>→</span>
      <Link href={`/agents/${to}`} className="font-medium text-foreground hover:text-accent">
        {shortName(to)}
      </Link>
      <span className="min-w-0 truncate">{summary}</span>
      {at ? <span className="shrink-0 text-[12px] text-[var(--faint)]">{at}</span> : null}
    </div>
  );
}
