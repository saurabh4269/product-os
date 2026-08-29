"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Card, Empty, ErrorState, Loading } from "@/components/ui";

export default function OpportunitiesPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.opportunities>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.opportunities().then(setData).catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;
  if (data.opportunities.length === 0) return <Empty title="No clusters" hint="Positive signals appear here." />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Opportunity board</h1>
      {data.opportunities.map((o) => (
        <Card key={String(o.id)}>
          <p className="text-sm font-medium">{String(o.title)}</p>
          <p className="mt-2 font-mono text-xs text-slate-400">
            {String(o.frequency)} customers · ${String(o.revenue_affected_usd)} · churn {String(o.churn_risk)}
          </p>
          <p className="mt-2 text-xs text-slate-500">Query: {String(o.source_query)}</p>
        </Card>
      ))}
    </div>
  );
}
