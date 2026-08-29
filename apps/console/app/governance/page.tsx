"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ErrorState, Loading } from "@/components/ui";

export default function GovernancePage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.governance>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .governance()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;

  return (
    <div className="px-8 py-10 lg:px-12">
      <p className="text-[12px] uppercase tracking-[0.2em] text-accent">Security plane</p>
      <h1 className="font-display mt-3 text-[48px] leading-none">Governance</h1>
      <p className="mt-6 font-display text-[40px] leading-none text-ok">
        failOpen = {String(data.failOpen)}
      </p>
      <div className="mt-12 max-w-2xl space-y-4">
        {data.identities.map((id) => (
          <div key={id.id} className="flex justify-between gap-6 border-b border-border py-3">
            <p className="text-[15px]">{id.id}</p>
            <p className="text-right text-[14px] text-[var(--dim)]">{id.envelope}</p>
          </div>
        ))}
      </div>
      <div className="mt-12 max-w-2xl space-y-2">
        {data.verdicts.map((v) => (
          <p key={String(v.id)} className="text-[14px] text-danger">
            {String(v.verdict)} · {String(v.tool)} — {String(v.rationale)}
          </p>
        ))}
      </div>
    </div>
  );
}
