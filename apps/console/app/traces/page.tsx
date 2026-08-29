"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { shortName } from "@/lib/names";
import { ErrorState, Loading } from "@/components/ui";
import { PixelSprite } from "@/components/pixel-office";

export default function TracesPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.traces>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .traces()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading label="Opening traces" />;

  return (
    <div className="px-8 py-10 lg:px-12">
      <p className="text-[12px] uppercase tracking-[0.2em] text-accent">Who spoke to whom</p>
      <h1 className="font-display mt-3 text-[48px] leading-none">Traces</h1>
      <div className="mt-10 space-y-3">
        {data.traces.map((t, i) => (
          <div key={String(t.id ?? i)} className="flex flex-wrap items-center gap-3 py-2">
            <PixelSprite name={String(t.from_agent ?? "")} scale={2} />
            <span className="text-[15px]">{shortName(String(t.from_agent ?? ""))}</span>
            <span className="text-[var(--faint)]">→</span>
            <PixelSprite name={String(t.to_agent ?? "")} scale={2} />
            <span className="text-[15px]">{shortName(String(t.to_agent ?? ""))}</span>
            <span className="text-[12px] text-[var(--faint)]">{String(t.summary ?? "")}</span>
          </div>
        ))}
      </div>
      <div className="mt-12">
        <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--faint)]">Policy</p>
        <div className="mt-4 space-y-2">
          {data.verdicts.map((v, i) => (
            <p key={String(v.id ?? i)} className="text-[15px]">
              <span
                className="mr-3 uppercase tracking-[0.12em]"
                style={{ color: v.verdict === "DENY" || v.verdict === "BLOCK" ? "var(--danger)" : "var(--ok)" }}
              >
                {String(v.verdict)}
              </span>
              <span className="text-[var(--dim)]">
                {String(v.agent_identity)} · {String(v.tool)}
              </span>
            </p>
          ))}
        </div>
      </div>
    </div>
  );
}
