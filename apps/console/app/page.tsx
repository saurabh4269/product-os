"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Room } from "@/lib/api";
import { pct, when } from "@/lib/utils";
import { Badge, Button, Card, ErrorState, Loading } from "@/components/ui";
import { Pixel } from "@/components/pixel-office";

export default function HomePage() {
  const [rooms, setRooms] = useState<Room[] | null>(null);
  const [signals, setSignals] = useState<Array<Record<string, unknown>>>([]);
  const [metrics, setMetrics] = useState<Awaited<ReturnType<typeof api.metrics>> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [r, s, m] = await Promise.all([
        api.rooms(),
        api.signals(),
        api.metrics().catch(() => null),
      ]);
      setRooms(r.rooms);
      setSignals(s.signals);
      setMetrics(m);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "API unreachable. Run ./scripts/boot.sh");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function seed() {
    setBusy(true);
    try {
      await api.seedWorld();
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "seed failed");
    } finally {
      setBusy(false);
    }
  }

  if (err) return <ErrorState message={err} />;
  if (!rooms) return <Loading label="Reading the fleet" />;

  const typeA = rooms.filter((r) => r.loop_type === "type_a");
  const typeB = rooms.filter((r) => r.loop_type === "type_b");

  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.22em] text-accent">Product OS</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">I observed the product.</h1>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-[var(--dim)]">
            Investigated. Talked to customers. Coordinated agents. Changed the software. Got the right approval.
            Verified the outcome. Rooms are the product — not a dashboard around one demo.
          </p>
        </div>
        <Button onClick={seed} disabled={busy}>
          {busy ? "Seeding…" : "Seed world"}
        </Button>
      </div>

      <div className="grid-fade grid gap-3 md:grid-cols-4">
        <Card>
          <p className="font-mono text-[10px] uppercase text-[var(--dim)]">Rooms</p>
          <p className="mt-2 text-3xl">{rooms.length}</p>
        </Card>
        <Card>
          <p className="font-mono text-[10px] uppercase text-[var(--dim)]">Type A · broke</p>
          <p className="mt-2 text-3xl">{typeA.length}</p>
        </Card>
        <Card>
          <p className="font-mono text-[10px] uppercase text-[var(--dim)]">Type B · better</p>
          <p className="mt-2 text-3xl">{typeB.length}</p>
        </Card>
        <Card>
          <p className="font-mono text-[10px] uppercase text-[var(--dim)]">Idea → impact</p>
          <p className="mt-2 text-3xl">
            {metrics?.idea_to_impact_hours_mean != null ? `${metrics.idea_to_impact_hours_mean}h` : "open"}
          </p>
          <p className="mt-1 text-[11px] text-[var(--dim)]">target &lt; {metrics?.idea_to_impact_target_hours ?? 48}h</p>
        </Card>
      </div>

      <section>
        <h2 className="mb-3 text-sm font-medium">Live signals</h2>
        <div className="grid-fade grid gap-2 md:grid-cols-2">
          {signals.map((s) => {
            const segs = (s.affected_segments as Array<{ browser?: string; os?: string; platform?: string; geo?: string }>) ?? [];
            const label = segs[0]?.browser || segs[0]?.os || segs[0]?.platform || segs[0]?.geo || "fleet";
            const mag = Number(s.magnitude);
            return (
              <Card key={String(s.id)} className="flex items-center justify-between gap-3 py-4">
                <div>
                  <p className="text-sm">
                    {String(s.metric)} · {label}
                  </p>
                  <p className="mt-1 font-mono text-[11px] text-[var(--dim)]">
                    {String(s.family)} · {String(s.funnel_position)} · {when(String(s.detected_at))}
                  </p>
                </div>
                <div className="text-right">
                  <p className={mag < 0 ? "font-mono text-sm text-danger" : "font-mono text-sm text-ok"}>
                    {Math.abs(mag) > 1 ? mag.toFixed(0) : pct(mag)}
                  </p>
                  <Badge tone={s.direction === "negative" ? "danger" : "ok"}>{String(s.direction)}</Badge>
                </div>
              </Card>
            );
          })}
        </div>
      </section>

      <section>
        <h2 className="mb-3 text-sm font-medium">Rooms</h2>
        <div className="grid-fade grid gap-2 md:grid-cols-2">
          {rooms
            .filter((r) => r.scenario_id)
            .map((room) => (
              <Link key={room.id} href={`/rooms/${room.id}`} className="block">
                <Card className="transition hover:border-accent/40">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <Pixel name={room.members[0] ?? "orchestrator"} />
                        <p className="text-sm font-medium">{room.title}</p>
                      </div>
                      <p className="mt-2 line-clamp-2 text-xs text-[var(--dim)]">{room.topic}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <Badge tone={room.kind === "incident" ? "danger" : room.kind === "opportunity" ? "ok" : "warn"}>
                        {room.kind}
                      </Badge>
                      {room.loop_type ? <Badge tone="accent">{room.loop_type === "type_a" ? "A" : "B"}</Badge> : null}
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
        </div>
      </section>
    </div>
  );
}
