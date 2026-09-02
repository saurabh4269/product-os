"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Investigation, type OfficeDesk } from "@/lib/api";
import { AgentBadge } from "@/components/agent-badge";
import { PageHeader, PageStatPill } from "@/components/page-header";
import { WorkflowLinksPanel } from "@/components/workflow-links";
import { MIcon } from "./icon";

const LOOP_STAGES = [
  { id: "signal", label: "Signal Agent", icon: "sensors" },
  { id: "investigate", label: "Investigation Team", icon: "psychology" },
  { id: "diagnose", label: "Root Cause Agent", icon: "biotech" },
  { id: "fix", label: "Fix Agent", icon: "build_circle" },
  { id: "verify", label: "Verify", icon: "verified" },
];

function stageStatus(
  state: string,
  stageId: string
): "completed" | "active" | "waiting" {
  const order = ["OPEN", "GATHERING", "DIAGNOSING", "AWAITING_APPROVAL", "ACTING", "VERIFYING", "RESOLVED"];
  const idx = order.indexOf(state);
  const stageIdx: Record<string, number> = {
    signal: 0,
    investigate: 1,
    diagnose: 2,
    fix: 3,
    verify: 4,
  };
  const current = stageIdx[stageId] ?? 0;
  if (idx < 0) return current === 0 ? "active" : "waiting";
  if (idx > current + 1) return "completed";
  if (idx === current || (stageId === "investigate" && idx <= 2)) return "active";
  if (idx < current) return "completed";
  return "waiting";
}

