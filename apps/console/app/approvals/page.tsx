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
    <div className="px-8 py-10 lg:px-12">
      <p className="text-[12px] uppercase tracking-[0.2em] text-accent">Waiting on a human</p>
      <h1 className="font-display mt-3 text-[48px] leading-none">Approvals</h1>
      {data.pending.length === 0 ? (
        <Empty title="Nothing at the gate." hint="Risk Agent will put work here." />
      ) : (
        <div className="mt-10 max-w-2xl space-y-10">
          {data.pending.map((a) => (
            <article key={a.id}>
              <p className="text-[11px] uppercase tracking-[0.16em] text-warn">{a.risk_tier}</p>
              <p className="font-display mt-2 text-[28px] leading-8">{a.consequence}</p>
              <p className="mt-2 text-[14px] text-[var(--dim)]">{a.tier_rationale}</p>
              <div className="mt-4 flex items-center gap-3">
                <Button disabled={busy === a.id} onClick={() => void decide(a, "approve")}>
                  Approve
                </Button>
                <Button variant="ghost" disabled={busy === a.id} onClick={() => void decide(a, "deny")}>
                  Hold
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
