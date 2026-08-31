"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { AgentBadge } from "@/components/agent-badge";
import { setPipelineHighlight, usePipelineHighlight } from "@/lib/pipeline-highlight";
import { useGlobalWs } from "@/lib/use-global-ws";

export type WorkflowStep = {
  n: number;
  id?: string;
  short: string;
  label: string;
  detail: string;
  stage: string;
  on?: boolean;
  status?: "done" | "active" | "next" | "watching";
  agent?: string;
};

type Handoff = {
  from: string;
  to: string;
  from_node?: string;
  to_node?: string;
  why: string;
};

/** Progressive case flow — steps appear as agents are invoked, not all at once. */
export function SevenStepLoop({
  activeStage,
  compact,
  className,
  steps: stepsProp,
}: {
  activeStage?: string | null;
  compact?: boolean;
  className?: string;
  steps?: WorkflowStep[] | null;
}) {
  const wsStage = usePipelineHighlight();
  const { tick } = useGlobalWs();
  const current = activeStage ?? wsStage;
  const [mode, setMode] = useState<"watching" | "active">("watching");
  const [watchLine, setWatchLine] = useState("Signal agent watching");
  const [watchDetail, setWatchDetail] = useState("Polling warehouse and product telemetry.");
  const [fetched, setFetched] = useState<WorkflowStep[] | null>(null);
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [kind, setKind] = useState<string | null>(null);
  const [roomId, setRoomId] = useState<string | null>(null);

  useEffect(() => {
    if (stepsProp?.length) return;
    api
      .workflowFocus()
      .then((r) => {
        setMode((r.mode as "watching" | "active") || (r.steps?.length ? "active" : "watching"));
        setWatchLine(r.watch_line || "Signal agent watching");
        setWatchDetail(r.signal_agent?.detail || "Polling warehouse and product telemetry.");
        setFetched(
          (r.steps || []).map((s) => ({
            n: s.n,
            id: s.id,
            short: s.short,
            label: s.label,
            detail: s.detail,
            stage: s.stage,
            on: s.on,
            status: (s as WorkflowStep).status,
            agent: (s as WorkflowStep).agent,
          }))
        );
        setHandoffs((r.handoffs as Handoff[]) || []);
        setKind(r.kind || null);
        setRoomId(r.room_id || null);
      })
      .catch(() => {
        setFetched(null);
        setMode("watching");
      });
  }, [tick, stepsProp]);

  const steps: WorkflowStep[] =
    (stepsProp && stepsProp.length ? stepsProp : null) ||
    (fetched && fetched.length ? fetched : []);

  function go(step: WorkflowStep) {
    setPipelineHighlight(step.stage);
    document.getElementById(`pipeline-col-${step.stage}`)?.scrollIntoView({
      behavior: "smooth",
      inline: "center",
      block: "nearest",
    });
  }

  if (mode === "watching" && !steps.length) {
    return (
      <div
        className={cn(
          "rounded-2xl border border-border bg-white px-4 py-4",
          className
        )}
      >
        <div className="flex items-start gap-3">
          <div className="relative shrink-0">
            <AgentBadge name="signal_agent" working size={32} variant="face" />
            <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-accent ring-2 ring-white animate-pulse" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--faint)]">
              {watchLine}
            </p>
            <p className="mt-0.5 text-[15px] font-semibold tracking-tight text-foreground">
              Nothing open yet
            </p>
            <p className="mt-1 text-[13px] leading-5 text-[var(--dim)]">{watchDetail}</p>
            <p className="mt-2 text-[12px] text-[var(--faint)]">
              When telemetry moves, the next agents appear here — one step at a time, with handoff reasons.
            </p>
          </div>
        </div>
      </div>
    );
  }

  const gridCols =
    steps.length <= 3
      ? "sm:grid-cols-1 md:grid-cols-3"
      : steps.length <= 5
        ? "sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
        : "sm:grid-cols-2 lg:grid-cols-4";

  return (
    <div className={cn("rounded-2xl border border-border bg-white px-4 py-3", className)}>
      <div className="mb-3 flex items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--faint)]">
            {kind ? `${kind} case` : "Active case"}
          </p>
          {roomId ? (
            <Link href={`/rooms/${roomId}`} className="text-[12px] text-accent hover:underline">
              Open chat →
            </Link>
          ) : null}
        </div>
      </div>

      <ol className={cn("grid gap-3", gridCols)}>
        {steps.map((step, idx) => {
          const hot = current === step.stage || step.status === "active";
          const done = step.status === "done" || Boolean(step.on && step.status !== "next");
          const next = step.status === "next";
          const handoff = handoffs.find((h) => h.to_node === step.id || h.to === step.agent);

          return (
            <li key={`${step.stage}-${step.n}`} className="relative">
              {idx > 0 && handoffs[idx - 1]?.why ? (
                <p className="mb-1.5 hidden text-[10px] leading-4 text-[var(--faint)] lg:block">
                  ↳ {handoffs[idx - 1]?.why}
                </p>
              ) : handoff?.why ? (
                <p className="mb-1.5 text-[10px] leading-4 text-[var(--faint)]">↳ {handoff.why}</p>
              ) : null}
              <button
                type="button"
                onClick={() => go(step)}
                className={cn(
                  "h-full w-full rounded-xl border px-3 py-2.5 text-left transition-all duration-300",
                  hot && "border-accent bg-[color-mix(in_srgb,var(--accent)_8%,white)] ring-2 ring-accent/20",
                  !hot && done && "border-border bg-[#eef2ee]",
                  next && "border-dashed border-accent/40 bg-white opacity-90",
                  !hot && !done && !next && "border-border bg-white hover:border-accent/30"
                )}
              >
                <div className="flex items-center gap-2">
                  {step.agent ? (
                    <AgentBadge
                      name={step.agent}
                      working={hot}
                      size={22}
                      variant="face"
                    />
                  ) : null}
                  <p
                    className={cn(
                      "text-[11px] font-semibold",
                      hot ? "text-accent" : next ? "text-[var(--dim)]" : "text-[var(--faint)]"
                    )}
                  >
                    {step.n} · {step.short}
                    {next ? " (next)" : ""}
                  </p>
                </div>
                <p className="mt-1 text-[13px] font-medium leading-5 text-foreground">{step.label}</p>
                {!compact && step.detail ? (
                  <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-[var(--dim)]">{step.detail}</p>
                ) : null}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