/** workflow_orchestration_automation_1/code.html — loop graph + coordination links. */
export function WorkflowsOrchestration() {
  const [office, setOffice] = useState<{ desks: OfficeDesk[]; working: number } | null>(null);
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.status>> | null>(null);

  useEffect(() => {
    Promise.all([api.office(), api.investigations(), api.status()])
      .then(([o, inv, st]) => {
        setOffice(o);
        setInvestigations(inv.investigations);
        setStatus(st);
      })
      .catch(() => undefined);
  }, []);

  const activeInv = useMemo(
    () =>
      investigations.find(
        (i) => !["RESOLVED", "NOT_RESOLVED", "INCONCLUSIVE", "PARTIALLY_RESOLVED"].includes(i.state)
      ),
    [investigations]
  );

  const workingDesks = office?.desks.filter((d) => d.status !== "idle").slice(0, 3) ?? [];
  const verified = investigations.filter((i) => ["RESOLVED", "PARTIALLY_RESOLVED"].includes(i.state));
  const successRate =
    investigations.length > 0 ? Math.round((verified.length / investigations.length) * 1000) / 10 : null;

  const openCount = investigations.filter(
    (i) => !["RESOLVED", "NOT_RESOLVED", "INCONCLUSIVE", "PARTIALLY_RESOLVED"].includes(i.state)
  ).length;

  return (
    <div className="mx-auto max-w-container-max space-y-margin-lg">
      <PageHeader title="Workflows">
        <PageStatPill>
          <span className="font-semibold text-text-primary">{openCount}</span> open
        </PageStatPill>
        <PageStatPill>
          <span className="font-semibold text-ok">{verified.length}</span> resolved
        </PageStatPill>
        {successRate != null ? (
          <PageStatPill>
            <span className="font-semibold text-text-primary">{successRate}%</span> success
          </PageStatPill>
        ) : null}
        <Link href="/registry" className="text-label-lg text-primary hover:underline">
          Agents
        </Link>
      </PageHeader>

      <div className="grid grid-cols-1 gap-margin-md xl:grid-cols-3">
        <div className="po-card flex flex-col rounded-xl p-margin-md xl:col-span-2">
          <div className="mb-margin-md flex items-center justify-between">
            <h3 className="text-headline-md text-text-primary">
              {activeInv ? "Active incident investigation loop" : "Investigation loop (idle)"}
            </h3>
            {activeInv ? (
              <span className="flex items-center gap-1 rounded-full bg-accent-success/10 px-3 py-1 text-label-caps text-accent-success">
                <span className="h-2 w-2 animate-pulse rounded-full bg-accent-success" />
                {activeInv.state.replace(/_/g, " ")}
              </span>
            ) : (
              <span className="rounded-full bg-surface-container-high px-3 py-1 text-label-caps text-on-surface-variant">
                Standby
              </span>
            )}
          </div>

          <div className="relative flex min-h-[400px] flex-1 items-center justify-center overflow-hidden rounded-lg border border-surface-subtle bg-surface-base">
            <div className="relative z-10 flex w-full max-w-2xl flex-col items-center gap-6 py-8">
              {LOOP_STAGES.map((stage, i) => {
                const st = activeInv ? stageStatus(activeInv.state, stage.id) : i === 0 ? "active" : "waiting";
                const desk = workingDesks[i];
                return (
                  <div key={stage.id} className="flex w-full flex-col items-center gap-4">
                    <div
                      className={`flex w-72 items-center gap-4 rounded-xl p-4 shadow-lg ${
                        st === "active"
                          ? "border-2 border-primary bg-white"
                          : st === "completed"
                            ? "border border-surface-subtle bg-white"
                            : "border border-surface-subtle bg-white/50 opacity-70"
                      }`}
                    >
                      {desk ? (
                        <AgentBadge name={desk.id} size={40} variant="face" />
                      ) : (
                        <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-surface-subtle bg-surface-container-low text-secondary">
                          <MIcon name={stage.icon} />
                        </div>
                      )}
                      <div>
                        <div className="text-label-lg text-text-primary">{desk?.display_name || stage.label}</div>
                        <div
                          className={`text-body-sm ${
                            st === "active"
                              ? "text-primary"
                              : st === "completed"
                                ? "text-accent-success"
                                : "text-text-secondary"
                          }`}
                        >
                          {desk?.doing ||
                            (st === "completed" ? "Completed" : st === "active" ? "In progress…" : "Waiting")}
                        </div>
                      </div>
                    </div>
                    {i < LOOP_STAGES.length - 1 ? (
                      <div className="relative h-8 w-0.5 bg-outline-variant">
                        <MIcon
                          name="arrow_downward"
                          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-outline-variant"
                        />
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </div>
          </div>

          {activeInv?.room_id ? (
            <div className="mt-4 text-center">
              <Link href={`/rooms/${activeInv.room_id}`} className="text-label-lg text-primary hover:underline">
                Open room →
              </Link>
            </div>
          ) : null}
        </div>

        <div className="flex flex-col gap-margin-md">
          <div className="po-card rounded-xl p-margin-md">
            <h3 className="mb-4 text-label-lg uppercase tracking-wider text-text-secondary">Overall performance</h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="rounded-lg bg-surface-base p-4">
                <div className="mb-1 text-body-sm text-text-secondary">Active agents</div>
                <div className="text-headline-md text-text-primary">{office?.working ?? status?.engaged ?? 0}</div>
              </div>
              <div className="rounded-lg bg-surface-base p-4">
                <div className="mb-1 text-body-sm text-text-secondary">Open missions</div>
                <div className="text-headline-md text-text-primary">
                  {investigations.filter((i) => !["RESOLVED", "NOT_RESOLVED", "INCONCLUSIVE", "PARTIALLY_RESOLVED"].includes(i.state)).length}
                </div>
              </div>
              <div className="col-span-2 flex items-center justify-between rounded-lg bg-surface-base p-4">
                <div>
                  <div className="mb-1 text-body-sm text-text-secondary">Success rate</div>
                  <div className="text-headline-md text-accent-success">
                    {successRate != null ? `${successRate}%` : "—"}
                  </div>
                </div>
                <div className="flex h-16 w-16 items-center justify-center rounded-full border-4 border-surface-subtle border-t-accent-success">
                  <MIcon name="trending_up" className="text-accent-success" />
                </div>
              </div>
            </div>
          </div>

          <div className="po-card flex flex-1 flex-col overflow-hidden rounded-xl p-margin-md">
            <h3 className="mb-4 text-label-lg uppercase tracking-wider text-text-secondary">Recent runs</h3>
            <div className="flex flex-col gap-3">
              {investigations.slice(0, 5).map((inv) => (
                <Link
                  key={inv.id}
                  href={inv.room_id ? `/rooms/${inv.room_id}` : "/"}
                  className="flex items-start gap-3 rounded-lg border border-transparent p-3 transition-colors hover:border-surface-subtle hover:bg-surface-subtle"
                >
                  <MIcon
                    name={
                      ["RESOLVED", "PARTIALLY_RESOLVED"].includes(inv.state)
                        ? "check_circle"
                        : inv.state === "AWAITING_APPROVAL"
                          ? "pending"
                          : "play_circle"
                    }
                    className={
                      ["RESOLVED", "PARTIALLY_RESOLVED"].includes(inv.state)
                        ? "mt-0.5 text-accent-success"
                        : "mt-0.5 text-primary"
                    }
                  />
                  <div>
                    <div className="text-label-lg text-text-primary">{inv.title || inv.scenario_id || inv.id.slice(0, 12)}</div>
                    <div className="text-body-sm text-text-secondary">{inv.state.replace(/_/g, " ")}</div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>

      <WorkflowLinksPanel />
    </div>
  );
}
