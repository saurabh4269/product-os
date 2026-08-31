"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type OfficeDesk, type RegistryAgent } from "@/lib/api";
import { AgentBadge, type AgentStatus } from "@/components/agent-badge";
import { agentHref } from "@/lib/names";
import { Chip, ErrorState, Loading, PageHeader, RowLink } from "@/components/ui";

function deskStatus(desk?: OfficeDesk): AgentStatus | undefined {
  if (!desk) return undefined;
  if (desk.status === "handing_off") return "handing_off";
  if (desk.status !== "idle") return "working";
  return "idle";
}

export default function RegistryPage() {
  const [agents, setAgents] = useState<RegistryAgent[] | null>(null);
  const [desks, setDesks] = useState<OfficeDesk[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.registry(), api.office()])
      .then(([r, o]) => {
        setAgents(r.agents);
        setDesks(o.desks);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "failed"));
  }, []);

  const deskById = useMemo(() => Object.fromEntries(desks.map((d) => [d.id, d])), [desks]);

  if (err) return <ErrorState message={err} />;
  if (!agents) return <Loading label="Agents" />;

  const tone = (level: string) =>
    level === "HIGH" ? "danger" : level === "MEDIUM" ? "warn" : level === "LOW" ? "ok" : "muted";

  return (
    <div className="page-pad fade-in">
      <PageHeader title="Agents" />
      <div className="surface-lg mt-8 divide-y divide-border overflow-hidden">
        {agents.map((a) => (
          <RowLink
            key={a.id}
            href={agentHref(a.id)}
            leading={<AgentBadge name={a.id} status={deskStatus(deskById[a.id])} size={36} variant="face" />}
            title={a.display_name}
            subtitle={deskById[a.id]?.doing || a.role}
            trailing={<Chip tone={tone(a.risk_level)}>{a.risk_level}</Chip>}
          />
        ))}
      </div>
    </div>
  );
}
