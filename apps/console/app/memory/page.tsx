"use client";

import { useEffect, useMemo, useState } from "react";
import { BookOpen, Building2, Code2, Lightbulb, Search, Users } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Chip, Empty, ErrorState, Loading, PageHeader } from "@/components/ui";

const KINDS = ["customer", "product", "engineering", "organizational"] as const;
type MemoryKind = (typeof KINDS)[number];

const KIND_META: Record<
  MemoryKind,
  { label: string; hint: string; icon: typeof Users }
> = {
  customer: { label: "Customer", hint: "Voice, friction, support patterns", icon: Users },
  product: { label: "Product", hint: "Features, proposals, UX", icon: Lightbulb },
  engineering: { label: "Engineering", hint: "SDK, regressions, fixes", icon: Code2 },
  organizational: { label: "Organizational", hint: "Process, activation, policy", icon: Building2 },
};

function memoryLine(card: Record<string, unknown>): string {
  if (typeof card.statement === "string" && card.statement.trim()) return card.statement;
  if (typeof card.title === "string" && card.title.trim()) {
    const body = typeof card.body === "string" ? card.body.trim() : "";
    return body ? `${card.title} — ${body}` : card.title;
  }
  if (typeof card.text === "string" && card.text.trim()) return card.text;
  const structured = card.structured;
  if (structured && typeof structured === "object") {
    const o = structured as Record<string, unknown>;
    if (typeof o.statement === "string") return o.statement;
    if (typeof o.reason === "string") return o.reason.replace(/_/g, " ");
  }
  if (typeof card.reason === "string") return card.reason.replace(/_/g, " ");
  return "";
}

function memoryProvenance(card: Record<string, unknown>): string | null {
  if (typeof card.provenance === "string" && card.provenance.trim()) return card.provenance;
  const structured = card.structured;
  if (structured && typeof structured === "object") {
    const o = structured as Record<string, unknown>;
    if (typeof o.provenance === "string" && o.provenance.trim()) return o.provenance;
  }
  return null;
}

function confidenceTone(value: unknown): "ok" | "muted" {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return "muted";
  return n >= 0.75 ? "ok" : "muted";
}

function formatConfidence(value: unknown): string | null {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return null;
  return `${Math.round(n * 100)}%`;
}

function humanizeToken(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  return value.replace(/_/g, " ");
}

function matchesQuery(text: string, q: string): boolean {
  return text.toLowerCase().includes(q.trim().toLowerCase());
}

