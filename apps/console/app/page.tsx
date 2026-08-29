"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Room } from "@/lib/api";
import { pct, when } from "@/lib/utils";
import { ErrorState, Loading } from "@/components/ui";
import { HiveChamber } from "@/components/pixel-office";

function magLabel(raw: unknown) {
  const n = Number(raw);
  if (Number.isNaN(n)) return "—";
  return Math.abs(n) > 1 ? String(Math.round(n)) : pct(n);
}

export default function HivePage() {
  const [rooms, setRooms] = useState<Room[] | null>(null);
  const [signals, setSignals] = useState<Array<Record<string, unknown>>>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.rooms(), api.signals()])
      .then(([r, s]) => {
        setRooms(r.rooms);
        setSignals(s.signals);
        setErr(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "API unreachable"));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!rooms) return <Loading label="Walking into the office" />;

  const chambers = rooms.filter((r) => r.scenario_id || ["review", "research", "ops"].includes(r.kind));

  return (
    <div className="min-h-full px-8 py-8 lg:px-12">
      <header className="max-w-3xl">
        <p className="text-[12px] uppercase tracking-[0.2em] text-accent">Live office</p>
        <h1 className="font-display mt-3 text-[52px] leading-[1.05] tracking-tight">
          I observed the product.
        </h1>
        <p className="mt-4 max-w-xl text-[16px] leading-7 text-[var(--dim)]">
          Agents are already in the rooms. Walk in. Nothing here is a dashboard about a single demo.
        </p>
      </header>

      {signals.length > 0 ? (
        <div className="mt-10 flex flex-wrap items-baseline gap-x-8 gap-y-3 border-y border-border py-4">
          {signals.map((s) => {
            const segs =
              (s.affected_segments as Array<{ browser?: string; os?: string; platform?: string; geo?: string }>) ?? [];
            const who = segs[0]?.browser || segs[0]?.os || segs[0]?.platform || segs[0]?.geo || "fleet";
            const n = Number(s.magnitude);
            return (
              <div key={String(s.id)} className="min-w-[140px]">
                <p className="text-[11px] uppercase tracking-[0.14em] text-[var(--faint)]">
                  {String(s.metric).replace(/_/g, " ")} · {who}
                </p>
                <p
                  className="mt-1 font-display text-[28px] leading-none"
                  style={{ color: n < 0 ? "var(--danger)" : "var(--ok)" }}
                >
                  {magLabel(s.magnitude)}
                </p>
                <p className="mt-1 text-[11px] text-[var(--faint)]">{when(String(s.detected_at))}</p>
              </div>
            );
          })}
        </div>
      ) : null}

      <div className="rise mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {chambers.map((room) => (
          <Link key={room.id} href={`/rooms/${room.id}`} className="block min-h-[240px]">
            <HiveChamber
              title={room.title}
              kind={room.kind}
              preview={room.preview ?? room.topic}
              members={room.members}
              loop={room.loop_type}
            />
          </Link>
        ))}
      </div>
    </div>
  );
}
