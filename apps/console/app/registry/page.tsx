"use client";

import { useEffect, useState } from "react";
import { api, type RegistryAgent } from "@/lib/api";
import { ErrorState, Loading } from "@/components/ui";
import { PixelSprite } from "@/components/pixel-office";

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
  if (!agents) return <Loading label="Opening agents" />;

  return (
    <div className="px-8 py-12 lg:px-16">
      <h1 className="text-[32px] font-semibold tracking-tight">Agents</h1>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        Each person has a role and a few permissions. Engineering can’t read customer records because that
        permission is off.
      </p>
      <div className="mt-10 divide-y divide-border overflow-hidden rounded-[20px] border border-border bg-white">
        {agents.map((a) => (
          <div key={a.id} className="grid grid-cols-[48px_1fr] gap-3 px-5 py-4 md:grid-cols-[48px_200px_1fr_80px]">
            <PixelSprite name={a.id} scale={2} />
            <div>
              <p className="text-[15px] font-medium">{a.display_name}</p>
              <p className="text-[12px] text-[var(--faint)]">{a.identity}</p>
            </div>
            <p className="hidden text-[13px] leading-5 text-[var(--dim)] md:block">{a.role}</p>
            <p className="text-[12px] text-[var(--faint)]">{a.risk_level}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
