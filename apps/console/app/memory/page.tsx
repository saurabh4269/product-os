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
    <div className="px-8 py-10 lg:px-12">
      <p className="text-[12px] uppercase tracking-[0.2em] text-accent">Knowledge, not facts</p>
      <h1 className="font-display mt-3 text-[48px] leading-none">Memory</h1>
      <p className="mt-4 max-w-xl text-[16px] leading-7 text-[var(--dim)]">
        The warehouse keeps numbers. This room keeps what we learned — so a later signal can find it.
      </p>
      <div className="mt-12 grid gap-12 lg:grid-cols-2">
        {KINDS.map((kind) => (
          <section key={kind}>
            <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--faint)]">{kind}</p>
            <div className="mt-4 space-y-6">
              {(data.memory[kind] ?? []).length === 0 ? (
                <p className="text-[14px] text-[var(--dim)]">Nothing stored yet.</p>
              ) : (
                (data.memory[kind] ?? []).map((card, i) => (
                  <article key={String(card.id ?? i)}>
                    <p className="font-display text-[24px] leading-8">
                      {String(card.statement ?? JSON.stringify(card.structured ?? card))}
                    </p>
                    <p className="mt-2 text-[12px] text-[var(--faint)]">
                      {String(card.provenance ?? "")}
                      {card.confidence != null ? ` · ${card.confidence}` : ""}
                    </p>
                  </article>
                ))
              )}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
