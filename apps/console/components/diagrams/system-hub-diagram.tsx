"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { usePipelineHighlight } from "@/lib/pipeline-highlight";
import { DiagramDetailPanel } from "@/components/diagrams/diagram-detail-panel";

const ARM_DETAILS: Record<string, { role: string; tools: string }> = {
  Analytics: { role: "Warehouse metrics, funnel slices", tools: "warehouse.read · BQ" },
  Logs: { role: "Error rates, stack traces", tools: "warehouse.read · logs" },
  Deploy: { role: "Release correlation", tools: "deployment.read" },
  Database: { role: "Query latency, row counts", tools: "warehouse.read" },
  Customer: { role: "Voice + feedback themes", tools: "voice · SDP redact" },
  Code: { role: "Repo diff, test status", tools: "github.read · clone" },
};

/** Tier B — three-piece system hub (User → Console → agents + WS). */
export function SystemHubDiagram({ className }: { className?: string }) {
  const stage = usePipelineHighlight();
  const hotConsole = Boolean(stage);
  const hotWs = stage === "investigate" || stage === "evidence" || stage === "approve";

  return (
    <div className={cn("overflow-x-auto rounded-2xl border border-border bg-[#f5f5f7] p-4", className)}>
      <pre
        className="min-w-[32rem] font-mono text-[12px] leading-6 text-[#1d1d1f]"
        aria-label="System hub diagram"
      >
        <span className="text-[#86868b]">{"  You (operator)"}</span>
        {"\n       │ click Run · approve modal\n       ▼\n"}
        <span className={cn(hotConsole && "rounded bg-[#0071e3]/15 px-1 text-[#0071e3]")}>
          {"  ┌─ Console (Next.js) ─────────────────────┐"}
        </span>
        {"\n  │  DemoRunner · PipelineBoard · Rooms    │\n  └──────────────┬──────────────────────────┘\n                 │ REST + "}
        <span className={cn(hotWs && "text-[#0071e3] font-semibold")}>WebSocket /ws</span>
        {"\n                 ▼\n  ┌─ Cloud Run "}
        <code>loop</code>
        {" ─────────────────────────────┐\n  │  LoopEngine · SQLite · agent_callback   │\n  │       │ fan-out investigators          │\n  │       ▼                                 │\n  │  Signal → Investigate → Evidence → …    │\n  └──────────────┬──────────────────────────┘\n                 │ optional\n                 ▼\n  ┌─ Cloud Run "}
        <code>loop-adk</code>
        {" ─ ADK 2 fleet when creds exist ─┐\n  └───────────────────────────────────────────┘\n                 │\n                 ▼ push events\n       Console updates live (no refresh)"}
      </pre>
    </div>
  );
}

/** Hybrid engine deployment inset (Tier C). */
export function HybridEngineDiagram({ className }: { className?: string }) {
  return (
    <div className={cn("grid gap-3 sm:grid-cols-2", className)}>
      <div className="rounded-2xl border border-border bg-white p-4">
        <p className="text-[11px] font-medium uppercase tracking-wide text-accent">Primary · loop</p>
        <p className="mt-1 text-[15px] font-semibold">Console + API + LoopEngine</p>
        <p className="mt-2 text-[13px] leading-5 text-[var(--dim)]">
          Hosted path runs without Gemini on cold start. Deterministic investigate → evidence → gate → PR.
        </p>
      </div>
      <div className="rounded-2xl border border-dashed border-border bg-[#eef2ee] p-4">
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--faint)]">Optional · loop-adk</p>
        <p className="mt-1 text-[15px] font-semibold">ADK 2 App fleet + Gemini</p>
        <p className="mt-2 text-[13px] leading-5 text-[var(--dim)]">
          When worker URL and creds exist — Workflow + JoinNode + RequestInput HITL. Same pipeline shape.
        </p>
      </div>
    </div>
  );
}

/** Event-driven side paths beyond “user clicked Run”. */
export function EventPathsDiagram({
  className,
  selected,
  onSelect,
}: {
  className?: string;
  selected?: string | null;
  onSelect?: (id: string | null) => void;
}) {
  const stage = usePipelineHighlight();
  const rows = [
    { id: "cove", label: "Cove checkout hang", path: "POST /api/t/acme/signals", hot: stage === "signal", detail: "Tenant webhook posts a signal; Signal agent opens or joins an investigation room." },
    { id: "demo", label: "Demo run", path: "POST /api/demo/run", hot: stage === "signal", detail: "One-click fixture signal for eval — same pipeline as production ingest." },
    { id: "callback", label: "Agent callback → UI", path: "POST /api/agent_callback → WS", hot: stage === "investigate", detail: "Worker posts progress; console WS pushes agent_presence and messages without refresh." },
    { id: "bq", label: "GA4 → BQ → warehouse", path: "pull · warehouse_mode: auto", hot: stage === "investigate", detail: "Scheduled pull reads facts tables; investigators query via warehouse.read." },
    { id: "hitl", label: "HIGH approval", path: "WS approval_required → modal", hot: stage === "approve", detail: "Risk tier HIGH blocks execute until operator approves in modal." },
    { id: "oauth", label: "Workspace OAuth", path: "Connect → Gmail draft · Calendar", hot: false, detail: "Operator consent for Calendar holds and draft emails — not auto-send." },
  ];

  return (
    <div className={cn("space-y-2 text-[13px]", className)}>
      {rows.map((row) => (
        <button
          key={row.id}
          type="button"
          onClick={() => onSelect?.(selected === row.id ? null : row.id)}
          className={cn(
            "flex w-full flex-wrap items-baseline justify-between gap-2 rounded-xl border px-3 py-2 text-left transition-all",
            selected === row.id && "border-accent bg-[color-mix(in_srgb,var(--accent)_8%,white)] ring-2 ring-accent/15",
            selected !== row.id && row.hot && "border-accent/40 bg-[color-mix(in_srgb,var(--accent)_6%,white)]",
            selected !== row.id && !row.hot && "border-border bg-white hover:border-accent/25"
          )}
        >
          <span className="font-medium text-foreground">{row.label}</span>
          <code className="text-[11px] text-[var(--dim)]">{row.path}</code>
        </button>
      ))}
      {selected ? (
        <p className="rounded-xl bg-white px-3 py-2 text-[13px] leading-5 text-[var(--dim)]">
          {rows.find((r) => r.id === selected)?.detail}
        </p>
      ) : (
        <p className="text-[12px] text-[var(--faint)]">Tap a path to see what fires</p>
      )}
    </div>
  );
}

