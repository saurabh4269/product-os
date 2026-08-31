"use client";

import { cn } from "@/lib/utils";
import { usePipelineHighlight } from "@/lib/pipeline-highlight";

const TB_LANES: Array<{
  tb: string;
  name: string;
  agents: string[];
  matchStages: string[];
  adk: string;
}> = [
  {
    tb: "TB-0",
    name: "Security",
    agents: ["security_policy"],
    matchStages: ["reviews"],
    adk: "Gateway enforce · DENY exfil",
  },
  {
    tb: "TB-1",
    name: "Orchestration",
    agents: ["evidence", "root_cause", "risk", "feedback", "orchestrator"],
    matchStages: ["evidence", "root_cause", "risk", "approve"],
    adk: "Merge · ≥3 sources · HITL gate",
  },
  {
    tb: "TB-2",
    name: "Analysis",
    agents: ["signal", "investigator", "analytics", "logs", "deployment", "database"],
    matchStages: ["signal", "investigate"],
    adk: "Workflow fan-out · warehouse.read",
  },
  {
    tb: "TB-3",
    name: "Customer voice",
    agents: ["customer_voice", "customer_simulator", "research"],
    matchStages: ["investigate"],
    adk: "Voice / simulated · SDP redact",
  },
  {
    tb: "TB-4",
    name: "Code",
    agents: ["code", "test"],
    matchStages: ["code"],
    adk: "Clone → test → PR · no merge",
  },
  {
    tb: "TB-5",
    name: "Product",
    agents: ["product", "coordination", "product_intel"],
    matchStages: ["product", "experiment"],
    adk: "PRD · experiment · Calendar draft",
  },
  {
    tb: "TB-6",
    name: "Experiment",
    agents: ["experiment"],
    matchStages: ["experiment"],
    adk: "Pct rollout · guardrails",
  },
  {
    tb: "TB-7",
    name: "Learning",
    agents: ["learning"],
    matchStages: ["verify", "learn"],
    adk: "Metric window → lesson",
  },
];

/** Fleet swimlanes with trust boundaries + ADK 2 shape (from registry). */
export function TrustBoundariesDiagram({
  agents,
  className,
}: {
  agents: Array<{ id: string; room: string; role: string; tb?: string }>;
  className?: string;
}) {
  const stage = usePipelineHighlight();
  const byTb = new Map<string, string[]>();
  for (const a of agents) {
    const tb = a.tb || "TB-1";
    const list = byTb.get(tb) || [];
    list.push(a.id.replace(/_agent$/, ""));
    byTb.set(tb, list);
  }

  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="w-full min-w-[640px] border-collapse text-left text-[12px]">
        <thead>
          <tr className="border-b border-border text-[11px] uppercase tracking-wide text-[var(--faint)]">
            <th className="py-2 pr-3 font-medium">Swimlane</th>
            <th className="py-2 pr-3 font-medium">Trust boundary</th>
            <th className="py-2 pr-3 font-medium">Agents</th>
            <th className="py-2 font-medium">ADK 2 shape</th>
          </tr>
        </thead>
        <tbody>
          {TB_LANES.map((lane) => {
            const hot = stage ? lane.matchStages.includes(stage) : false;
            const regAgents = byTb.get(lane.tb) ?? [...lane.agents];
            return (
              <tr
                key={lane.tb}
                className={cn(
                  "border-b border-border/60 transition-colors",
                  hot && "bg-[color-mix(in_srgb,var(--accent)_8%,white)]"
                )}
              >
                <td className="py-2.5 pr-3 font-semibold text-foreground">{lane.name}</td>
                <td className="py-2.5 pr-3 font-mono text-[11px] text-accent">{lane.tb}</td>
                <td className="py-2.5 pr-3">
                  <div className="flex flex-wrap gap-1">
                    {regAgents.map((id) => (
                      <span key={id} className="rounded-md bg-[#eef2ee] px-1.5 py-0.5 font-medium">
                        {id}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="py-2.5 text-[var(--dim)]">{lane.adk}</td>
              </tr>
            );
          })}
          <tr className="bg-[#eef2ee]">
            <td className="py-2.5 pr-3 font-semibold">Govern</td>
            <td className="py-2.5 pr-3 font-mono text-[11px]">HITL</td>
            <td className="py-2.5 pr-3 font-medium">You (operator)</td>
            <td className="py-2.5 text-[var(--dim)]">RequestInput · approve modal · OAuth consent</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
