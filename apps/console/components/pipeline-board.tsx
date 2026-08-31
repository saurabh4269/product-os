"use client";

import Link from "next/link";
import { usePipelineHighlight } from "@/lib/pipeline-highlight";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useDemoGuide } from "@/lib/demo-guide-context";
import { useGlobalWs } from "@/lib/use-global-ws";
import { AgentBadge } from "@/components/agent-badge";
import { PipelineFlowOverlay } from "@/components/pipeline-flow-overlay";
import { cn } from "@/lib/utils";

const LABELS: Record<string, string> = {
  signal: "Signal",
  investigate: "Investigate",
  evidence: "Evidence",
  root_cause: "Root cause",
  code: "Code",
  product: "Product",
  experiment: "Experiment",
  risk: "Risk",
  approve: "Approve",
  verify: "Verify",
  learn: "Learn",
};

const STAGE_AGENTS: Record<string, string[]> = {
  signal: ["signal_agent"],
  investigate: ["analytics_agent", "logs_agent", "deployment_agent", "database_agent", "customer_voice_agent"],
  evidence: ["evidence_agent"],
  root_cause: ["root_cause_agent"],
  code: ["code_agent", "test_agent"],
  product: ["product_agent"],
  risk: ["risk_agent"],
  approve: ["risk_agent"],
  verify: ["learning_agent"],
  learn: ["learning_agent"],
};

const AGENT_COLUMNS: Array<{ id: string; label: string; stages: string[] }> = [
  { id: "signal_agent", label: "Signal", stages: ["signal"] },
  { id: "analytics_agent", label: "Analytics", stages: ["investigate"] },
  { id: "logs_agent", label: "Logs", stages: ["investigate"] },
  { id: "deployment_agent", label: "Deploy", stages: ["investigate"] },
  { id: "evidence_agent", label: "Evidence", stages: ["evidence"] },
  { id: "root_cause_agent", label: "Root cause", stages: ["root_cause"] },
  { id: "code_agent", label: "Code", stages: ["code"] },
  { id: "product_agent", label: "Product", stages: ["product", "experiment"] },
  { id: "risk_agent", label: "Risk / Approve", stages: ["risk", "approve"] },
  { id: "learning_agent", label: "Learning", stages: ["verify", "learn"] },
];

const VIEW_KEY = "loop-pipeline-view";

type Card = {
  room_id: string;
  title: string;
  stage: string;
  kind: string;
  tenant_product?: string | null;
  awaiting_approval?: boolean;
  pr_url?: string | null;
  evidence_snippet?: string | null;
  calendar_snippet?: string | null;
  voice_snippet?: string | null;
  verified?: boolean;
  denied?: boolean;
  active_agents?: string[];
};

function cardAgent(c: Card): string {
  if (c.active_agents?.[0]) return c.active_agents[0];
  const defaults = STAGE_AGENTS[c.stage];
  return defaults?.[0] || "orchestrator_agent";
}

function statusChip(c: Card) {
  if (c.awaiting_approval) return { label: "Approve", tone: "accent" as const };
  if (c.denied) return { label: "Held", tone: "danger" as const };
  if (c.verified) return { label: "Verified", tone: "ok" as const };
  if (c.pr_url) return { label: "PR", tone: "ok" as const };
  return { label: LABELS[c.stage] || c.stage, tone: "faint" as const };
}

