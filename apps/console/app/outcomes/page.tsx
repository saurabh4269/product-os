"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { pct, when } from "@/lib/utils";
import { Badge, Card, Empty, ErrorState, Loading } from "@/components/ui";

export default function OutcomesPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.outcomes>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.outcomes().then(setData).catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;
  if (data.outcomes.length === 0) {
    return <Empty title="No verified outcomes" hint="Approve a gated action in a room to close a loop." />;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Outcome ledger</h1>
      {data.outcomes.map((o) => (
        <Card key={String(o.id)}>
          <div className="flex items-center justify-between">
            <p className="text-sm">{String(o.metric)}</p>
            <Badge tone="ok">{String(o.verdict)}</Badge>
          </div>
          <p className="mt-3 font-mono text-sm">
            {pct(Number(o.pre_value))} → {pct(Number(o.post_value))} · Δ {pct(Number(o.delta))}
          </p>
          <p className="mt-2 text-xs text-[var(--dim)]">{when(String(o.measured_at))}</p>
        </Card>
      ))}
    </div>
  );
}