export default function MemoryPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.memory>> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    api
      .memory()
      .then(setData)
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, []);

  const filtered = useMemo(() => {
    if (!data) return null;
    const q = query.trim();
    if (!q) return data;

    const lessons = data.lessons.filter((lesson) => {
      const blob = [
        lesson.statement,
        lesson.root_cause_family,
        ...(Array.isArray(lesson.applicable_conditions) ? lesson.applicable_conditions : []),
        lesson.linked_playbook_skill,
      ]
        .filter(Boolean)
        .join(" ");
      return matchesQuery(blob, q);
    });

    const memory = Object.fromEntries(
      KINDS.map((kind) => [
        kind,
        (data.memory[kind] ?? []).filter((card) => {
          const line = memoryLine(card);
          const prov = memoryProvenance(card) ?? "";
          return matchesQuery(`${line} ${prov}`, q);
        }),
      ]),
    ) as Record<MemoryKind, Array<Record<string, unknown>>>;

    return { lessons, memory };
  }, [data, query]);

  if (err) return <ErrorState message={err} />;
  if (!data || !filtered) return <Loading label="Memory" />;

  const totalEntries = KINDS.reduce((sum, kind) => sum + (filtered.memory[kind]?.length ?? 0), 0);
  const totalAll = KINDS.reduce((sum, kind) => sum + (data.memory[kind]?.length ?? 0), 0);
  const isEmpty = filtered.lessons.length === 0 && totalEntries === 0;

  return (
    <div className="page-pad fade-in">
      <PageHeader title="Memory" />
      <p className="mt-1 max-w-xl text-[13px] leading-relaxed text-[var(--dim)]">
        What the org learned — verified lessons and recall cards agents use during investigations.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-2.5">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-3 py-1 text-[12px] text-[var(--dim)]">
          <BookOpen className="h-3.5 w-3.5 text-accent" aria-hidden />
          <span className="tabular-nums font-medium text-foreground">{data.lessons.length}</span>
          <span>lessons</span>
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-white px-3 py-1 text-[12px] text-[var(--dim)]">
          <span className="tabular-nums font-medium text-foreground">{totalAll}</span>
          <span>recall cards</span>
        </span>
      </div>

      <label className="relative mt-6 block max-w-md">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--faint)]" aria-hidden />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search lessons and recall…"
          className="field-input w-full rounded-xl border border-border bg-white py-2.5 pl-9 pr-3 text-[14px] text-foreground outline-none transition-colors placeholder:text-[var(--faint)] focus:border-accent focus:ring-2 focus:ring-accent/20"
        />
      </label>

      {isEmpty ? (
        <Empty
          title={query.trim() ? "No matches" : "Memory is empty"}
          hint={
            query.trim()
              ? "Try a different keyword — lesson text, root cause, or provenance."
              : "Run an investigation; verified lessons land here after recall."
          }
          className="mt-12"
        />
      ) : (
        <>
          {filtered.lessons.length > 0 ? (
            <section className="surface-lg mt-10 max-w-3xl overflow-hidden">
              <div className="flex items-start gap-3 border-b border-border px-5 py-4">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent/[0.08] text-accent">
                  <BookOpen className="h-4 w-4" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-[14px] font-medium text-foreground">Lessons learned</p>
                  <p className="mt-0.5 text-[12px] text-[var(--faint)]">Verified outcomes agents recall on similar signals</p>
                </div>
                <span className="shrink-0 tabular-nums text-[13px] font-medium text-[var(--dim)]">
                  {filtered.lessons.length}
                </span>
              </div>
              <div className="space-y-2.5 px-5 py-4">
                {filtered.lessons.map((lesson, i) => {
                  const statement = String(lesson.statement ?? lesson.title ?? "");
                  const family = humanizeToken(lesson.root_cause_family);
                  const confidence = formatConfidence(lesson.confidence);
                  return (
                    <article
                      key={String(lesson.id ?? i)}
                      className="rounded-xl border border-border/70 border-l-[3px] border-l-accent/70 bg-[var(--elev)]/35 px-4 py-3.5 transition-colors hover:border-accent/20 hover:bg-white"
                    >
                      <p className="text-[14px] leading-6 text-foreground">{statement}</p>
                      {(family || confidence) && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {family ? <Chip tone="accent">{family}</Chip> : null}
                          {confidence ? (
                            <Chip tone={confidenceTone(lesson.confidence)}>{confidence} confidence</Chip>
                          ) : null}
                        </div>
                      )}
                    </article>
                  );
                })}
              </div>
            </section>
          ) : null}

          <div className="mt-10 grid gap-5 lg:grid-cols-2">
            {KINDS.map((kind) => {
              const meta = KIND_META[kind];
              const Icon = meta.icon;
              const cards = filtered.memory[kind] ?? [];
              return (
                <section key={kind} className="surface-lg overflow-hidden">
                  <div className="flex items-start gap-3 border-b border-border px-5 py-4">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent/[0.08] text-accent">
                      <Icon className="h-4 w-4" aria-hidden />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-[14px] font-medium text-foreground">{meta.label}</p>
                      <p className="mt-0.5 text-[12px] text-[var(--faint)]">{meta.hint}</p>
                    </div>
                    <span className="shrink-0 tabular-nums text-[13px] font-medium text-[var(--dim)]">{cards.length}</span>
                  </div>
                  <div className={cn("px-5 py-4", cards.length ? "space-y-2.5" : "")}>
                    {cards.length === 0 ? (
                      <p className="py-6 text-center text-[13px] text-[var(--faint)]">
                        {query.trim() ? "No matches in this category." : "Nothing stored yet."}
                      </p>
                    ) : (
                      cards.map((card, i) => {
                        const line = memoryLine(card);
                        const prov = memoryProvenance(card);
                        const confidence = formatConfidence(card.confidence);
                        return (
                          <article
                            key={String(card.id ?? i)}
                            className="rounded-xl border border-border/70 bg-[var(--elev)]/35 px-4 py-3.5 transition-colors hover:border-accent/20 hover:bg-white"
                          >
                            <p className="text-[14px] leading-6 text-foreground">{line || "—"}</p>
                            {(prov || confidence) && (
                              <div className="mt-2 flex flex-wrap items-center gap-2">
                                {prov ? <span className="text-[11px] text-[var(--faint)]">{prov}</span> : null}
                                {confidence ? <Chip tone={confidenceTone(card.confidence)}>{confidence}</Chip> : null}
                              </div>
                            )}
                          </article>
                        );
                      })
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