/** Investigation fan-out — ParallelAgent story in ADK 2 terms. */
export function InvestigationFanoutDiagram({ className }: { className?: string }) {
  const stage = usePipelineHighlight();
  const hot = stage === "investigate" || stage === "evidence";
  const arms = ["Analytics", "Logs", "Deploy", "Database", "Customer", "Code"];
  const [picked, setPicked] = useState<string | null>(null);
  const detail = picked ? ARM_DETAILS[picked] : null;

  return (
    <div className={cn("space-y-3", className)}>
      <div className={cn("rounded-2xl border border-border bg-white p-4", hot && "ring-2 ring-accent/20")}>
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--faint)]">investigation_fanout</p>
        <p className="mt-1 text-[14px] font-semibold">Workflow + JoinNode — tap an arm</p>
        <div className="mt-4 flex flex-col items-center gap-2">
          <div className="rounded-lg bg-[#eef2ee] px-3 py-1.5 text-[12px] font-medium">Investigator dispatch</div>
          <div className="grid w-full max-w-lg grid-cols-3 gap-2 sm:grid-cols-6">
            {arms.map((a) => (
              <button
                key={a}
                type="button"
                onClick={() => setPicked((p) => (p === a ? null : a))}
                className={cn(
                  "rounded-lg border px-2 py-1.5 text-center text-[11px] font-medium transition-all",
                  picked === a && "border-accent bg-accent text-white shadow-sm",
                  picked !== a && hot && "border-accent/30 bg-[color-mix(in_srgb,var(--accent)_6%,white)]",
                  picked !== a && !hot && "border-border bg-white hover:border-accent/30"
                )}
              >
                {a}
              </button>
            ))}
          </div>
          <div className="text-[var(--faint)]">▼</div>
          <div
            className={cn(
              "rounded-lg px-4 py-2 text-[12px] font-medium",
              stage === "evidence" ? "bg-accent text-white" : "bg-[#eef2ee] text-foreground"
            )}
          >
            JoinNode → Evidence agent (≥3 independence groups)
          </div>
        </div>
      </div>
      {detail && picked ? (
        <DiagramDetailPanel
          title={picked}
          subtitle="Investigator arm"
          body={detail.role}
          meta={[{ label: "Tools", value: detail.tools }]}
          onClear={() => setPicked(null)}
        />
      ) : null}
    </div>
  );
}

/** Workflow catalog detail panel. */
export function WorkflowDetailPanel({
  workflows,
  className,
}: {
  workflows: {
    adk_version?: string;
    investigation_fanout?: string;
    proposal_critique?: string;
    investigators_fanout?: string[];
    adopted_patterns?: string[];
    hitl?: Record<string, unknown>;
    enterprise?: Record<string, string>;
  } | null;
  className?: string;
}) {
  if (!workflows) return null;
  const patterns = workflows.adopted_patterns ?? [];
  return (
    <div className={cn("rounded-2xl border border-border bg-[#eef2ee] px-4 py-3 text-[13px]", className)}>
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--faint)]">GET /api/workflows</p>
      <dl className="mt-2 grid gap-2 sm:grid-cols-2">
        <div>
          <dt className="text-[var(--faint)]">ADK</dt>
          <dd className="font-medium">{workflows.adk_version || "2.x"}</dd>
        </div>
        <div>
          <dt className="text-[var(--faint)]">investigation_fanout</dt>
          <dd className="font-medium">{workflows.investigation_fanout || "—"}</dd>
        </div>
        <div>
          <dt className="text-[var(--faint)]">proposal_critique</dt>
          <dd className="font-medium">{workflows.proposal_critique || "—"}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-[var(--faint)]">adopted_patterns</dt>
          <dd className="mt-1 flex flex-wrap gap-1">
            {patterns.map((p) => (
              <span key={p} className="rounded-full bg-white px-2 py-0.5 text-[11px]">
                {p}
              </span>
            ))}
          </dd>
        </div>
      </dl>
    </div>
  );
}
