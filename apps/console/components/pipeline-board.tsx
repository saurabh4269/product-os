"use client";

import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { usePipelineHighlight } from "@/lib/pipeline-highlight";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useDemoGuide } from "@/lib/demo-guide-context";
import { useGlobalWs } from "@/lib/use-global-ws";
import { AgentBadge } from "@/components/agent-badge";
import { PipelineFlowOverlay } from "@/components/pipeline-flow-overlay";
import { PipelineEmpty } from "@/components/pipeline-empty";
import { WorkflowLinkChips } from "@/components/workflow-links";
import { cn } from "@/lib/utils";

const LABELS: Record<string, string> = {
  signal: "Signal",
  investigate: "Investigate",
  evidence: "Evidence",
  customer: "Customer",
  root_cause: "Root cause",
  code: "Code",
  product: "Product",
  experiment: "Experiment",
  risk: "Risk",
  approve: "Approve",
  coordinate: "Coordinate",
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

const AGENT_COLUMN_META: Record<string, { label: string; stages: string[] }> = {
  signal_agent: { label: "Signal", stages: ["signal"] },
  analytics_agent: { label: "Analytics", stages: ["investigate"] },
  logs_agent: { label: "Logs", stages: ["investigate"] },
  deployment_agent: { label: "Deploy", stages: ["investigate"] },
  customer_voice_agent: { label: "Customer", stages: ["investigate", "customer", "customer_mail", "customer_call"] },
  evidence_agent: { label: "Evidence", stages: ["evidence"] },
  root_cause_agent: { label: "Root cause", stages: ["root_cause"] },
  code_agent: { label: "Code", stages: ["code"] },
  product_agent: { label: "Product", stages: ["product", "experiment"] },
  risk_agent: { label: "Risk / Approve", stages: ["risk", "approve"] },
  learning_agent: { label: "Learning", stages: ["verify", "learn"] },
};

const AGENT_COLUMN_FALLBACK: Array<{ id: string; label: string; stages: string[] }> = Object.entries(
  AGENT_COLUMN_META
).map(([id, meta]) => ({ id, ...meta }));

const VIEW_KEY = "loop-pipeline-view";

type Card = {
  room_id: string;
  title: string;
  stage: string;
  kind: string;
  workflow?: {
    steps?: Array<{ id: string; label: string; short?: string; detail?: string; on?: boolean }>;
    nodes?: string[];
    current?: string;
  };
  tenant_product?: string | null;
  awaiting_approval?: boolean;
  pr_url?: string | null;
  evidence_snippet?: string | null;
  calendar_snippet?: string | null;
  calendar_url?: string | null;
  meet_url?: string | null;
  gmail_url?: string | null;
  voice_snippet?: string | null;
  contact_phone?: string | null;
  call_feedback?: string | null;
  warehouse_snippet?: string | null;
  code_snippet?: string | null;
  activity_line?: string | null;
  activity_author?: string | null;
  verified?: boolean;
  denied?: boolean;
  active_agents?: string[];
};

function cardAgent(c: Card): string {
  if (c.active_agents?.[0]) return c.active_agents[0];
  const defaults = STAGE_AGENTS[c.stage];
  return defaults?.[0] || "orchestrator";
}

function statusChip(c: Card) {
  if (c.awaiting_approval) return { label: "Approve", tone: "accent" as const };
  if (c.denied) return { label: "Held", tone: "danger" as const };
  if (c.verified) return { label: "Verified", tone: "ok" as const };
  if (c.call_feedback) return { label: "Feedback", tone: "ok" as const };
  if (c.contact_phone && c.stage === "investigate") return { label: "Contact", tone: "ok" as const };
  if (c.pr_url) return { label: "PR open", tone: "ok" as const };
  if (c.active_agents?.length) return { label: "Working", tone: "accent" as const };
  return { label: LABELS[c.stage] || c.stage, tone: "faint" as const };
}

function agentLabel(id: string) {
  return id.replace(/_agent$/, "").replace(/_/g, " ");
}

function cardReceipt(c: Card): string | null {
  if (c.call_feedback) return c.call_feedback;
  if (c.warehouse_snippet) return c.warehouse_snippet;
  if (c.code_snippet) return c.code_snippet;
  if (c.evidence_snippet) return c.evidence_snippet;
  if (c.calendar_snippet) return c.calendar_snippet;
  if (c.voice_snippet) return c.voice_snippet;
  return null;
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
  const receipt = cardReceipt(c);
  const activity = c.activity_line || receipt;
  return (
    <div
      className={cn(
        "interactive group overflow-hidden rounded-xl border bg-card shadow-sm",
        c.denied && "border-danger/40 bg-red-50/40",
        c.verified && "border-ok/40",
        c.awaiting_approval && "border-accent/50 ring-2 ring-accent/20",
        c.call_feedback && !c.awaiting_approval && "border-accent/30 bg-accent/[0.03]",
        demoFocus && !c.awaiting_approval && "ring-2 ring-accent/25 border-accent/40",
        !c.denied && !c.verified && !c.awaiting_approval && !demoFocus && !c.call_feedback && "border-border",
        moved && "scale-[1.02]"
      )}
    >
      <Link href={`/rooms/${c.room_id}`} className="block px-3 py-2.5">
        <div className="flex items-start gap-2">
          <AgentBadge name={agent} working={working} size={24} variant="face" />
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-medium leading-5 text-foreground line-clamp-2">{c.title}</p>
            {c.contact_phone ? (
              <p className="mt-1 font-mono text-[12px] tabular-nums text-[var(--dim)]">{c.contact_phone}</p>
            ) : null}
            {c.tenant_product && !c.contact_phone ? (
              <p className="mt-1 text-[11px] text-[var(--faint)]">{c.tenant_product}</p>
            ) : null}
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  chip.tone === "accent" && "bg-accent/10 text-accent",
                  chip.tone === "ok" && "bg-ok/10 text-ok",
                  chip.tone === "danger" && "bg-danger/10 text-danger",
                  chip.tone === "faint" && "bg-[var(--elev)] text-[var(--faint)]"
                )}
              >
                {chip.label}
              </span>
            </div>
            {receipt && receipt !== activity ? (
              <p className="mt-2 line-clamp-2 text-[11px] leading-4 text-[var(--dim)]">{receipt}</p>
            ) : null}
          </div>
          <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-[var(--faint)] opacity-0 transition group-hover:opacity-60" />
        </div>
      </Link>
      <WorkflowLinkChips
        calendar_url={c.calendar_url}
        meet_url={c.meet_url}
        gmail_url={c.gmail_url}
        pr_url={c.pr_url}
      />
      {activity ? (
        <p className="border-t border-border/60 px-3 py-1.5 text-[10px] leading-4 text-[var(--faint)] line-clamp-2">
          {c.activity_author ? (
            <span className="font-medium text-[var(--dim)]">{agentLabel(c.activity_author)}: </span>
          ) : null}
          {activity}
        </p>
      ) : null}
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

export function PipelineBoard({ subtitle, className }: { subtitle?: string; className?: string }) {
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

  const cols = columns.length ? columns : [];
  const highlight = demo?.active && demo.highlightStage ? demo.highlightStage : wsStage;

  const agentColumns = (() => {
    const seen = new Set<string>();
    const out: Array<{ id: string; label: string; stages: string[] }> = [];
    for (const c of cards) {
      for (const id of [cardAgent(c), ...(c.active_agents || [])]) {
        if (!id || seen.has(id)) continue;
        seen.add(id);
        const meta = AGENT_COLUMN_META[id];
        out.push({
          id,
          label: meta?.label || agentLabel(id),
          stages: meta?.stages || [c.stage],
        });
      }
    }
    return out.length ? out : AGENT_COLUMN_FALLBACK;
  })();

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

  const awaiting = cards.filter((c) => c.awaiting_approval).length;
  const withContact = cards.filter((c) => Boolean(c.contact_phone)).length;
  const withFeedback = cards.filter((c) => Boolean(c.call_feedback)).length;
  const withPr = cards.filter((c) => Boolean(c.pr_url)).length;

  return (
    <div id="pipeline-board" className={cn(className, demo?.active ? "mt-4" : "mt-0")}>
      <PipelineFlowOverlay
        open={Boolean(liveFlow)}
        onClose={() => setFlowCard(null)}
        title={liveFlow?.title || ""}
        stage={liveFlow?.stage || "signal"}
        roomId={liveFlow?.room_id || ""}
        evidenceSnippet={liveFlow?.evidence_snippet}
        voiceSnippet={liveFlow?.voice_snippet}
        calendarSnippet={liveFlow?.calendar_snippet}
        steps={liveFlow?.workflow?.steps?.map((s, i) => ({
          n: i + 1,
          short: s.short || s.label,
          label: s.label,
          detail: s.detail || "",
          stage: s.id,
        }))}
      />
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[18px] font-semibold tracking-tight">Pipeline</h2>
          {subtitle ? <p className="mt-0.5 text-[13px] text-[var(--dim)]">{subtitle}</p> : null}
        </div>
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
            <span className="text-[12px] text-[var(--faint)]">Eval scenarios only</span>
          ) : null}
        </div>
      </div>

      {loaded && cards.length > 0 ? (
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            { label: "Open rooms", value: cards.length },
            { label: "Awaiting you", value: awaiting, hot: awaiting > 0 },
            { label: "Contacts on file", value: withContact },
            { label: withFeedback ? "Call feedback" : "PRs open", value: withFeedback || withPr },
          ].map((k) => (
            <div
              key={k.label}
              className={cn(
                "rounded-xl border px-3 py-2",
                k.hot ? "border-accent/40 bg-accent/5" : "border-border bg-white"
              )}
            >
              <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--faint)]">{k.label}</p>
              <p className="mt-0.5 text-[20px] font-semibold tabular-nums tracking-tight">{k.value}</p>
            </div>
          ))}
        </div>
      ) : null}

      {loaded && awaiting > 0 ? (
        <div className="mt-3 rounded-xl border border-accent/30 bg-accent/5 px-4 py-2.5 text-[13px] text-accent">
          {awaiting === 1 ? "1 change waiting" : `${awaiting} changes waiting`}
        </div>
      ) : null}

      {loaded && cards.length === 0 ? <PipelineEmpty /> : null}

      {loaded && cards.length > 0 && view === "stage" ? (
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
                  "min-w-[11.5rem] shrink-0 rounded-2xl p-2 transition-all duration-300",
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
      ) : loaded && cards.length > 0 ? (
        <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
          {agentColumns.map((col) => {
            const inCol = cards.filter((c) => cardAgent(c) === col.id || c.active_agents?.includes(col.id));
            const colLive = agentLive(col.id);
            const colHighlight = col.stages.includes(highlight || "");
            return (
              <div
                key={col.id}
                id={`pipeline-agent-${col.id}`}
                className={cn(
                  "min-w-[11.5rem] shrink-0 rounded-2xl p-2 transition-all duration-300",
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
      ) : null}
    </div>
  );
}
