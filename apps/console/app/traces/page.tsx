"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { shortName } from "@/lib/names";
import { ErrorState, Loading } from "@/components/ui";
import { PixelSprite } from "@/components/pixel-office";

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
    <div className="px-8 py-10 lg:px-14">
      <h1 className="text-[28px] font-semibold tracking-tight">Traces</h1>
      <p className="mt-2 text-[15px] text-[var(--dim)]">Who talked to whom.</p>
      <div className="mt-8 space-y-2">
        {data.traces.map((t, i) => (
          <div key={String(t.id ?? i)} className="flex flex-wrap items-center gap-2 py-1">
            <PixelSprite name={String(t.from_agent ?? "")} scale={2} />
            <span className="text-[14px]">{shortName(String(t.from_agent ?? ""))}</span>
            <span className="text-[var(--faint)]">→</span>
            <PixelSprite name={String(t.to_agent ?? "")} scale={2} />
            <span className="text-[14px]">{shortName(String(t.to_agent ?? ""))}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
