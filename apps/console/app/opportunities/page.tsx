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
  if (data.opportunities.length === 0) return <Empty title="No ideas yet." hint="They’ll show up as rooms." />;

  return (
    <div className="page-pad">
      <h1 className="text-[32px] font-semibold tracking-tight">Ideas</h1>
      <div className="mt-8 max-w-lg space-y-4">
        {data.opportunities.map((o) => (
          <Link key={String(o.id)} href={`/rooms/${String(o.room_id ?? o.id)}`} className="block text-[16px] font-medium hover:text-accent">
            {String(o.title)}
          </Link>
        ))}
      </div>
    </div>
  );
}
