"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, hasAdminToken, type Action, type Room } from "@/lib/api";
import { Button, Chip, Empty, ErrorState, Loading, PageHeader } from "@/components/ui";

export default function ApprovalsPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.approvals>> | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [prUrl, setPrUrl] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<string | null>(null);
  const [needsAdmin, setNeedsAdmin] = useState(false);

  useEffect(() => {
    api.config().then((c) => setNeedsAdmin(Boolean(c.hosted && !c.eval_mode && !hasAdminToken()))).catch(() => undefined);
  }, []);

  async function pollJob(actionId: string, attempts = 0) {
    if (attempts > 40) {
      setJobStatus("Still running. Check the room.");
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
        const detail = job.error || (job.result?.detail as string | undefined) || "see room for details";
        setJobStatus(`Code fix failed: ${detail}`);
        setJobDetail(JSON.stringify(job.result || {}, null, 2));
        return;
      }
      if (job?.status === "succeeded") {
        const resultUrl = (job.result?.url as string | undefined) || url;
        if (resultUrl) {
          setNotice("Pull request opened. Product OS did not merge it.");
          setPrUrl(resultUrl);
        } else {
          setJobStatus("Done. Check the room for the PR link.");
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
    return room ? `/rooms/${room.id}` : "/";
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
          setNotice("Approved. Opening a pull request.");
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
    <div className="page-pad fade-in">
      <PageHeader title="Approvals" />
      {needsAdmin ? (
        <p className="mt-4 max-w-xl rounded-xl border border-border bg-[#fbfbfd] px-4 py-3 text-[14px] leading-6 text-[var(--dim)]">
          Hosted production requires an admin token to approve.{" "}
          <Link href="/connect" className="text-accent hover:underline">
            Connect → Authorize
          </Link>{" "}
          if you have not pasted <code className="text-[12px]">LOOP_ADMIN_TOKEN</code> yet.
        </p>
      ) : null}
      {notice ? (
        <p className="mt-4 max-w-xl text-[14px] leading-6 text-foreground">
          {notice}
          {jobStatus ? <span className="mt-1 block text-[var(--dim)]">{jobStatus}</span> : null}
          {jobDetail ? (
            <pre className="mt-2 max-h-40 overflow-auto rounded-lg bg-[#f5f5f7] p-3 text-[11px] text-[var(--dim)]">
              {jobDetail}
            </pre>
          ) : null}
          {prUrl ? (
            <>
              {" "}
              <a href={prUrl} className="text-accent" target="_blank" rel="noreferrer">
                GitHub
              </a>
            </>
          ) : null}
        </p>
      ) : null}
      {data.pending.length === 0 ? (
        <Empty title="Clear" hint="" className="mt-12" />
      ) : (
        <div className="mt-8 max-w-xl space-y-4">
          {data.pending.map((a) => (
            <article key={a.id} className="surface-lg p-6">
              <Chip tone={a.risk_tier === "HIGH" ? "danger" : "warn"}>{a.risk_tier}</Chip>
              <p className="mt-3 text-[15px] leading-6">{a.consequence}</p>
              {a.gate || a.tenant_repo ? (
                <p className="mt-2 text-[13px] leading-5 text-[var(--faint)]">
                  {a.gate || (a.tenant_repo ? `PR on ${a.tenant_repo}` : null)}
                </p>
              ) : null}
              <div className="mt-5 flex flex-wrap items-center gap-2">
                <Button disabled={busy !== null} onClick={() => void decide(a, "approve")}>
                  {busy === a.id ? "…" : "Approve"}
                </Button>
                <Button variant="ghost" disabled={busy !== null} onClick={() => void decide(a, "deny")}>
                  Not yet
                </Button>
                <Link href={roomHref(a)} className="ml-auto text-[13px] text-accent">
                  Room →
                </Link>
              </div>
            </article>
          ))}
        </div>
      )}
      {data.history.length ? (
        <div className="surface-lg mt-12 max-w-xl divide-y divide-border">
          {data.history.slice(0, 8).map((h, i) => (
            <p key={String(h.id ?? i)} className="px-5 py-3 text-[14px] leading-6 text-[var(--dim)]">
              <span className="font-medium text-foreground">{String(h.decision ?? "decision")}</span>
              {h.tier_at_decision ? ` · ${String(h.tier_at_decision)}` : ""}
              {h.rationale ? `. ${String(h.rationale)}` : ""}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
