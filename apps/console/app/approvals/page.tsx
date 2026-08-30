"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Action, type Room } from "@/lib/api";
import { Button, Empty, ErrorState, Loading } from "@/components/ui";

export default function ApprovalsPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.approvals>> | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function load() {
    try {
      const [next, listed] = await Promise.all([api.approvals(), api.rooms()]);
      setData(next);
      setRooms(listed.rooms);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;

  function roomHref(a: Action) {
    const room = rooms.find((r) => r.investigation_id === a.investigation_id);
    return room ? `/rooms/${room.id}` : `/investigations/${a.investigation_id}`;
  }

  async function decide(a: Action, decision: "approve" | "deny") {
    setBusy(a.id);
    try {
      await api.approve(a.id, decision);
      await load();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page-pad">
      <h1 className="text-[26px] font-semibold tracking-tight sm:text-[32px]">Approvals</h1>
      <p className="mt-3 text-[15px] text-[var(--dim)]">A few changes are waiting for a yes.</p>
      {data.pending.length === 0 ? (
        <Empty title="You’re all caught up." hint="New gates will show up here." />
      ) : (
        <div className="mt-8 max-w-xl space-y-6">
          {data.pending.map((a) => (
            <article key={a.id} className="rounded-[20px] border border-border bg-white p-6">
              <p className="text-[13px] text-[var(--faint)]">{a.risk_tier}</p>
              <p className="mt-2 text-[15px] leading-6">{a.consequence}</p>
              <p className="mt-2 text-[13px] leading-5 text-[var(--dim)]">
                {a.gate ||
                  (a.tenant_repo
                    ? `Will open a pull request on ${a.tenant_repo}. Product OS will not merge it.`
                    : "Will only flip an OS flag. No git repo is connected.")}
              </p>
              <div className="mt-4 flex items-center gap-3">
                <Button disabled={busy === a.id} onClick={() => void decide(a, "approve")}>
                  Approve
                </Button>
                <Button variant="ghost" disabled={busy === a.id} onClick={() => void decide(a, "deny")}>
                  Not yet
                </Button>
                <Link href={roomHref(a)} className="text-[13px] text-accent">
                  Open room
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
      {data.history.length ? (
        <div className="mt-12 max-w-xl">
          <p className="text-[13px] text-[var(--faint)]">Already decided</p>
          <div className="mt-4 space-y-3">
            {data.history.slice(0, 8).map((h, i) => (
              <p key={String(h.id ?? i)} className="text-[14px] leading-6 text-[var(--dim)]">
                <span className="font-medium text-foreground">{String(h.decision ?? "decision")}</span>
                {h.tier_at_decision ? ` · ${String(h.tier_at_decision)}` : ""}
                {h.rationale ? ` — ${String(h.rationale)}` : ""}
              </p>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
