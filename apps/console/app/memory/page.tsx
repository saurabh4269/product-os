"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge, Card, ErrorState, Loading } from "@/components/ui";

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
  if (!data) return <Loading label="Opening Memory Bank" />;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Memory Bank</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--dim)]">
          Four kinds of organizational memory. Warehouse holds facts. Memory holds knowledge — retrieved when a
          later signal looks like a past one.
        </p>
      </div>
      <div className="grid-fade grid gap-4 md:grid-cols-2">
        {KINDS.map((kind) => (
          <Card key={kind}>
            <Badge tone="accent">{kind}</Badge>
            <div className="mt-4 space-y-3">
              {(data.memory[kind] ?? []).length === 0 ? (
                <p className="text-sm text-[var(--dim)]">Empty</p>
              ) : (
                (data.memory[kind] ?? []).map((card, i) => (
                  <div key={String(card.id ?? i)} className="rounded-lg border border-border p-3">
                    <p className="text-sm leading-relaxed">{String(card.statement ?? JSON.stringify(card.structured ?? card))}</p>
                    <p className="mt-2 font-mono text-[10px] text-[var(--dim)]">
                      {String(card.provenance ?? "")} · {String(card.confidence ?? "")}
                    </p>
                  </div>
                ))
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
