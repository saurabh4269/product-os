"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Action } from "@/lib/api";
import { Badge, Button, Card, Empty, ErrorState, Loading } from "@/components/ui";

export default function ApprovalsPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.approvals>> | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    try {
      setData(await api.approvals());
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;

  async function decide(a: Action, decision: "approve" | "deny") {
    setBusy(a.id);
    await api.approve(a.id, decision);
    await load();
    setBusy(null);
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-semibold">Approval queue</h1>
      {data.pending.length === 0 ? (
        <Empty title="Queue clear" hint="Risk Agent gates land here and survive restarts." />
      ) : (
        data.pending.map((a) => (
          <Card key={a.id} className="space-y-3">
            <div className="flex justify-between">
              <Badge tone="high">{a.risk_tier}</Badge>
              <Link href={`/investigations/${a.investigation_id}`} className="font-mono text-xs text-accent">
                open room
              </Link>
            </div>
            <p className="text-sm">{a.consequence}</p>
            <p className="text-xs text-[var(--dim)]">{a.tier_rationale}</p>
            <div className="flex gap-2">
              <Button disabled={busy === a.id} onClick={() => void decide(a, "approve")}>
                Approve
              </Button>
              <Button variant="ghost" disabled={busy === a.id} onClick={() => void decide(a, "deny")}>
                Deny
              </Button>
            </div>
          </Card>
        ))
      )}
    </div>
  );
}
