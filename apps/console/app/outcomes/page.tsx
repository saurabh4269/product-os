"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { pct } from "@/lib/utils";
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
    return <Empty title="No outcomes yet." hint="Approve something in a room to close a loop." />;
  }

  return (
    <div className="px-8 py-10 lg:px-14">
      <h1 className="text-[28px] font-semibold tracking-tight">Outcomes</h1>
      <div className="mt-8 max-w-md space-y-6">
        {data.outcomes.map((o) => (
          <article key={String(o.id)}>
            <p className="text-[13px] text-[var(--faint)]">{String(o.metric)}</p>
            <p className="mt-1 text-[22px] font-semibold">
              {pct(Number(o.pre_value))} → {pct(Number(o.post_value))}
            </p>
            <p className="mt-1 text-[13px] text-ok">{String(o.verdict)}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
