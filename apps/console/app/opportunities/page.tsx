"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Empty, ErrorState, Loading } from "@/components/ui";

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
  if (!data) return <Loading />;
  if (data.opportunities.length === 0) return <Empty title="No Type B rooms." hint="Opportunities open as rooms." />;

  return (
    <div className="px-8 py-10 lg:px-12">
      <p className="text-[12px] uppercase tracking-[0.2em] text-ok">Something could be better</p>
      <h1 className="font-display mt-3 text-[48px] leading-none">Opportunities</h1>
      <div className="mt-10 max-w-2xl space-y-6">
        {data.opportunities.map((o) => (
          <Link key={String(o.id)} href={`/rooms/${String(o.room_id ?? o.id)}`} className="block">
            <p className="font-display text-[28px] leading-8 hover:text-accent">{String(o.title)}</p>
            <p className="mt-1 text-[13px] text-[var(--faint)]">{String(o.status)}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
