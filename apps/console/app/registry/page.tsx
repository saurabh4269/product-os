"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type OfficeDesk, type RegistryAgent } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { AgentBadge, type AgentStatus } from "@/components/agent-badge";
import { AgentTrustGlyph } from "@/components/agent-trust-glyph";
import { agentHref } from "@/lib/names";
import { ErrorState, Loading } from "@/components/ui";
import { MIcon } from "@/components/ref/icon";

function deskStatus(desk?: OfficeDesk): AgentStatus | undefined {
  if (!desk) return undefined;
  if (desk.status === "handing_off") return "handing_off";
  if (desk.status !== "idle") return "working";
  return "idle";
}

/** agent_registry_workforce_management/code.html — grid cards with capabilities + live activity. */
export default function RegistryPage() {
  const { tick } = useGlobalWs();
  const [agents, setAgents] = useState<RegistryAgent[] | null>(null);
  const [desks, setDesks] = useState<OfficeDesk[]>([]);
  const [query, setQuery] = useState("");
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.registry(), api.office()])
      .then(([r, o]) => {
        setAgents(r.agents);
        setDesks(o.desks);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, [tick]);

  const deskById = useMemo(() => Object.fromEntries(desks.map((d) => [d.id, d])), [desks]);

  const fleetStats = useMemo(() => {
    const active = desks.filter((d) => d.status !== "idle");
    const idle = desks.filter((d) => d.status === "idle");
    return { active, idle };
  }, [desks]);

  const filtered = useMemo(() => {
    if (!agents) return [];
    const q = query.trim().toLowerCase();
    const rows = !q
      ? agents
      : agents.filter(
          (a) =>
            a.display_name.toLowerCase().includes(q) ||
            a.id.toLowerCase().includes(q) ||
            a.capabilities.some((c) => c.toLowerCase().includes(q))
        );
    return [...rows].sort((a, b) => {
      const aBusy = deskById[a.id]?.status !== "idle" ? 0 : 1;
      const bBusy = deskById[b.id]?.status !== "idle" ? 0 : 1;
      return aBusy - bBusy;
    });
  }, [agents, query, deskById]);

  if (err) return <ErrorState message={err} />;
  if (!agents) return <Loading label="Agents" />;

  return (
    <div className="page-pad fade-in mx-auto max-w-container-max">
      <div className="mb-margin-lg flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="text-display-lg font-bold tracking-tight text-text-primary">Agent registry</h1>
          {desks.length > 0 ? (
            <p className="mt-2 text-body-md text-text-secondary">
              {fleetStats.active.length} active · {fleetStats.idle.length} idle
            </p>
          ) : null}
        </div>
        <Link href="/data" className="text-label-lg text-primary hover:underline">
          Data plane
        </Link>
      </div>

      <div className="mb-margin-md rounded-xl border border-surface-subtle/50 bg-white p-4 shadow-[0_4px_20px_rgba(0,0,0,0.02)]">
        <div className="relative max-w-md">
          <MIcon
            name="search"
            className="absolute left-3 top-1/2 -translate-y-1/2 text-outline"
          />
          <input
            className="w-full rounded-lg border border-transparent bg-surface-base py-2.5 pl-10 pr-4 text-body-md text-text-primary outline-none transition-all placeholder:text-outline focus:border-primary/30 focus:ring-2 focus:ring-primary/20"
            placeholder="Search agents by name or capability…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((a) => {
          const desk = deskById[a.id];
          const status = deskStatus(desk);
          const working = status === "working" || status === "thinking" || status === "handing_off";
          return (
            <Link
              key={a.id}
              href={agentHref(a.id)}
              className="group relative flex flex-col overflow-hidden rounded-xl border border-surface-subtle/40 bg-white shadow-[0_4px_20px_rgba(0,0,0,0.04)] transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_8px_30px_rgba(0,0,0,0.08)]"
            >
              <div className="flex flex-1 flex-col gap-4 p-5">
                <div className="flex items-start gap-3">
                  <div className="relative shrink-0">
                    <AgentBadge name={a.id} status={status} size={48} variant="face" />
                    <span
                      className={`absolute -bottom-0.5 -right-0.5 z-10 h-3.5 w-3.5 rounded-full border-2 border-white ${
                        working ? "bg-accent-success" : "bg-surface-subtle"
                      }`}
                    />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <h3 className="truncate text-headline-sm leading-tight text-text-primary group-hover:text-primary">
                          {a.display_name}
                        </h3>
                        <p className="mt-0.5 truncate text-body-sm text-text-secondary">{a.role}</p>
                      </div>
                      <AgentTrustGlyph agent={a} />
                    </div>
                    {a.environment && a.environment !== "prod" ? (
                      <span className="mt-2 inline-block rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-amber-800">
                        {a.environment}
                      </span>
                    ) : null}
                  </div>
                </div>
                {desk?.doing ? (
                  <p
                    className={`line-clamp-2 text-body-sm leading-snug ${
                      working ? "text-text-primary" : "text-on-surface-variant"
                    }`}
                  >
                    {desk.doing}
                  </p>
                ) : (
                  <p className="text-body-sm text-outline">Idle</p>
                )}
              </div>
              <div className="flex items-center justify-end border-t border-surface-subtle/60 px-4 py-2.5">
                <MIcon
                  name="arrow_forward"
                  className="text-[18px] text-outline transition group-hover:translate-x-0.5 group-hover:text-primary"
                />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
