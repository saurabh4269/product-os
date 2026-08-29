"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Room } from "@/lib/api";
import { pct } from "@/lib/utils";
import { ErrorState, Loading } from "@/components/ui";
import { HiveChamber } from "@/components/pixel-office";

function magLabel(raw: unknown) {
  const n = Number(raw);
  if (Number.isNaN(n)) return "—";
  return Math.abs(n) > 1 ? String(Math.round(n)) : pct(n);
}

export default function HomePage() {
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
  if (!rooms) return <Loading label="Opening home" />;

  const chambers = rooms.filter((r) => r.scenario_id || ["review", "research", "ops"].includes(r.kind));

  return (
    <div className="min-h-full px-8 py-12 lg:px-16">
      <header className="max-w-xl">
        <h1 className="text-[32px] font-semibold tracking-tight">Welcome</h1>
        <p className="mt-3 text-[15px] leading-6 text-[var(--dim)]">
          The team is already in the rooms. Open one when you’re ready.
        </p>
      </header>

      {signals.length > 0 ? (
        <div className="mt-10 flex flex-wrap gap-x-10 gap-y-4">
          {signals.map((s) => {
            const segs =
              (s.affected_segments as Array<{ browser?: string; os?: string; platform?: string; geo?: string }>) ?? [];
            const who = segs[0]?.browser || segs[0]?.os || segs[0]?.platform || segs[0]?.geo || "all";
            return (
              <div key={String(s.id)}>
                <p className="text-[12px] text-[var(--faint)]">
                  {String(s.metric).replace(/_/g, " ")} · {who}
                </p>
                <p className="mt-0.5 text-[20px] font-semibold tracking-tight text-foreground">{magLabel(s.magnitude)}</p>
              </div>
            );
          })}
        </div>
      ) : null}

      <div className="rise mt-12 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        {chambers.map((room) => (
          <Link key={room.id} href={`/rooms/${room.id}`} className="block min-h-[220px]">
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
