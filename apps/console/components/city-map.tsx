"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Handoff, OfficeDesk, Room } from "@/lib/api";
import { shortName } from "@/lib/names";
import { PixelSprite } from "@/components/pixel-office";
import { cn } from "@/lib/utils";

type Slot = { x: number; y: number; kind: string };

const SLOTS: Record<string, Slot[]> = {
  incident: [
    { x: 22.5, y: 46, kind: "incident" },
    { x: 28.5, y: 39, kind: "incident" },
    { x: 25.5, y: 55, kind: "incident" },
  ],
  opportunity: [
    { x: 55, y: 43, kind: "opportunity" },
    { x: 63, y: 50, kind: "opportunity" },
  ],
  review: [{ x: 41.5, y: 40, kind: "review" }],
  research: [{ x: 78, y: 34, kind: "research" }],
  ops: [{ x: 71.5, y: 43, kind: "ops" }],
};

const LANDMARKS = [
  { href: "/memory", label: "Memory", hint: "What we learned last time", x: 37.5, y: 67 },
  { href: "/approvals", label: "Approvals", hint: "A few things waiting on you", x: 52, y: 77 },
];

type Placed = {
  room: Room;
  x: number;
  y: number;
  desks: OfficeDesk[];
};

function placeRooms(rooms: Room[], desks: OfficeDesk[]): Placed[] {
  const used: Record<string, number> = {};
  const out: Placed[] = [];
  const ordered = [...rooms].sort((a, b) => a.kind.localeCompare(b.kind) || a.title.localeCompare(b.title));
  for (const room of ordered) {
    const bank = SLOTS[room.kind] ?? SLOTS.ops;
    const i = used[room.kind] ?? 0;
    used[room.kind] = i + 1;
    const slot = bank[Math.min(i, bank.length - 1)];
    const people = desks.filter((d) => d.room_id === room.id).slice(0, 4);
    out.push({ room, x: slot.x + i * 0.15, y: slot.y + (i > bank.length - 1 ? 4 : 0), desks: people });
  }
  return out;
}

function kindWord(kind: string) {
  if (kind === "incident") return "Incident";
  if (kind === "opportunity") return "Idea";
  if (kind === "review") return "Review";
  if (kind === "research") return "Research";
  return "Ops";
}

