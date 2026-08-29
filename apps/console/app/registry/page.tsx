"use client";

import { useEffect, useState } from "react";
import { api, type RegistryAgent } from "@/lib/api";
import { Badge, Card, ErrorState, Loading } from "@/components/ui";
import { Pixel } from "@/components/pixel-office";

export default function RegistryPage() {
  const [agents, setAgents] = useState<RegistryAgent[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .registry()
      .then((r) => setAgents(r.agents))
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!agents) return <Loading label="Opening registry" />;

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Agent Registry</h1>
        <p className="mt-2 max-w-2xl text-sm text-[var(--dim)]">
          Identity, capabilities, permissions, version, environment, risk. What stops engineering from reading
          customer data is the deny list on <span className="font-mono text-foreground">loop-code</span>, not a
          prompt.
        </p>
      </div>
      <div className="grid-fade grid gap-3 md:grid-cols-2">
        {agents.map((a) => (
          <Card key={a.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <Pixel name={a.id} />
                <div>
                  <p className="text-sm font-medium">{a.display_name}</p>
                  <p className="font-mono text-[10px] text-[var(--dim)]">
                    {a.identity} · v{a.version} · {a.environment}
                  </p>
                </div>
              </div>
              <Badge tone={a.risk_level === "HIGH" ? "high" : a.risk_level === "MEDIUM" ? "warn" : "muted"}>
                {a.risk_level}
              </Badge>
            </div>
            <p className="mt-3 text-sm text-[var(--dim)]">{a.role}</p>
            <p className="mt-2 font-mono text-[10px] text-[var(--dim)]">owner {a.owner}</p>
            <div className="mt-3 flex flex-wrap gap-1">
              {a.permissions_allow.slice(0, 4).map((p) => (
                <Badge key={p} tone="ok">
                  allow {p}
                </Badge>
              ))}
              {a.permissions_deny.slice(0, 3).map((p) => (
                <Badge key={p} tone="danger">
                  deny {p}
                </Badge>
              ))}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
