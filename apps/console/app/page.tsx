"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { pct, when } from "@/lib/utils";
import { Badge, Button, Card, Empty, ErrorState, Loading } from "@/components/ui";

export default function PulsePage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.investigations>> | null>(null);
  const [signals, setSignals] = useState<Awaited<ReturnType<typeof api.signals>> | null>(null);
  const [metrics, setMetrics] = useState<Awaited<ReturnType<typeof api.metrics>> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    try {
      const [inv, sig, met] = await Promise.all([
        api.investigations(),
        api.signals(),
        api.metrics().catch(() => null),
      ]);
      setData(inv);
      setSignals(sig);
      setMetrics(met);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "API unreachable. Run ./scripts/boot.sh");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function run() {
    setBusy(true);
    try {
      await api.run();
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "run failed");
    } finally {
      setBusy(false);
    }
  }

  if (err) return <ErrorState message={err} />;
  if (!data || !signals) return <Loading label="Reading warehouse" />;

  const open = data.investigations.filter((i) => !["RESOLVED", "NOT_RESOLVED", "INCONCLUSIVE"].includes(i.state));

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Pulse</h1>
          <p className="mt-1 text-sm text-slate-400">
            Signal detection is unprompted. LOOP opened what the warehouse showed.
          </p>
        </div>
        <Button onClick={run} disabled={busy}>
          {busy ? "Detecting…" : "Run detection"}
        </Button>
      </div>

      <div className="grid-fade grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Open investigations</p>
          <p className="mt-2 text-3xl">{open.length}</p>
        </Card>
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Signals</p>
          <p className="mt-2 text-3xl">{signals.signals.length}</p>
        </Card>
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Awaiting you</p>
          <p className="mt-2 text-3xl">
            {data.investigations.filter((i) => i.state === "AWAITING_APPROVAL").length}
          </p>
        </Card>
        <Card>
          <p className="font-mono text-[11px] uppercase text-slate-500">Idea → impact</p>
          <p className="mt-2 text-3xl">
            {metrics?.idea_to_impact_hours_mean != null
              ? `${metrics.idea_to_impact_hours_mean}h`
              : "open"}
          </p>
          <p className="mt-1 text-[11px] text-slate-500">
            target &lt; {metrics?.idea_to_impact_target_hours ?? 48}h · manual ~3 weeks
          </p>
        </Card>
      </div>

      <section className="space-y-3">
        <h2 className="text-sm font-medium text-slate-300">Signal feed</h2>
        {signals.signals.length === 0 ? (
          <Empty title="No signals yet" hint="Run detection against the seeded warehouse." />
        ) : (
          <div className="grid-fade space-y-2">
            {signals.signals.map((s) => (
              <Card key={String(s.id)} className="flex items-center justify-between">
                <div>
                  <p className="text-sm">
                    {String(s.metric)} · {String((s.affected_segments as Array<{ browser?: string }>)?.[0]?.browser ?? "segment")}
                  </p>
                  <p className="mt-1 font-mono text-xs text-slate-500">{when(String(s.detected_at))}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-sm text-red-400">{pct(Number(s.magnitude))}</span>
                  <Badge tone={s.status === "suppressed" ? "muted" : "warn"}>{String(s.status)}</Badge>
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-medium text-slate-300">Investigations</h2>
        {data.investigations.length === 0 ? (
          <Empty title="Nothing opened" hint="A Safari conversion drop should open one investigation." />
        ) : (
          <div className="grid-fade space-y-2">
            {data.investigations.map((inv) => (
              <Link key={inv.id} href={`/investigations/${inv.id}`} className="block">
                <Card className="transition-colors duration-150 hover:border-accent/40">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-mono text-xs text-slate-500">{inv.id}</p>
                      <p className="mt-1 text-sm">{inv.hypothesis ?? "Gathering evidence"}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      {inv.risk_tier ? <Badge tone={inv.risk_tier === "HIGH" ? "high" : "warn"}>{inv.risk_tier}</Badge> : null}
                      <Badge tone={inv.state === "AWAITING_APPROVAL" ? "warn" : "muted"}>{inv.state}</Badge>
                    </div>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
