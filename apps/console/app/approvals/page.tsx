"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, hasAdminToken, type Action, type Room } from "@/lib/api";
import { Button, Empty, ErrorState, Loading } from "@/components/ui";
import { ProofEmbed, proofFromArtifact, type ProofPayload } from "@/components/proof-embed";
import { MIcon } from "@/components/ref/icon";
import { ToolSurfaceRail } from "@/components/ref/tool-surface-rail";

/**
 * approvals_governance_lab/code.html detail panel — one gate at a time with embedded GitHub,
 * not a split inbox queue.
 */
export default function ApprovalsPage() {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.approvals>> | null>(null);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [prUrl, setPrUrl] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string | null>(null);
  const [needsAdmin, setNeedsAdmin] = useState(false);
  const [pick, setPick] = useState(0);
  const [toolCards, setToolCards] = useState<ProofPayload[]>([]);

  useEffect(() => {
    api.config().then((c) => setNeedsAdmin(Boolean(c.hosted && !c.eval_mode && !hasAdminToken()))).catch(() => undefined);
    api
      .proof()
      .then((pf) => {
        const cards = [pf.github, pf.gateway, pf.flags, ...(pf.cards || [])].filter(
          (c): c is ProofPayload => Boolean(c && (c as ProofPayload).kind)
        );
        setToolCards(cards);
      })
      .catch(() => undefined);
  }, []);

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

  const pending = data?.pending ?? [];
  const action = pending[pick] ?? pending[0];

  const githubProof = useMemo(() => {
    if (!action) return null;
    const art = action.artifacts as Record<string, unknown>;
    const exec = (art?.execution ?? {}) as Record<string, unknown>;
    return (
      proofFromArtifact({ ...exec, pr_url: exec.pr_url, proof: exec.proof }, "pr") ||
      proofFromArtifact(art, "code_fix")
    );
  }, [action]);

  if (err) return <ErrorState message={err} />;
  if (!data) return <Loading />;

  function roomHref(a: Action) {
    const room = rooms.find((r) => r.investigation_id === a.investigation_id);
    return room ? `/rooms/${room.id}?view=lab` : "/";
  }

  async function decide(a: Action, decision: "approve" | "deny") {
    setBusy(a.id);
    try {
      const res = await api.approve(a.id, decision);
      if (decision === "approve") {
        if (res.pr_url) {
          setNotice("Pull request opened. Product OS did not merge it.");
          setPrUrl(res.pr_url);
        } else if (res.execution?.job_id) {
          setNotice("Approved. Opening a pull request.");
        } else {
          setNotice("Approved.");
        }
      }
      await load();
      setPick(0);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page-pad fade-in mx-auto max-w-6xl">
      <header className="mb-margin-md flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <h1 className="mb-2 text-headline-lg text-on-surface">Pending approvals</h1>
        </div>
        {pending.length > 1 ? (
          <div className="flex items-center gap-2 text-body-sm text-on-surface-variant">
            <button
              type="button"
              className="rounded-lg border border-outline-variant px-2 py-1 disabled:opacity-40"
              disabled={pick <= 0}
              onClick={() => setPick((p) => Math.max(0, p - 1))}
            >
              ←
            </button>
            <span>
              {pick + 1} / {pending.length}
            </span>
            <button
              type="button"
              className="rounded-lg border border-outline-variant px-2 py-1 disabled:opacity-40"
              disabled={pick >= pending.length - 1}
              onClick={() => setPick((p) => Math.min(pending.length - 1, p + 1))}
            >
              →
            </button>
          </div>
        ) : null}
      </header>

      {needsAdmin ? (
        <p className="mb-4 max-w-xl rounded-xl border border-border bg-[#fbfbfd] px-4 py-3 text-[14px] text-[var(--dim)]">
          Hosted production requires an admin token.{" "}
          <Link href="/settings" className="text-accent hover:underline">
            Connect → Authorize
          </Link>
        </p>
      ) : null}

      {notice ? <p className="mb-4 text-body-md text-on-surface">{notice}</p> : null}
      {jobStatus ? <p className="mb-4 text-body-sm text-on-surface-variant">{jobStatus}</p> : null}
      {prUrl ? (
        <a href={prUrl} className="mb-4 inline-block text-accent hover:underline" target="_blank" rel="noreferrer">
          Open GitHub PR →
        </a>
      ) : null}

      {pending.length === 0 ? (
        <Empty title="Clear" hint="No gates waiting — agents will surface PRs and flags here." className="mt-12" />
      ) : action ? (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,0.9fr)]">
          <article className="overflow-hidden rounded-xl border border-surface-subtle bg-white shadow-[0_4px_20px_rgba(0,0,0,0.04)]">
            <div className="flex items-start justify-between border-b border-surface-subtle bg-surface-bright p-6">
              <div>
                <div className="mb-2 flex items-center gap-3">
                  <MIcon name="merge" className="text-[24px] text-primary" />
                  <h2 className="text-headline-md text-on-surface">
                    {action.tenant_repo ? `Change on ${action.tenant_repo}` : "Proposed action"}
                  </h2>
                  <span
                    className={`ml-2 rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${
                      action.risk_tier === "HIGH"
                        ? "bg-error-container text-on-error-container"
                        : "bg-surface-container text-on-surface-variant"
                    }`}
                  >
                    {action.risk_tier} risk
                  </span>
                </div>
                <p className="text-body-md text-text-secondary">{action.gate || action.tier_rationale}</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" disabled={busy !== null} onClick={() => void decide(action, "deny")}>
                  Deny
                </Button>
                <Button disabled={busy !== null} onClick={() => void decide(action, "approve")}>
                  <MIcon name="check_circle" className="mr-1 text-[18px]" />
                  {busy === action.id ? "…" : "Approve"}
                </Button>
              </div>
            </div>

            <div className="space-y-8 p-6">
              <section>
                <h3 className="mb-3 flex items-center gap-2 text-label-lg text-on-surface">
                  <MIcon name="psychology" className="text-[18px] text-text-secondary" />
                  Agent rationale
                </h3>
                <div className="rounded-lg border border-surface-subtle bg-surface-base p-4">
                  <p className="text-body-md leading-relaxed text-on-surface-variant">{action.consequence}</p>
                </div>
              </section>

              <section>
                <h3 className="mb-3 flex items-center gap-2 text-label-lg text-on-surface">
                  <MIcon name="shield" className="text-[18px] text-text-secondary" />
                  Model armor scan
                </h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="flex items-start gap-3 rounded-lg border border-surface-subtle bg-surface-base p-4">
                    <MIcon name="verified" className="mt-0.5 text-accent-success" />
                    <div>
                      <h4 className="text-label-lg text-on-surface">Policy gate</h4>
                      <p className="mt-1 text-body-sm text-text-secondary">
                        {action.gate_mode || "fail closed"} · human approval required for {action.risk_tier} tier
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3 rounded-lg border border-surface-subtle bg-surface-base p-4">
                    <MIcon name="verified" className="mt-0.5 text-accent-success" />
                    <div>
                      <h4 className="text-label-lg text-on-surface">Exfil guard</h4>
                      <p className="mt-1 text-body-sm text-text-secondary">
                        Customer record export denied at gateway identity — not prompt-only.
                      </p>
                    </div>
                  </div>
                </div>
              </section>

              <section>
                <h3 className="mb-3 flex items-center gap-2 text-label-lg text-on-surface">
                  <MIcon name="code" className="text-[18px] text-text-secondary" />
                  GitHub · live PR surface
                </h3>
                {githubProof ? (
                  <ProofEmbed proof={githubProof} />
                ) : (
                  <p className="text-body-sm text-on-surface-variant">
                    PR embed appears after code agent stages the change — approve to open on GitHub.
                  </p>
                )}
              </section>

              <Link href={roomHref(action)} className="inline-flex items-center gap-1 text-body-sm font-semibold text-secondary">
                Open full transparency lab <MIcon name="open_in_new" className="text-[14px]" />
              </Link>
            </div>
          </article>

          <ToolSurfaceRail title="Connected tools" cards={toolCards} />
        </div>
      ) : null}
    </div>
  );
}
