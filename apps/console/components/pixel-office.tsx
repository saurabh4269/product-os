"use client";

import { cn } from "@/lib/utils";

export const AGENT_COLOR: Record<string, string> = {
  signal_agent: "#5e6ad2",
  investigator_agent: "#7c8aff",
  orchestrator: "#d4a27f",
  analytics_agent: "#8b7cf6",
  logs_agent: "#e2a03f",
  deployment_agent: "#eb5757",
  database_agent: "#4cb782",
  customer_voice_agent: "#5ec8c8",
  customer_simulator: "#9ad7d7",
  feedback_agent: "#6ec8a0",
  evidence_agent: "#a78bfa",
  root_cause_agent: "#f472b6",
  risk_agent: "#f5c16c",
  code_agent: "#94a3b8",
  test_agent: "#64748b",
  product_agent: "#60a5fa",
  product_intelligence_agent: "#93c5fd",
  experiment_agent: "#38bdf8",
  learning_agent: "#4cb782",
  security_policy_agent: "#eb5757",
  coordination_agent: "#d4a27f",
  consent_agent: "#c4b5fd",
  decision_agent: "#e2a03f",
  you: "#ececee",
};

function PixelSprite({ color, working }: { color: string; working?: boolean }) {
  const cells = [0, 1, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 1, 0, 0, 1];
  return (
    <span
      className={cn("pixel-agent inline-grid grid-cols-4 gap-px", working && "is-working")}
      style={{ width: 16, height: 16 }}
      aria-hidden
    >
      {cells.map((on, i) => (
        <span key={i} style={{ background: on ? color : `${color}22` }} />
      ))}
    </span>
  );
}

export function Pixel({ name, size = 12 }: { name: string; size?: number }) {
  const color = AGENT_COLOR[name] ?? "#64748b";
  return (
    <span className="inline-grid grid-cols-2 gap-px" style={{ width: size, height: size }} aria-hidden>
      {[0, 1, 2, 3].map((i) => (
        <span key={i} style={{ background: i % 2 ? color : `${color}88` }} />
      ))}
    </span>
  );
}

export function PixelOffice({
  members,
  working,
}: {
  members: string[];
  working: Set<string>;
}) {
  const shown = members.filter((m) => m !== "system").slice(0, 12);
  return (
    <div className="office-floor relative overflow-hidden rounded-xl border border-border px-4 py-3">
      <div className="mb-2 flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--dim)]">Agents in the room</p>
        <p className="font-mono text-[10px] text-[var(--dim)]">{working.size} working</p>
      </div>
      <div className="flex flex-wrap items-end gap-5">
        {shown.map((name) => {
          const color = AGENT_COLOR[name] ?? "#64748b";
          const isWork = working.has(name);
          return (
            <div key={name} className="flex flex-col items-center gap-1">
              <PixelSprite color={color} working={isWork} />
              <span className="max-w-[72px] truncate font-mono text-[9px] text-[var(--dim)]">
                {name.replace(/_agent$/, "").replace(/_/g, " ")}
              </span>
              <span className={cn("h-1 w-1 rounded-full", isWork ? "bg-ok" : "bg-white/15")} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
