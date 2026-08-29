"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge, Card, ErrorState, Loading } from "@/components/ui";
import { Pixel } from "@/components/pixel-office";

export default function TracesPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.traces>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .traces()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading label="Opening traces" />;

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Observability</h1>
        <p className="mt-2 text-sm text-[var(--dim)]">
          A2A reasoning hops and policy verdicts. OpenTelemetry-shaped locally; Cloud Trace in GCP.
        </p>
      </div>
      <section className="space-y-2">
        <h2 className="text-sm font-medium">Reasoning chain</h2>
        {data.traces.map((t, i) => (
          <Card key={String(t.id ?? i)} className="flex items-center justify-between gap-3 py-3">
            <div className="flex items-center gap-2">
              <Pixel name={String(t.from_agent ?? "")} />
              <span className="text-sm">{String(t.from_agent)}</span>
              <span className="text-[var(--dim)]">→</span>
              <Pixel name={String(t.to_agent ?? "")} />
              <span className="text-sm">{String(t.to_agent)}</span>
            </div>
            <div className="text-right">
              <Badge>{String(t.trust_boundary ?? "")}</Badge>
              <p className="mt-1 max-w-sm truncate font-mono text-[10px] text-[var(--dim)]">{String(t.summary ?? "")}</p>
            </div>
          </Card>
        ))}
      </section>
      <section className="space-y-2">
        <h2 className="text-sm font-medium">Policy verdicts</h2>
        {data.verdicts.map((v, i) => (
          <Card key={String(v.id ?? i)} className="flex items-center justify-between">
            <p className="text-sm">
              {String(v.agent_identity)} · {String(v.tool)}
            </p>
            <Badge tone={v.verdict === "DENY" || v.verdict === "BLOCK" ? "high" : "ok"}>{String(v.verdict)}</Badge>
          </Card>
        ))}
      </section>
    </div>
  );
}
