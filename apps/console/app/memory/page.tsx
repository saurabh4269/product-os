"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ErrorState, Loading } from "@/components/ui";

const KINDS = ["customer", "product", "engineering", "organizational"] as const;

function memoryLine(card: Record<string, unknown>): string {
  if (typeof card.statement === "string" && card.statement.trim()) return card.statement;
  if (typeof card.text === "string" && card.text.trim()) return card.text;
  const structured = card.structured;
  if (structured && typeof structured === "object") {
    const o = structured as Record<string, unknown>;
    if (typeof o.reason === "string") return o.reason.replace(/_/g, " ");
    if (typeof o.statement === "string") return o.statement;
  }
  if (typeof card.reason === "string") return card.reason.replace(/_/g, " ");
  return "";
}

export default function MemoryPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.memory>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .memory()
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading label="Opening memory" />;

  return (
    <div className="page-pad">
      <h1 className="text-[26px] font-semibold tracking-tight sm:text-[32px]">Memory</h1>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        What we learned last time. The short version, kept here.
      </p>
      {data.lessons.length ? (
        <section className="mt-8 max-w-2xl rounded-[20px] border border-border bg-white p-6">
          <p className="text-[13px] font-medium text-[var(--faint)]">Lessons</p>
          <div className="mt-4 space-y-4">
            {data.lessons.map((lesson, i) => (
              <p key={String(lesson.id ?? i)} className="text-[14px] leading-6">
                {String(lesson.statement ?? lesson.title ?? JSON.stringify(lesson))}
              </p>
            ))}
          </div>
        </section>
      ) : null}
      <div className="mt-10 grid gap-5 lg:grid-cols-2">
        {KINDS.map((kind) => (
          <section key={kind} className="rounded-[20px] border border-border bg-white p-6">
            <p className="text-[13px] font-medium capitalize text-[var(--faint)]">{kind}</p>
            <div className="mt-4 space-y-4">
              {(data.memory[kind] ?? []).length === 0 ? (
                <p className="text-[14px] text-[var(--dim)]">Nothing stored yet.</p>
              ) : (
                (data.memory[kind] ?? []).map((card, i) => (
                  <p key={String(card.id ?? i)} className="text-[14px] leading-6">
                    {memoryLine(card) || "A note is stored here."}
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
