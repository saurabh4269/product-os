"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Badge, Card, ErrorState, Loading } from "@/components/ui";

export default function GovernancePage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.governance>> | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.governance().then(setData).catch((e) => setErr(e.message));
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Governance</h1>
      <Card>
        <p className="font-mono text-[11px] uppercase text-slate-500">Safety pins</p>
        <div className="mt-3 flex gap-2">
          <Badge tone={data.failOpen ? "danger" : "ok"}>failOpen={String(data.failOpen)}</Badge>
          <Badge tone="ok">tool-output screen on</Badge>
        </div>
      </Card>
      <div className="grid gap-3 md:grid-cols-2">
        {data.identities.map((id) => (
          <Card key={id.id}>
            <p className="font-mono text-sm">{id.id}</p>
            <p className="mt-1 text-sm text-slate-400">{id.envelope}</p>
          </Card>
        ))}
      </div>
      <Card>
        <p className="font-mono text-[11px] uppercase text-slate-500">Policy verdicts</p>
        {data.verdicts.length === 0 ? (
          <p className="mt-2 text-sm text-slate-400">No blocks yet. Injected tool output is logged here.</p>
        ) : (
          data.verdicts.map((v) => (
            <p key={String(v.id)} className="mt-2 text-sm text-red-300">
              {String(v.verdict)} · {String(v.tool)} — {String(v.rationale)}
            </p>
          ))
        )}
      </Card>
    </div>
  );
}
