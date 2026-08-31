"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useDemoGuide } from "@/lib/demo-guide-context";
import { useHumanInput } from "@/lib/human-input-context";
import { setPipelineHighlight } from "@/lib/pipeline-highlight";
import { useToast } from "@/lib/toast-context";
import { Button } from "@/components/ui";

async function promptHumanInput(
  hitl: ReturnType<typeof useHumanInput>,
  pending: { room_id?: string; action_id?: string; title?: string }
) {
  if (!hitl) return;
  try {
    const oauth = await api.oauth();
    if (!oauth.connected) {
      hitl.setPendingOAuth({
        reason: "Calendar holds and Gmail drafts need Workspace OAuth once. Send stays off.",
        authorize_url: oauth.authorize_url || "/api/oauth/google/start",
        redirect_uri: oauth.redirect_uri,
        room_id: pending.room_id,
      });
      return;
    }
    const suggested = await api.calendarSuggest({ limit: 5 });
    if (suggested.slots?.length) {
      hitl.setPendingCalendar({
        title: pending.title || "Post-approve review",
        room_id: pending.room_id,
        action_id: pending.action_id,
        slots: suggested.slots,
      });
    }
  } catch {
    /* optional */
  }
}

export function ApprovalModal() {
  const demo = useDemoGuide();
  const hitl = useHumanInput();
  const toast = useToast();
  const pending = demo?.pendingApproval;
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (!pending?.action_id) return null;

  async function decide(decision: "approve" | "deny") {
    if (!pending?.action_id) return;
    setBusy(true);
    setErr(null);
    try {
      const out = await api.approve(pending.action_id, decision);
      demo?.setPendingApproval(null);
      if (decision === "approve") {
        demo?.setHighlightStage("verify");
        setPipelineHighlight("verify");
        toast?.push("Approved — fleet continuing", { hot: true });
        const prUrl = out.pr_url || out.execution?.pr_url;
        if (prUrl) toast?.push("Pull request opened", { href: prUrl, hot: true });
        await promptHumanInput(hitl, pending);
      } else {
        toast?.push("Change held — more evidence needed");
        demo?.setFleetWorking(false);
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Approval failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-black/20 p-4 sm:items-center">
      <div
        className="w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-xl"
        role="dialog"
        aria-labelledby="approval-title"
      >
        <p className="text-[13px] text-[var(--faint)]">Needs your look · {pending.risk_tier || "HIGH"}</p>
        <h2 id="approval-title" className="mt-1 text-[20px] font-semibold tracking-tight">
          {pending.title || "Change waiting on you"}
        </h2>
        <p className="mt-3 text-[14px] leading-6 text-[var(--dim)]">
          {pending.consequence || "Review evidence in the room before approving."}
        </p>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={() => void decide("approve")} disabled={busy}>
            {busy ? "Working…" : "Approve"}
          </Button>
          <Button variant="ghost" onClick={() => void decide("deny")} disabled={busy}>
            Not yet
          </Button>
          {pending.room_id ? (
            <a href={`/rooms/${pending.room_id}`} className="self-center text-[13px] text-accent hover:underline">
              Open room
            </a>
          ) : null}
        </div>
        {err ? <p className="mt-3 text-[13px] text-red-600">{err}</p> : null}
      </div>
    </div>
  );
}
