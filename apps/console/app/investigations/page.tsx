"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Badge, Card, Empty, ErrorState, Loading } from "@/components/ui";

export default function InvestigationsPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.investigations>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.investigations().then(setData).catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;
  if (data.investigations.length === 0) {
    return <Empty title="No investigations" hint="Run detection from Pulse." />;
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Investigations</h1>
      <div className="space-y-2">
        {data.investigations.map((inv) => (
          <Link key={inv.id} href={`/investigations/${inv.id}`} className="block">
            <Card className="hover:border-accent/40">
              <div className="flex justify-between gap-4">
                <div>
                  <p className="font-mono text-xs text-slate-500">{inv.id}</p>
                  <p className="mt-1 text-sm">{inv.hypothesis ?? "In progress"}</p>
                </div>
                <Badge tone={inv.state === "AWAITING_APPROVAL" ? "warn" : "muted"}>{inv.state}</Badge>
              </div>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
