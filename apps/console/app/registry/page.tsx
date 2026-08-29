"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
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
    <div className="page-pad">
      <h1 className="text-[26px] font-semibold tracking-tight sm:text-[32px]">Agents</h1>
      <p className="mt-3 max-w-lg text-[15px] leading-6 text-[var(--dim)]">
        Each person has a role and a few permissions. Open anyone to see what they’re doing.
      </p>
      <div className="mt-10 divide-y divide-border overflow-hidden rounded-[20px] border border-border bg-white">
        {agents.map((a) => (
          <Link
            key={a.id}
            href={`/agents/${a.id}`}
            className="grid grid-cols-[48px_1fr] gap-3 px-5 py-4 hover:bg-[var(--elev)] md:grid-cols-[48px_200px_1fr_80px]"
          >
            <PixelSprite name={a.id} scale={2} />
            <div>
              <p className="text-[15px] font-medium">{a.display_name}</p>
              <p className="text-[12px] text-[var(--faint)]">{a.identity}</p>
            </div>
            <p className="hidden text-[13px] leading-5 text-[var(--dim)] md:block">{a.role}</p>
            <p className="text-[12px] text-[var(--faint)]">{a.risk_level}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
