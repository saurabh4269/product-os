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
  if (!agents) return <Loading label="Opening the registry" />;

  return (
    <div className="px-8 py-10 lg:px-12">
      <p className="text-[12px] uppercase tracking-[0.2em] text-accent">Who is allowed</p>
      <h1 className="font-display mt-3 text-[48px] leading-none">Registry</h1>
      <p className="mt-4 max-w-xl text-[16px] leading-7 text-[var(--dim)]">
        Identity first. Engineering cannot read customer records because <em>loop-code</em> is denied that
        permission — not because a prompt said please don’t.
      </p>
      <div className="rise mt-10 divide-y divide-border">
        {agents.map((a) => (
          <div key={a.id} className="grid grid-cols-[56px_1fr] gap-4 py-6 md:grid-cols-[56px_220px_1fr_120px]">
            <PixelSprite name={a.id} scale={3} />
            <div>
              <p className="text-[16px] leading-5">{a.display_name}</p>
              <p className="mt-1 text-[12px] text-[var(--faint)]">
                {a.identity} · {a.version}
              </p>
            </div>
            <p className="hidden text-[14px] leading-6 text-[var(--dim)] md:block">{a.role}</p>
            <p
              className="text-[12px] uppercase tracking-[0.14em]"
              style={{
                color: a.risk_level === "HIGH" ? "var(--danger)" : a.risk_level === "MEDIUM" ? "var(--warn)" : "var(--dim)",
              }}
            >
              {a.risk_level}
            </p>
            <div className="col-span-full flex flex-wrap gap-x-4 gap-y-1 text-[12px] md:col-start-2">
              {a.permissions_allow.slice(0, 3).map((p) => (
                <span key={p} className="text-ok">
                  {p}
                </span>
              ))}
              {a.permissions_deny.slice(0, 3).map((p) => (
                <span key={p} className="text-danger">
                  {p}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
