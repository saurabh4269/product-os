"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { Button } from "@/components/ui";
import { cn } from "@/lib/utils";

export type IncidentStep = {
  id: string;
  label: string;
  detail?: string;
  done: boolean;
  active?: boolean;
  href?: string | null;
  room_id?: string | null;
  action_id?: string | null;
};

export type IncidentLifecycle = {
  status: string;
  tenant_id: string;
  checkout_url?: string | null;
  deploy_url?: string | null;
  room_id?: string | null;
  investigation_id?: string | null;
  investigation_state?: string | null;
  pending_action_id?: string | null;
  execution?: { pr_url?: string; flag?: string } | null;
  steps: IncidentStep[];
  progress: { done: number; total: number };
  ready_for_checkout?: boolean;
  pay_sdk_active?: string;
  regression_active?: boolean;
  phase?: string;
  headline?: string;
  subtitle?: string;
  product_status?: string;
  last_ingest_at?: string | null;
  flags?: Record<string, string>;
};

const BANNER: Record<string, { ring: string; bg: string; dot: string }> = {
  degraded: { ring: "border-amber-300/80", bg: "bg-amber-50/90", dot: "bg-amber-500" },
  signal_received: { ring: "border-accent/40", bg: "bg-accent/5", dot: "bg-accent animate-pulse" },
  diagnosing: { ring: "border-accent/40", bg: "bg-accent/5", dot: "bg-accent animate-pulse" },
  awaiting_approval: { ring: "border-violet-300/70", bg: "bg-violet-50/80", dot: "bg-violet-500" },
  verifying: { ring: "border-emerald-300/70", bg: "bg-emerald-50/80", dot: "bg-emerald-500 animate-pulse" },
  recovered: { ring: "border-emerald-300/70", bg: "bg-emerald-50/80", dot: "bg-emerald-600" },
  healthy: { ring: "border-border", bg: "bg-[var(--elev)]", dot: "bg-[var(--faint)]" },
  idle: { ring: "border-border", bg: "bg-[var(--elev)]", dot: "bg-[var(--faint)]" },
};