function PipelineCard({
  c,
  moved,
  demoFocus,
  onShowFlow,
}: {
  c: Card;
  moved?: boolean;
  demoFocus?: boolean;
  onShowFlow?: () => void;
}) {
  const agent = c.active_agents?.[0] || cardAgent(c);
  const chip = statusChip(c);
  const working = Boolean(c.active_agents?.length);
  return (
    <div
      className={cn(
        "rounded-xl border bg-white shadow-sm transition-all duration-500 hover:border-accent/40",
        c.denied && "border-danger/40 bg-red-50/40",
        c.verified && "border-ok/40",
        c.awaiting_approval && "border-accent/50 ring-2 ring-accent/30",
        demoFocus && !c.awaiting_approval && "ring-2 ring-accent/35 border-accent/40",
        !c.denied && !c.verified && !c.awaiting_approval && !demoFocus && "border-border",
        moved && "scale-[1.02]"
      )}
    >
      <Link href={`/rooms/${c.room_id}`} className="block px-3 py-2.5">
        <div className="flex items-start gap-2">
          <AgentBadge name={agent} working={working} size={22} />
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium leading-5 text-foreground line-clamp-2">{c.title}</p>
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-medium",
                  chip.tone === "accent" && "bg-accent/10 text-accent",
                  chip.tone === "ok" && "bg-ok/10 text-ok",
                  chip.tone === "danger" && "bg-danger/10 text-danger",
                  chip.tone === "faint" && "bg-[var(--elev)] text-[var(--faint)]"
                )}
              >
                {chip.label}
              </span>
              {c.calendar_snippet ? (
                <span className="truncate text-[10px] text-accent">{c.calendar_snippet}</span>
              ) : null}
            </div>
          </div>
        </div>
      </Link>
      <div className="flex items-center justify-between border-t border-border/60 px-2 py-1">
        <button
          type="button"
          className="text-[10px] font-medium text-[var(--faint)] hover:text-accent"
          onClick={(e) => {
            e.preventDefault();
            onShowFlow?.();
          }}
        >
          Flow
        </button>
        {c.pr_url ? (
          <a
            href={c.pr_url}
            className="text-[10px] font-medium text-ok hover:underline"
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
          >
            PR →
          </a>
        ) : null}
      </div>
    </div>
  );
}

