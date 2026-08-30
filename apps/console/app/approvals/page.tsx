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
  const [notice, setNotice] = useState<string | null>(null);
  const [prUrl, setPrUrl] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);

  async function pollJob(actionId: string, attempts = 0) {
    if (attempts > 40) {
      setJobStatus("Still running — check the room for updates.");
      return;
    }
    try {
      const st = await api.approvalStatus(actionId);
      const job = st.job;
      const url = st.pr_url || (st.execution?.pr_url as string | undefined);
      if (url) {
        setNotice("Pull request opened. Product OS did not merge it.");
        setPrUrl(url);
        setJobStatus(null);
        return;
      }
      if (job?.status === "failed" || job?.status === "dead") {
        setJobStatus(`Code fix failed: ${job.error || "see room for details"}`);
        return;
      }
      if (job?.status === "succeeded") {
        const resultUrl = (job.result?.url as string | undefined) || url;
        if (resultUrl) {
          setNotice("Pull request opened. Product OS did not merge it.");
          setPrUrl(resultUrl);
        } else {
          setJobStatus("Job finished — check the room for the PR link.");
        }
        return;
      }
      setJobStatus(`Code fix ${job?.status ?? "queued"}…`);
      window.setTimeout(() => void pollJob(actionId, attempts + 1), 3000);
    } catch {
      window.setTimeout(() => void pollJob(actionId, attempts + 1), 4000);
    }
  }

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
      const res = await api.approve(a.id, decision);
      if (decision === "approve") {
        if (res.pr_url) {
          setNotice("Pull request opened. Product OS did not merge it.");
          setPrUrl(res.pr_url);
          setJobStatus(null);
        } else if (res.execution?.flag) {
          setNotice(`Flag ${res.execution.flag} is now ${String(res.execution.value ?? "updated")}.`);
          setPrUrl(null);
          setJobStatus(null);
        } else if (res.execution?.job_id) {
          setNotice("Approved — opening a pull request in the background.");
          setPrUrl(null);
          void pollJob(a.id);
        } else {
          setNotice("Approved.");
          setPrUrl(null);
          setJobStatus(null);
        }
      }
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
      {notice ? (
        <p className="mt-4 max-w-xl text-[14px] leading-6 text-foreground">
          {notice}
          {jobStatus ? <span className="block mt-1 text-[var(--dim)]">{jobStatus}</span> : null}
          {prUrl ? (
            <>
              {" "}
              <a href={prUrl} className="text-accent" target="_blank" rel="noreferrer">
                Open on GitHub
              </a>
            </>
          ) : null}
        </p>
      ) : null}
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
                <Button disabled={busy !== null} onClick={() => void decide(a, "approve")}>
                  {busy === a.id ? "Working…" : "Approve"}
                </Button>
                <Button variant="ghost" disabled={busy !== null} onClick={() => void decide(a, "deny")}>
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