/** Checkout regression on Product Y — live status + pipeline progress. */
export function LiveIncidentPanel({ tenantId, adminReady }: { tenantId: string; adminReady: boolean }) {
  const [life, setLife] = useState<IncidentLifecycle | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { connection, incidentLifecycle } = useGlobalWs();
  const wsLive = connection === "live";

  const refresh = useCallback(async () => {
    try {
      const next = await api.incidentLifecycle(tenantId);
      setLife(next);
      setErr(null);
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not load incident status";
      if (/404|not found/i.test(msg)) {
        setErr("Incident status needs a newer LOOP deploy.");
      } else if (/401|403|admin/i.test(msg)) {
        setErr("Authorize admin token above to watch diagnosis live.");
      } else {
        setErr(msg);
      }
    }
  }, [tenantId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (incidentLifecycle?.tenantId === tenantId) {
      setLife(incidentLifecycle.lifecycle as IncidentLifecycle);
      setErr(null);
    }
  }, [incidentLifecycle, tenantId]);

  useEffect(() => {
    const phase = life?.phase;
    const activePhase = phase === "diagnosing" || phase === "signal_received";
    const ms = wsLive
      ? activePhase
        ? 30_000
        : 60_000
      : activePhase
        ? 8000
        : 15_000;
    const id = window.setInterval(() => {
      void refresh();
    }, ms);
    return () => window.clearInterval(id);
  }, [life?.phase, refresh, wsLive]);

  async function resetRegression() {
    setBusy(true);
    try {
      const out = await api.armIncident(tenantId);
      setLife(out.lifecycle as IncidentLifecycle);
      setErr(null);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Reset failed");
    } finally {
      setBusy(false);
    }
  }

  const checkoutExternal = life?.checkout_url?.startsWith("http") ? life.checkout_url : null;
  const phase = life?.phase ?? "idle";
  const banner = BANNER[phase] ?? BANNER.idle;
  const canReset = adminReady && life && !life.regression_active && (life.progress?.done ?? 0) >= 4;

  return (
    <section className="surface-lg mt-8 max-w-xl space-y-4 p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">
            Active incident · checkout
          </p>
        </div>
        {life ? (
          <p className="text-[12px] font-medium text-[var(--faint)]">
            {life.progress.done}/{life.progress.total}
          </p>
        ) : null}
      </div>

      {life?.headline ? (
        <div className={cn("rounded-xl border px-4 py-3", banner.ring, banner.bg)}>
          <div className="flex items-start gap-3">
            <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", banner.dot)} aria-hidden />
            <div className="min-w-0">
              <p className="text-[15px] font-semibold tracking-tight text-foreground">{life.headline}</p>
              {life.subtitle ? (
                <p className="mt-1 text-[13px] leading-5 text-[var(--dim)]">{life.subtitle}</p>
              ) : null}
              {phase === "degraded" && checkoutExternal ? (
                <p className="mt-2 text-[12px] text-[var(--faint)]">
                  Reproduce: cart → checkout → Pay now. Product OS will ingest the hang automatically.
                </p>
              ) : null}
              {phase === "diagnosing" && life.room_id ? (
                <Link href={`/rooms/${life.room_id}`} className="mt-2 inline-block text-[13px] font-medium text-accent hover:underline">
                  Watch agents in the room →
                </Link>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}

      {err ? <p className="text-[13px] text-red-600">{err}</p> : null}

      <div className="flex flex-wrap gap-2">
        {checkoutExternal && phase !== "recovered" ? (
          <a
            href={checkoutExternal}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center rounded-full border border-accent/40 bg-accent/5 px-4 py-2 text-[13px] font-medium text-accent transition hover:bg-accent/10"
          >
            {phase === "degraded" ? "Reproduce at checkout ↗" : "Open Product Y checkout ↗"}
          </a>
        ) : null}
        {life?.room_id ? (
          <Link
            href={`/rooms/${life.room_id}`}
            className="inline-flex items-center rounded-full border border-border bg-white px-4 py-2 text-[13px] font-medium text-foreground transition hover:bg-[var(--elev)]"
          >
            Open room
          </Link>
        ) : null}
        {life?.pending_action_id ? (
          <Link
            href={`/approvals?focus=${life.pending_action_id}`}
            className="inline-flex items-center rounded-full border border-accent/30 px-4 py-2 text-[13px] font-medium text-accent"
          >
            Approve fix
          </Link>
        ) : null}
        <Button type="button" variant="ghost" disabled={busy} onClick={() => void refresh()}>
          Refresh
        </Button>
        {canReset ? (
          <Button type="button" variant="ghost" disabled={busy} onClick={() => void resetRegression()}>
            Reset checkout regression
          </Button>
        ) : null}
      </div>

      <ol className="space-y-2">
        {(life?.steps ?? []).map((step, i) => (
          <li
            key={step.id}
            className={cn(
              "flex gap-3 rounded-xl border px-3 py-2.5 text-[13px] transition-colors",
              step.done && "border-emerald-200/80 bg-emerald-50/50",
              step.active && !step.done && "border-accent/40 bg-accent/5 ring-1 ring-accent/20",
              !step.done && !step.active && "border-border bg-white"
            )}
          >
            <span
              className={cn(
                "mt-0.5 font-semibold tabular-nums",
                step.done ? "text-emerald-700" : step.active ? "text-accent" : "text-[var(--faint)]"
              )}
            >
              {step.done ? "✓" : i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p
                className={cn(
                  "font-medium",
                  step.done ? "text-emerald-900" : step.active ? "text-foreground" : "text-foreground"
                )}
              >
                {step.label}
                {step.active && !step.done ? (
                  <span className="ml-2 text-[11px] font-normal text-accent">in progress</span>
                ) : null}
              </p>
              {step.detail ? <p className="mt-0.5 text-[12px] leading-5 text-[var(--faint)]">{step.detail}</p> : null}
              {step.href && step.href.startsWith("/") ? (
                <Link href={step.href} className="mt-1 inline-block text-[12px] text-accent hover:underline">
                  Open in console →
                </Link>
              ) : null}
              {step.href && step.href.startsWith("http") ? (
                <a href={step.href} target="_blank" rel="noreferrer" className="mt-1 inline-block text-[12px] text-accent hover:underline">
                  Open Product Y →
                </a>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
