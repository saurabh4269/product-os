"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Investigation, type Room } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { when } from "@/lib/utils";
import { AgentBadge } from "@/components/agent-badge";
import { MIcon } from "./icon";

function stateBadge(state: string) {
  const s = state.replace(/_/g, " ");
  if (state === "AWAITING_APPROVAL") return { label: "Awaiting approval", bg: "bg-[#EEF2FF]", text: "text-[#3730A3]", dot: "bg-[#6366F1]" };
  if (state === "VERIFYING" || state === "ACTING") return { label: s, bg: "bg-[#ECFDF5]", text: "text-[#065F46]", dot: "bg-[#10B981]" };
  if (["RESOLVED", "PARTIALLY_RESOLVED"].includes(state)) return { label: "Verified", bg: "bg-[#ECFDF5]", text: "text-[#065F46]", dot: "bg-[#10B981]" };
  return { label: s || "Diagnosing", bg: "bg-[#ECFDF5]", text: "text-[#065F46]", dot: "bg-[#10B981]" };
}

function missionDot(state: string) {
  if (state === "AWAITING_APPROVAL") return "bg-[#F59E0B] animate-pulse";
  if (state === "ACTING") return "bg-[#6366F1]";
  return "bg-[#3B82F6]";
}

/** autonomous_command_center/code.html — missions + embedded tool surfaces (no inbox feed). */
export function MissionControl() {
  const { tick } = useGlobalWs();
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.status>> | null>(null);

  useEffect(() => {
    Promise.all([api.investigations(), api.rooms(), api.status()])
      .then(([inv, r, st]) => {
        setInvestigations(inv.investigations);
        setRooms(r.rooms);
        setStatus(st);
      })
      .catch(() => undefined);
  }, [tick]);

  const roomByInv = useMemo(() => {
    const m: Record<string, Room> = {};
    for (const r of rooms) {
      if (r.investigation_id) m[r.investigation_id] = r;
    }
    return m;
  }, [rooms]);

  const open = investigations.filter(
    (i) => !["RESOLVED", "NOT_RESOLVED", "INCONCLUSIVE", "PARTIALLY_RESOLVED"].includes(i.state)
  );
  const verified = investigations.filter((i) =>
    ["RESOLVED", "PARTIALLY_RESOLVED"].includes(i.state)
  );
  const successRate =
    investigations.length > 0 ? Math.round((verified.length / investigations.length) * 1000) / 10 : null;
  const activeAgents = status?.presence?.agents ?? status?.engaged ?? 0;

  return (
    <div className="mx-auto max-w-7xl space-y-stack-lg pb-4">
      <div>
        <h2 className="text-display-lg font-black text-primary">Mission Control</h2>
      </div>

      <section className="grid grid-cols-1 gap-stack-md md:grid-cols-3">
        <div className="po-card relative flex flex-col gap-2 overflow-hidden rounded-xl p-stack-md">
          <div className="flex items-start justify-between">
            <span className="text-label-caps uppercase text-on-surface-variant">Open investigations</span>
            <MIcon name="precision_manufacturing" className="text-[20px] text-secondary" />
          </div>
          <div className="mt-2 text-headline-md font-bold">{open.length}</div>
          <div className="flex items-center gap-1 text-body-sm text-accent-success">
            <MIcon name="sensors" className="text-[14px]" />
            <span>{status?.rooms?.open ?? 0} active rooms</span>
          </div>
        </div>
        <div className="po-card flex flex-col gap-2 rounded-xl p-stack-md">
          <div className="flex items-start justify-between">
            <span className="text-label-caps uppercase text-on-surface-variant">Success rate (fix/verify)</span>
            <MIcon name="check_circle" className="text-[20px] text-accent-success" />
          </div>
          <div className="mt-2 text-headline-md font-bold">{successRate != null ? `${successRate}%` : "—"}</div>
          <div className="text-body-sm text-on-surface-variant">
            Based on {verified.length} verified of {investigations.length} missions
          </div>
        </div>
        <div className="po-card flex flex-col gap-2 rounded-xl border-none bg-[#0F172A] p-stack-md text-white">
          <div className="flex items-start justify-between">
            <span className="text-label-caps uppercase text-inverse-primary">Pending approvals</span>
            <MIcon name="gavel" className="text-[20px] text-inverse-primary" />
          </div>
          <div className="mt-2 text-headline-md font-bold">{status?.approvals_pending ?? 0}</div>
          <div className="flex items-center gap-1 text-body-sm text-accent-success">
            <MIcon name="smart_toy" className="text-[14px]" />
            <span>{activeAgents} agents engaged</span>
          </div>
          {(status?.approvals_pending ?? 0) > 0 ? (
            <div className="mt-auto pt-2">
              <Link
                href="/approvals"
                className="flex items-center gap-1 text-body-sm font-semibold text-secondary-fixed hover:text-white"
              >
                Review with GitHub embed <MIcon name="arrow_forward" className="text-[14px]" />
              </Link>
            </div>
          ) : null}
        </div>
      </section>

      <div className="space-y-stack-md">
          <div className="mb-stack-sm flex items-center justify-between">
            <h3 className="text-headline-sm text-on-surface">Active investigations</h3>
            <div className="flex items-center gap-4">
              <Link href="/workflows" className="text-body-sm font-semibold text-secondary hover:underline">
                Workflows
              </Link>
            </div>
          </div>
          {open.length === 0 ? (
            <div className="po-card rounded-xl p-stack-md text-body-md text-on-surface-variant">
              No open missions — signals from Product Y or fixtures will open a room automatically.
            </div>
          ) : (
            open.slice(0, 4).map((inv) => {
              const room = roomByInv[inv.id] || (inv.room_id ? rooms.find((r) => r.id === inv.room_id) : undefined);
              const badge = stateBadge(inv.state);
              const title = room?.title || inv.title || inv.id;
              return (
                <div key={inv.id} className="po-card po-card-hover po-ambient-shadow overflow-hidden rounded-xl p-0">
                  <div className="flex items-center justify-between border-b border-[#E2E8F0] bg-[#F8FAFC] px-stack-md py-3">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${missionDot(inv.state)}`} />
                      <span className="font-mono text-code-sm text-on-surface-variant">{inv.id.slice(0, 12)}</span>
                    </div>
                    <div className="flex gap-2">
                      <div
                        className={`flex items-center gap-1 rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${badge.bg} ${badge.text}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${badge.dot}`} />
                        {badge.label}
                      </div>
                      {inv.scenario_id ? (
                        <div className="rounded-full bg-surface-variant px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                          {inv.scenario_id.replace(/_/g, " ")}
                        </div>
                      ) : null}
                    </div>
                  </div>
                  <div className="p-stack-md">
                    <h4 className="mb-1 text-headline-sm font-semibold">{title}</h4>
                    <p className="mb-4 text-body-sm text-on-surface-variant">
                      {room?.topic || "Agents are gathering evidence from connected tools."}
                    </p>
                    {(inv.assigned_agents?.length || room?.members?.length) ? (
                      <div className="rounded border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                        <div className="mb-2 text-label-caps uppercase text-on-surface-variant">Assigned agents</div>
                        <div className="flex flex-wrap gap-4">
                          {(inv.assigned_agents?.length ? inv.assigned_agents : room?.members || [])
                            .filter((a) => a !== "system" && a !== "you")
                            .slice(0, 4)
                            .map((a) => (
                              <div key={a} className="flex items-center gap-2">
                                <AgentBadge name={a} size={24} variant="face" />
                                <span className="font-mono text-code-sm">{a.replace(/_agent$/, "")}</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    ) : null}
                  </div>
                  <div className="flex items-center justify-between border-t border-[#E2E8F0] bg-surface px-stack-md py-2">
                    <span className="font-mono text-[10px] text-on-surface-variant">
                      {inv.opened_at ? `Started ${when(inv.opened_at)}` : ""}
                    </span>
                    {room ? (
                      <Link
                        href={`/rooms/${room.id}?view=lab`}
                        className="text-body-sm font-semibold text-secondary hover:underline"
                      >
                        Open transparency lab
                      </Link>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
        </div>
    </div>
  );
}