export function PipelineBoard() {
  const demo = useDemoGuide();
  const wsStage = usePipelineHighlight();
  const { tick } = useGlobalWs();
  const [view, setView] = useState<"stage" | "agent">("stage");
  const [columns, setColumns] = useState<string[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [flowCard, setFlowCard] = useState<Card | null>(null);
  const prevStages = useRef<Record<string, string>>({});

  useEffect(() => {
    try {
      const v = localStorage.getItem(VIEW_KEY);
      if (v === "agent" || v === "stage") setView(v);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    api
      .pipeline()
      .then((r) => {
        setColumns(r.columns);
        setCards(r.cards);
        setLoaded(true);
      })
      .catch(() => {
        setColumns([]);
        setCards([]);
        setLoaded(true);
      });
  }, [tick]);

  useEffect(() => {
    if (!loaded) return;
    const t = window.setTimeout(() => {
      const map: Record<string, string> = {};
      for (const c of cards) map[c.room_id] = c.stage;
      prevStages.current = map;
    }, 520);
    return () => window.clearTimeout(t);
  }, [cards, loaded]);

  useEffect(() => {
    if (!demo?.flowRequest || !demo.roomId) return;
    const card = cards.find((c) => c.room_id === demo.roomId);
    if (card) setFlowCard(card);
  }, [demo?.flowRequest, demo?.roomId, cards]);

  useEffect(() => {
    if (!flowCard) return;
    const fresh = cards.find((c) => c.room_id === flowCard.room_id);
    if (fresh && fresh.stage !== flowCard.stage) setFlowCard(fresh);
  }, [cards, flowCard]);

  const liveFlow = flowCard ? cards.find((c) => c.room_id === flowCard.room_id) || flowCard : null;

  const cols = columns.length ? columns : ["signal", "investigate", "evidence", "approve", "verify", "learn"];
  const highlight = demo?.active && demo.highlightStage ? demo.highlightStage : wsStage;

  function columnLive(col: string) {
    return cards.some(
      (c) =>
        c.stage === col &&
        (c.active_agents?.some((a) => (STAGE_AGENTS[col] || []).includes(a)) || (c.active_agents?.length ?? 0) > 0)
    );
  }

  function agentLive(agentId: string) {
    return cards.some((c) => cardAgent(c) === agentId || c.active_agents?.includes(agentId));
  }

  function toggleView(next: "stage" | "agent") {
    setView(next);
    try {
      localStorage.setItem(VIEW_KEY, next);
    } catch {
      /* ignore */
    }
  }

  return (
    <div id="pipeline-board" className={cn(demo?.active ? "mt-4" : "mt-0")}>
      <PipelineFlowOverlay
        open={Boolean(liveFlow)}
        onClose={() => setFlowCard(null)}
        title={liveFlow?.title || ""}
        stage={liveFlow?.stage || "signal"}
        roomId={liveFlow?.room_id || ""}
        evidenceSnippet={liveFlow?.evidence_snippet}
        voiceSnippet={liveFlow?.voice_snippet}
        calendarSnippet={liveFlow?.calendar_snippet}
      />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-[18px] font-semibold tracking-tight">Pipeline</h2>
        <div className="flex items-center gap-2">
          <div className="flex rounded-full border border-border bg-white p-0.5 text-[12px]">
            <button
              type="button"
              onClick={() => toggleView("stage")}
              className={cn(
                "rounded-full px-2.5 py-1 font-medium transition-colors",
                view === "stage" ? "bg-accent text-white" : "text-[var(--dim)]"
              )}
            >
              By stage
            </button>
            <button
              type="button"
              onClick={() => toggleView("agent")}
              className={cn(
                "rounded-full px-2.5 py-1 font-medium transition-colors",
                view === "agent" ? "bg-accent text-white" : "text-[var(--dim)]"
              )}
            >
              By agent
            </button>
          </div>
          {cards.length ? (
            <span className="text-[12px] text-[var(--faint)]">{cards.length} open</span>
          ) : loaded ? (
            <span className="text-[12px] text-[var(--faint)]">Run demo</span>
          ) : null}
        </div>
      </div>

      {view === "stage" ? (
        <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
          {cols.map((col) => {
            const inCol = cards.filter((c) => c.stage === col);
            const colLive = columnLive(col);
            const colHighlight = highlight === col;
            return (
              <div
                key={col}
                id={`pipeline-col-${col}`}
                className={cn(
                  "min-w-[9.5rem] shrink-0 rounded-2xl p-2 transition-all duration-300",
                  colHighlight ? "bg-[color-mix(in_srgb,var(--accent)_12%,#eef2ee)] ring-2 ring-accent/25" : "bg-[#eef2ee]"
                )}
              >
                <div className="flex items-center gap-1.5 px-2 py-1">
                  <span className={cn("h-1.5 w-1.5 rounded-full", colLive ? "bg-accent" : "bg-[var(--faint)]/40")} />
                  <p className="text-[11px] font-medium text-[var(--faint)]">
                    {LABELS[col] || col}
                    {inCol.length ? ` · ${inCol.length}` : ""}
                  </p>
                </div>
                <div className="mt-1 min-h-[4rem] space-y-2">
                  {inCol.map((c) => {
                    const moved = Boolean(prevStages.current[c.room_id] && prevStages.current[c.room_id] !== c.stage);
                    return (
                      <PipelineCard
                        key={c.room_id}
                        c={c}
                        moved={moved}
                        demoFocus={demo?.active && demo.roomId === c.room_id}
                        onShowFlow={() => setFlowCard(c)}
                      />
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
          {AGENT_COLUMNS.map((col) => {
            const inCol = cards.filter((c) => cardAgent(c) === col.id || c.active_agents?.includes(col.id));
            const colLive = agentLive(col.id);
            const colHighlight = col.stages.includes(highlight || "");
            return (
              <div
                key={col.id}
                id={`pipeline-agent-${col.id}`}
                className={cn(
                  "min-w-[9.5rem] shrink-0 rounded-2xl p-2 transition-all duration-300",
                  colHighlight ? "bg-[color-mix(in_srgb,var(--accent)_12%,#eef2ee)] ring-2 ring-accent/25" : "bg-[#eef2ee]"
                )}
              >
                <div className="flex items-center gap-1.5 px-2 py-1">
                  <span className={cn("h-1.5 w-1.5 rounded-full", colLive ? "bg-accent" : "bg-[var(--faint)]/40")} />
                  <p className="text-[11px] font-medium text-[var(--faint)]">
                    {col.label}
                    {inCol.length ? ` · ${inCol.length}` : ""}
                  </p>
                </div>
                <div className="mt-1 min-h-[4rem] space-y-2">
                  {inCol.map((c) => {
                    const moved = Boolean(prevStages.current[c.room_id] && prevStages.current[c.room_id] !== c.stage);
                    return (
                      <PipelineCard
                        key={c.room_id}
                        c={c}
                        moved={moved}
                        demoFocus={demo?.active && demo.roomId === c.room_id}
                        onShowFlow={() => setFlowCard(c)}
                      />
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