export function CityMap({
  rooms,
  desks,
  handoffs,
  working,
}: {
  rooms: Room[];
  desks: OfficeDesk[];
  handoffs: Handoff[];
  working: number;
}) {
  const placed = useMemo(() => placeRooms(rooms, desks), [rooms, desks]);
  const [focus, setFocus] = useState<string | null>(null);
  const current = placed.find((p) => p.room.id === focus) ?? null;
  const byId = Object.fromEntries(placed.map((p) => [p.room.id, p]));

  const lines = handoffs
    .filter((h) => h.room_id && byId[h.room_id])
    .slice(-6)
    .map((h) => {
      const dest = h.room_id ? byId[h.room_id] : null;
      const srcRoom = placed.find((p) => p.desks.some((d) => d.id === h.from_agent)) ?? dest;
      if (!dest || !srcRoom) return null;
      return { id: h.id, a: srcRoom, b: dest, summary: h.summary };
    })
    .filter(Boolean) as Array<{ id: string; a: Placed; b: Placed; summary: string }>;

  return (
    <div className="relative flex h-full min-h-0 flex-col bg-[#f4f6f4]">
      <header className="pointer-events-none absolute left-6 top-6 z-20 max-w-sm">
        <p className="text-[13px] text-[var(--faint)]">Campus</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-tight">The work has a place</h1>
        <p className="mt-2 text-[14px] leading-6 text-[var(--dim)]">
          {working} people are already in the buildings. Click a pin to look inside.
        </p>
      </header>

      <div className="relative min-h-0 flex-1">
        <img
          src="/city/campus.png"
          alt="Product campus"
          className="absolute inset-0 h-full w-full object-contain object-center"
        />

        <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
          {lines.map((line) => (
            <path
              key={line.id}
              d={`M ${line.a.x} ${line.a.y} Q ${(line.a.x + line.b.x) / 2} ${Math.min(line.a.y, line.b.y) - 8} ${line.b.x} ${line.b.y}`}
              fill="none"
              stroke="rgba(29,29,31,0.22)"
              strokeWidth="0.35"
              strokeDasharray="1.2 1"
            />
          ))}
        </svg>

        {LANDMARKS.map((mark) => (
          <Link
            key={mark.href}
            href={mark.href}
            className="absolute z-10 -translate-x-1/2 -translate-y-full text-center"
            style={{ left: `${mark.x}%`, top: `${mark.y}%` }}
          >
            <span className="inline-block rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-medium text-[var(--dim)] shadow-sm">
              {mark.label}
            </span>
          </Link>
        ))}

        {placed.map((spot) => {
          const busy = spot.desks.some((d) => d.status !== "idle") || (spot.room.message_count ?? 0) > 0;
          const selected = focus === spot.room.id;
          return (
            <button
              key={spot.room.id}
              type="button"
              onClick={() => setFocus(spot.room.id)}
              className="absolute z-10 -translate-x-1/2 -translate-y-[86%] text-center"
              style={{ left: `${spot.x}%`, top: `${spot.y}%` }}
            >
              <span className="relative inline-block">
                <img
                  src="/city/pin.png"
                  alt=""
                  className={cn("mx-auto block drop-shadow-md transition-transform", selected ? "h-14 w-14" : "h-10 w-10", busy && "pin-bob")}
                />
                <span className="absolute -bottom-1 left-1/2 flex -translate-x-1/2">
                  {spot.desks.slice(0, 3).map((desk, i) => (
                    <span key={desk.id} className="inline-block" style={{ marginLeft: i ? -8 : 0 }}>
                      <PixelSprite name={desk.id} scale={2} working={desk.status !== "idle"} />
                    </span>
                  ))}
                </span>
              </span>
              <span
                className={cn(
                  "mt-7 block max-w-[140px] truncate rounded-full px-2.5 py-1 text-[11px] font-medium shadow-sm",
                  selected ? "bg-[#1d1d1f] text-white" : "bg-white/90 text-[var(--ink)]"
                )}
              >
                {spot.room.title}
              </span>
            </button>
          );
        })}
      </div>

      {current ? (
        <aside className="absolute bottom-5 left-5 right-5 z-30 mx-auto max-w-md rounded-[22px] border border-border bg-white/95 p-5 shadow-[0_12px_40px_rgba(0,0,0,0.08)] backdrop-blur md:left-auto md:right-6 md:mx-0">
          <p className="text-[12px] text-[var(--faint)]">{kindWord(current.room.kind)}</p>
          <h2 className="mt-1 text-[18px] font-semibold leading-6 tracking-tight">{current.room.title}</h2>
          <p className="mt-2 text-[13px] leading-5 text-[var(--dim)]">{current.room.preview ?? current.room.topic}</p>
          {current.desks.length ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {current.desks.map((desk) => (
                <Link
                  key={desk.id}
                  href={`/agents/${desk.id}`}
                  className="inline-flex items-center gap-1.5 rounded-full bg-[var(--elev)] py-1 pl-1 pr-2.5 text-[12px] hover:bg-[#ececef]"
                >
                  <PixelSprite name={desk.id} scale={2} working={desk.status !== "idle"} />
                  {desk.display_name}
                </Link>
              ))}
            </div>
          ) : null}
          <div className="mt-4 flex items-center gap-3">
            <Link
              href={`/rooms/${current.room.id}`}
              className="inline-flex rounded-full bg-accent px-4 py-2 text-[14px] font-medium text-white hover:bg-[#0077ed]"
            >
              Open the room
            </Link>
            <button type="button" onClick={() => setFocus(null)} className="text-[13px] text-[var(--dim)]">
              Keep looking
            </button>
          </div>
        </aside>
      ) : null}
    </div>
  );
}
