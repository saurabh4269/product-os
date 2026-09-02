"use client";

import { cn } from "@/lib/utils";

export type StructuredEvidence = {
  reason?: string;
  severity?: string;
  purchase_intent?: string;
  friction?: string;
  competitor_mentioned?: string | boolean;
  feature_request?: string | boolean;
  willing_to_retry?: string | boolean;
  confidence?: number | string;
  transcript?: string;
  [key: string]: unknown;
};

const FIELDS: Array<{ key: keyof StructuredEvidence; label: string }> = [
  { key: "reason", label: "Reason" },
  { key: "severity", label: "Severity" },
  { key: "purchase_intent", label: "Intent" },
  { key: "friction", label: "Friction" },
  { key: "competitor_mentioned", label: "Competitor" },
  { key: "feature_request", label: "Feature ask" },
  { key: "willing_to_retry", label: "Will retry" },
  { key: "confidence", label: "Confidence" },
];

function formatVal(v: unknown) {
  if (v == null || v === "") return null;
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return v <= 1 && v >= 0 ? `${Math.round(v * 100)}%` : String(v);
  return String(v);
}

/** Customer Voice diagnostic output — structured JSON, not a survey. */
export function StructuredEvidenceCard({
  structured,
  title = "Customer voice · structured evidence",
  transcript,
  className,
}: {
  structured?: StructuredEvidence | Record<string, unknown> | null;
  title?: string;
  transcript?: string | null;
  className?: string;
}) {
  const data = (structured || {}) as StructuredEvidence;
  const rows = FIELDS.map(({ key, label }) => {
    const val = formatVal(data[key]);
    return val ? { label, val } : null;
  }).filter(Boolean) as Array<{ label: string; val: string }>;

  const tx = transcript || (typeof data.transcript === "string" ? data.transcript : null);

  if (!rows.length && !tx) return null;

  return (
    <article
      className={cn(
        "overflow-hidden rounded-xl border border-violet-200/80 bg-[#fbfbfc] shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]",
        className
      )}
    >
      <div className="border-b border-border bg-white px-3 py-2">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-violet-800">{title}</p>
        <p className="text-[10px] text-[var(--faint)]">Diagnostic evidence — not a survey response</p>
      </div>
      {rows.length ? (
        <dl className="grid grid-cols-2 gap-x-3 gap-y-2 px-3 py-2.5 text-[12px] sm:grid-cols-4">
          {rows.map(({ label, val }) => (
            <div key={label}>
              <dt className="text-[10px] font-medium uppercase tracking-wide text-[var(--faint)]">{label}</dt>
              <dd className="mt-0.5 font-medium text-foreground">{val}</dd>
            </div>
          ))}
        </dl>
      ) : null}
      {tx ? (
        <blockquote className="border-t border-border/70 px-3 py-2 text-[12px] leading-5 text-[var(--dim)]">
          {tx}
        </blockquote>
      ) : null}
    </article>
  );
}

/** Pull structured block from a room message artifact. */
export function structuredFromArtifact(artifact?: Record<string, unknown> | null): StructuredEvidence | null {
  if (!artifact) return null;
  const nested = artifact.structured;
  if (nested && typeof nested === "object" && !Array.isArray(nested)) {
    return nested as StructuredEvidence;
  }
  const keys = new Set(FIELDS.map((f) => f.key));
  const has = Object.keys(artifact).some((k) => keys.has(k as keyof StructuredEvidence));
  return has ? (artifact as StructuredEvidence) : null;
}
