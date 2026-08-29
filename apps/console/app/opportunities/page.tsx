"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Badge, Card, Empty, ErrorState, Loading } from "@/components/ui";

export default function OpportunitiesPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.opportunities>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.opportunities().then(setData).catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;
  if (data.opportunities.length === 0) return <Empty title="No Type B rooms" hint="Opportunities open as rooms." />;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <h1 className="text-3xl font-semibold tracking-tight">Type B · opportunities</h1>
      {data.opportunities.map((o) => (
        <Link key={String(o.id)} href={`/rooms/${String(o.room_id ?? o.id)}`} className="block">
          <Card className="hover:border-accent/40">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium">{String(o.title)}</p>
              <Badge tone="ok">{String(o.loop_type ?? "type_b")}</Badge>
            </div>
            <p className="mt-2 font-mono text-xs text-[var(--dim)]">{String(o.status)}</p>
          </Card>
        </Link>
      ))}
    </div>
  );
}
