"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Action } from "@/lib/api";
import { Button, Empty, ErrorState, Loading } from "@/components/ui";

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
    <div className="px-8 py-12 lg:px-16">
      <h1 className="text-[32px] font-semibold tracking-tight">Approvals</h1>
      <p className="mt-3 text-[15px] text-[var(--dim)]">A few changes are waiting for a yes.</p>
      {data.pending.length === 0 ? (
        <Empty title="You’re all caught up." hint="New gates will show up here." />
      ) : (
        <div className="mt-8 max-w-xl space-y-6">
          {data.pending.map((a) => (
            <article key={a.id} className="rounded-[20px] border border-border bg-white p-6">
              <p className="text-[13px] text-[var(--faint)]">{a.risk_tier}</p>
              <p className="mt-2 text-[15px] leading-6">{a.consequence}</p>
              <div className="mt-4 flex items-center gap-3">
                <Button disabled={busy === a.id} onClick={() => void decide(a, "approve")}>
                  Approve
                </Button>
                <Button variant="ghost" disabled={busy === a.id} onClick={() => void decide(a, "deny")}>
                  Not yet
                </Button>
                <Link href={`/investigations/${a.investigation_id}`} className="text-[13px] text-accent">
                  Open room
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
