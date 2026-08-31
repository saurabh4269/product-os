"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Chip, ErrorState, Loading, PageHeader } from "@/components/ui";

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
  if (!data) return <Loading label="Governance" />;

  return (
    <div className="page-pad fade-in">
      <PageHeader
        title="Governance"
        action={
          <Chip tone={data.failOpen ? "danger" : "ok"}>{data.failOpen ? "failOpen" : "fail closed"}</Chip>
        }
      />
      <div className="surface-lg mt-8 max-w-xl divide-y divide-border">
        {data.identities.map((id) => (
          <div key={id.id} className="flex justify-between gap-6 px-5 py-3.5">
            <p className="text-[14px] font-medium">{id.id}</p>
            <p className="text-right text-[13px] text-[var(--dim)]">{id.envelope}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
