"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ErrorState, Loading } from "@/components/ui";

const KINDS = ["customer", "product", "engineering", "organizational"] as const;

export default function MemoryPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.memory>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .memory()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading label="Opening memory" />;

  return (
    <div className="px-8 py-10 lg:px-14">
      <h1 className="text-[28px] font-semibold tracking-tight">Memory</h1>
      <p className="mt-2 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        What we learned last time. Numbers stay in the warehouse; this is the short version we keep.
      </p>
      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        {KINDS.map((kind) => (
          <section key={kind} className="rounded-2xl border border-border bg-white p-5">
            <p className="text-[13px] font-medium capitalize text-[var(--faint)]">{kind}</p>
            <div className="mt-4 space-y-4">
              {(data.memory[kind] ?? []).length === 0 ? (
                <p className="text-[14px] text-[var(--dim)]">Nothing stored yet.</p>
              ) : (
                (data.memory[kind] ?? []).map((card, i) => (
                  <p key={String(card.id ?? i)} className="text-[14px] leading-6">
                    {String(card.statement ?? JSON.stringify(card.structured ?? card))}
                  </p>
                ))
              )}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
