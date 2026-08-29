"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { pct, when } from "@/lib/utils";
import { Empty, ErrorState, Loading } from "@/components/ui";

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
  if (!data) return <Loading />;
  if (data.outcomes.length === 0) {
    return <Empty title="No outcomes yet." hint="Approve a gate in a room to close a loop." />;
  }

  return (
    <div className="px-8 py-10 lg:px-12">
      <p className="text-[12px] uppercase tracking-[0.2em] text-accent">Did it work</p>
      <h1 className="font-display mt-3 text-[48px] leading-none">Outcomes</h1>
      <div className="mt-10 max-w-xl space-y-8">
        {data.outcomes.map((o) => (
          <article key={String(o.id)}>
            <p className="text-[13px] text-[var(--faint)]">{String(o.metric)}</p>
            <p className="font-display mt-1 text-[36px] leading-none">
              {pct(Number(o.pre_value))} → {pct(Number(o.post_value))}
            </p>
            <p className="mt-2 text-[13px] text-ok">{String(o.verdict)}</p>
            <p className="mt-1 text-[12px] text-[var(--faint)]">{when(String(o.measured_at))}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
