"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { pct } from "@/lib/utils";
import { Empty, ErrorState, Loading, PageHeader } from "@/components/ui";

export default function OutcomesPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.outcomes>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .outcomes()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading label="Outcomes" />;
  if (data.outcomes.length === 0) {
    return (
      <div className="page-pad fade-in">
        <PageHeader title="Outcomes" />
        <Empty title="None" hint="" className="mt-12" />
      </div>
    );
  }

  return (
    <div className="page-pad fade-in">
      <PageHeader title="Outcomes" />
      <div className="mt-8 max-w-md space-y-4">
        {data.outcomes.map((o) => (
          <article key={String(o.id)} className="surface-lg p-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">{String(o.metric)}</p>
            <p className="mt-2 text-[22px] font-semibold tracking-tight">
              {pct(Number(o.pre_value))} → {pct(Number(o.post_value))}
            </p>
            <p className="mt-1 text-[13px] text-ok">{String(o.verdict)}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
