"use client";

import { useState } from "react";
import type { RoomMessage } from "@/lib/api";
import { ProofEmbed, proofFromArtifact } from "@/components/proof-embed";

const KIND_TONE: Record<string, string> = {
  evidence: "border-emerald-200/80 text-emerald-800",
  hypothesis: "border-amber-200/80 text-amber-900",
  pr: "border-sky-200/80 text-sky-800",
  risk: "border-red-200/80 text-red-700",
  risk_decision: "border-red-200/80 text-red-700",
  experiment: "border-teal-200/80 text-teal-800",
  experiment_design: "border-teal-200/80 text-teal-800",
  experiment_result: "border-teal-300/80 text-teal-900",
  product_proposal: "border-indigo-200/80 text-indigo-900",
  memory: "border-accent/30 text-accent",
  signal: "border-orange-200/80 text-orange-800",
  deny: "border-red-300 text-red-700",
  customer_brief: "border-violet-200/80 text-violet-900",
  call_evidence: "border-fuchsia-200/80 text-fuchsia-900",
  call: "border-sky-200/80 text-sky-800",
  call_feedback: "border-fuchsia-200/80 text-fuchsia-900",
  contact: "border-violet-200/80 text-violet-900",
  contact_lookup: "border-violet-200/80 text-violet-900",
  code_brief: "border-sky-200/80 text-sky-900",
  voice_context: "border-violet-200/80 text-violet-900",
  evidence_pack: "border-emerald-300/80 text-emerald-900",
  prd: "border-indigo-200/80 text-indigo-900",
  coordination: "border-sky-200/80 text-sky-900",
  classification: "border-teal-200/80 text-teal-800",
};

function headline(msg: RoomMessage): string {
  const p = msg.artifact ?? {};
  if (msg.artifact_type === "customer_brief" && typeof p.user_id === "string") {
    return `Customer Context Brief · user ${p.user_id}`;
  }
  if (msg.artifact_type === "call_evidence") {
    const s = (p.structured ?? {}) as Record<string, unknown>;
    if (typeof s.reason === "string") return `Call evidence · ${s.reason}`;
  }
  if (msg.artifact_type === "experiment_design" && typeof p.treatment === "string") {
    return `Experiment · ${p.treatment}`;
  }
  if (msg.artifact_type === "experiment_result" && typeof p.verdict === "string") {
    return `Experiment result · ${p.verdict}`;
  }
  if (msg.artifact_type === "product_proposal") {
    return typeof p.title === "string" ? p.title : "Product proposal";
  }
  if (msg.artifact_type === "evidence_pack" && typeof p.correlation_summary === "string") {
    return p.correlation_summary;
  }
  if (msg.artifact_type === "voice_context") {
    return `Voice context · ${typeof p.user_label === "string" ? p.user_label : "customer"}`;
  }
  if (msg.artifact_type === "code_brief") {
    return typeof p.issue === "string" ? `Code brief · ${p.issue.slice(0, 80)}` : "Code brief";
  }
  if (msg.artifact_type === "prd") {
    return typeof p.title === "string" ? `PRD · ${p.title}` : "Product proposal";
  }
  if (msg.artifact_type === "coordination") {
    const tier = typeof p.risk_tier === "string" ? p.risk_tier : "";
    const owners = Array.isArray(p.owners) ? p.owners.length : 0;
    return `Coordination${tier ? ` · ${tier}` : ""}${owners ? ` · ${owners} owners` : ""}`;
  }
  if (typeof p.title === "string") return p.title;
  if (typeof p.statement === "string") return p.statement;
  if (typeof p.cluster === "string") return p.cluster;
  if (typeof p.action === "string") return String(p.action);
  if (typeof p.metric === "string") return `${p.metric} ${p.delta ?? ""}`.trim();
  if (typeof p.number === "number") return `PR #${p.number}`;
  if (typeof p.reason === "string" && msg.artifact_type === "deny") return String(p.reason);
  return msg.text || (msg.artifact_type ?? "note");
}

function rows(p: Record<string, unknown>): Array<[string, string]> {
  const skip = new Set(["agentId"]);
  const out: Array<[string, string]> = [];
  for (const [k, v] of Object.entries(p)) {
    if (skip.has(k) || v == null) continue;
    if (typeof v === "object") {
      for (const [k2, v2] of Object.entries(v as Record<string, unknown>)) {
        if (v2 == null || typeof v2 === "object") continue;
        out.push([k2, String(v2)]);
      }
    } else {
      out.push([k, String(v)]);
    }
    if (out.length >= 8) break;
  }
  return out;
}

export function ArtifactCard({ msg }: { msg: RoomMessage }) {
  const [flip, setFlip] = useState(false);
  const [open, setOpen] = useState(false);
  const kind = msg.artifact_type ?? "note";
  const tone = KIND_TONE[kind] || "border-border text-[var(--dim)]";
  const fieldRows = rows((msg.artifact ?? {}) as Record<string, unknown>);
  const proof = proofFromArtifact(msg.artifact as Record<string, unknown>, msg.artifact_type);

  if (proof) {
    return (
      <article className="w-full max-w-[620px]">
        <ProofEmbed proof={proof} compact className="mt-0" />
        {msg.text && !String(msg.text).startsWith("Opened PR") ? (
          <p className="mt-1.5 text-[12px] text-[var(--dim)]">{msg.text}</p>
        ) : null}
      </article>
    );
  }

  return (
    <article className="w-full max-w-[620px]">
      <button
        type="button"
        onClick={() => setFlip((f) => !f)}
        className={
          "w-full cursor-pointer rounded-xl border bg-[var(--elev)] px-4 py-3 text-left transition hover:border-accent/40 " +
          tone
        }
        aria-pressed={flip}
      >
        {!flip ? (
          <>
            <p className="text-[11px] font-medium uppercase tracking-wide opacity-80">{kind.replace(/_/g, " ")}</p>
            <p className="mt-1 text-[14px] leading-6 text-[var(--ink)]">{headline(msg)}</p>
            <p className="mt-2 text-[11px] text-[var(--faint)]">Flip for fields</p>
          </>
        ) : (
          <>
            <p className="text-[11px] font-medium uppercase tracking-wide text-accent">{kind.replace(/_/g, " ")} · fields</p>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[12px]">
              {fieldRows.length === 0 ? (
                <dd className="col-span-2 text-[var(--dim)]">{msg.text}</dd>
              ) : (
                fieldRows.map(([k, v]) => (
                  <span key={k} className="contents">
                    <dt className="text-[var(--faint)]">{k}</dt>
                    <dd className="truncate text-[var(--ink)]">{v}</dd>
                  </span>
                ))
              )}
            </dl>
          </>
        )}
      </button>
      <button
        type="button"
        className="mt-1 text-[11px] text-[var(--faint)] hover:text-accent"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? "Collapse" : "Expand"}
      </button>
      {open ? (
        <pre className="mt-1 max-h-40 overflow-auto rounded-lg bg-[var(--elev)] p-3 text-[11px] text-[var(--dim)]">
          {JSON.stringify(msg.artifact ?? {}, null, 2)}
        </pre>
      ) : null}
    </article>
  );
}
