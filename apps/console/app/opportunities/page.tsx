"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Empty, ErrorState, Loading, PageHeader, RowLink } from "@/components/ui";

export default function OpportunitiesPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.opportunities>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .opportunities()
      .then(setData)
      .catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading label="Ideas" />;
  if (data.opportunities.length === 0) {
    return (
      <div className="page-pad fade-in">
        <PageHeader title="Ideas" />
        <Empty title="None" hint="" className="mt-12" />
      </div>
    );
  }

  return (
    <div className="page-pad fade-in">
      <PageHeader title="Ideas" />
      <div className="surface-lg mt-8 max-w-lg divide-y divide-border">
        {data.opportunities.map((o) => (
          <RowLink key={String(o.id)} href={`/rooms/${String(o.room_id ?? o.id)}`} title={String(o.title)} />
        ))}
      </div>
    </div>
  );
}
