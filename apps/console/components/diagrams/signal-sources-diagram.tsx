"use client";

import { cn } from "@/lib/utils";
import { usePipelineHighlight } from "@/lib/pipeline-highlight";

/** Push vs pull signal sources for Connect desk. */
export function SignalSourcesDiagram({
  className,
  selected,
  onSelect,
}: {
  className?: string;
  selected?: "push" | "pull" | null;
  onSelect?: (side: "push" | "pull" | null) => void;
}) {
  const stage = usePipelineHighlight();
  const hotPush = stage === "signal";
  const hotPull = stage === "investigate" || stage === "evidence";

  return (
    <div className={cn("grid gap-4 sm:grid-cols-2", className)}>
      <button
        type="button"
        onClick={() => onSelect?.(selected === "push" ? null : "push")}
        className={cn(
          "rounded-2xl border p-4 text-left transition-all duration-300",
          selected === "push" && "ring-2 ring-accent/20",
          hotPush ? "border-accent/40 bg-[color-mix(in_srgb,var(--accent)_6%,white)]" : "border-border bg-white",
          selected !== "push" && "hover:border-accent/30"
        )}
      >
        <p className="text-[11px] font-medium uppercase tracking-wide text-accent">Push (real-time)</p>
        <p className="mt-1 text-[14px] font-semibold">Tenant initiates</p>
        <ul className="mt-3 space-y-2 text-[13px] text-[var(--dim)]">
          <li>
            <code className="text-[12px]">POST /api/t/&#123;id&#125;/signals</code> · Cove ingest
          </li>
          <li>
            <code className="text-[12px]">POST /api/t/&#123;id&#125;/voice</code>
          </li>
          <li>Checkout hang · feedback webhook</li>
        </ul>
      </button>
      <button
        type="button"
        onClick={() => onSelect?.(selected === "pull" ? null : "pull")}
        className={cn(
          "rounded-2xl border p-4 text-left transition-all duration-300",
          selected === "pull" && "ring-2 ring-accent/20",
          hotPull ? "border-accent/40 bg-[color-mix(in_srgb,var(--accent)_6%,white)]" : "border-border bg-white",
          selected !== "pull" && "hover:border-accent/30"
        )}
      >
        <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--faint)]">Pull (warehouse)</p>
        <p className="mt-1 text-[14px] font-semibold">OS reads facts</p>
        <ul className="mt-3 space-y-2 text-[13px] text-[var(--dim)]">
          <li>GA4 → BQ → Signal agent detect</li>
          <li>
            <code className="text-[12px]">loop_raw</code> / <code className="text-[12px]">loop_metrics</code>
          </li>
          <li>Pub/Sub loop.signals (scheduled)</li>
        </ul>
      </button>
    </div>
  );
}

/** Functional swimlanes: Detect → Investigate → Decide → Act → Govern → Verify. */
export function FleetSwimlanes({
  agents,
  workflows,
  className,
  selected,
  onSelect,
}: {
  agents: Array<{ id: string; room: string; role: string; tb?: string }>;
  workflows?: {
    investigation_fanout?: string;
    proposal_critique?: string;
    investigators_fanout?: string[];
  } | null;
  className?: string;
  selected?: string | null;
  onSelect?: (lane: string | null) => void;
}) {
  const stage = usePipelineHighlight();

  const lanes = [
    { title: "Detect", subtitle: "Signal", items: ["signal"], adk: "never investigates", match: ["signal"] },
    {
      title: "Investigate",
      subtitle: "Fan-out",
      items: workflows?.investigators_fanout?.map((id) => id.replace(/_agent$/, "")) ?? [
        "analytics",
        "logs",
        "deploy",
        "voice",
        "code",
      ],
      adk: "Workflow + JoinNode",
      match: ["investigate"],
    },
    {
      title: "Decide",
      subtitle: "Diagnose",
      items: ["evidence", "root_cause"],
      adk: "≥3 independence groups",
      match: ["evidence", "root_cause"],
    },
    {
      title: "Act",
      subtitle: "BUG vs FEATURE",
      items: ["code", "product", "risk"],
      adk: "Type A / B fork",
      match: ["code", "product", "experiment", "risk"],
    },
    { title: "Govern", subtitle: "HITL", items: ["you"], adk: "HIGH gate", match: ["approve"] },
    { title: "Verify", subtitle: "Learn", items: ["learning"], adk: "metric window", match: ["verify", "learn"] },
  ];

  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex flex-wrap gap-2 text-[12px] text-[var(--dim)]">
        <span className="rounded-full border border-border bg-white px-2.5 py-1">
          investigation_fanout: <strong>{workflows?.investigation_fanout || "catalog"}</strong>
        </span>
        <span className="rounded-full border border-border bg-white px-2.5 py-1">
          proposal_critique: <strong>{workflows?.proposal_critique || "catalog"}</strong>
        </span>
        <span className="rounded-full border border-border bg-white px-2.5 py-1">{agents.length} registry agents</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] border-collapse text-[12px]">
          <thead>
            <tr className="text-[11px] uppercase tracking-wide text-[var(--faint)]">
              <th className="pb-2 pr-3 text-left font-medium">Lane</th>
              <th className="pb-2 pr-3 text-left font-medium">Agents</th>
              <th className="pb-2 text-left font-medium">ADK 2</th>
            </tr>
          </thead>
          <tbody>
            {lanes.map((lane) => {
              const hot = stage ? lane.match.some((m) => m === stage) : false;
              const picked = selected === lane.title;
              return (
                <tr
                  key={lane.title}
                  onClick={() => onSelect?.(picked ? null : lane.title)}
                  className={cn(
                    "cursor-pointer border-t border-border/60 transition-colors",
                    (hot || picked) && "bg-[color-mix(in_srgb,var(--accent)_8%,white)]",
                    picked && "ring-1 ring-inset ring-accent/25"
                  )}
                >
                  <td className="py-2.5 pr-3 align-top">
                    <p className="font-semibold">{lane.title}</p>
                    <p className="text-[11px] text-[var(--faint)]">{lane.subtitle}</p>
                  </td>
                  <td className="py-2.5 pr-3">
                    <div className="flex flex-wrap gap-1">
                      {lane.items.map((item) => (
                        <span key={item} className="rounded-md bg-[#eef2ee] px-1.5 py-0.5 font-medium">
                          {item}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="py-2.5 text-[var(--dim)]">{lane.adk}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
