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
    <div className="page-pad">
      <h1 className="text-[32px] font-semibold tracking-tight">Governance</h1>
      <p className="mt-3 text-[15px] text-[var(--dim)]">Safety stays closed if something fails. failOpen = {String(data.failOpen)}.</p>
      <div className="mt-8 max-w-xl space-y-3">
        {data.identities.map((id) => (
          <div key={id.id} className="flex justify-between gap-6 border-b border-border py-3">
            <p className="text-[14px]">{id.id}</p>
            <p className="text-right text-[13px] text-[var(--dim)]">{id.envelope}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
