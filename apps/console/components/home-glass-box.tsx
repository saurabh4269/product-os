"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiAuthError, hasAdminToken } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { useDebouncedWorldTick } from "@/lib/world-refresh";
import { ProofEmbed, ProofGrid, type ProofPayload } from "@/components/proof-embed";
import { LiveWorkBoard, type LiveWorkCard } from "@/components/live-work-board";
import { cn } from "@/lib/utils";
import { ExternalLink } from "lucide-react";

function SkipChip({ detail }: { detail: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-dashed border-[var(--faint)]/40 bg-[var(--elev)] px-2 py-0.5 text-[10px] text-[var(--faint)]">
      Skipped · {detail}
    </span>
  );
}

function FeaturedCard({ card }: { card: LiveWorkCard }) {
  return (
    <Link
      href={`/rooms/${card.room_id}`}
      className="block overflow-hidden rounded-2xl border border-border bg-white shadow-sm transition hover:border-accent/30"
    >
      <div className="border-b border-border/60 px-3.5 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-accent">
            {card.badge}
          </span>
          {card.tenant_product ? (
            <span className="text-[10px] text-[var(--faint)]">{card.tenant_product}</span>
          ) : null}
        </div>
        <p className="mt-1.5 text-[14px] font-medium leading-5 text-foreground line-clamp-2">{card.text}</p>
        {card.room_title ? (
          <p className="mt-1 text-[11px] text-[var(--faint)]">{card.room_title}</p>
        ) : null}
      </div>
      {card.proof ? (
        <div className="px-2.5 py-2" onClick={(e) => e.preventDefault()}>
          <ProofEmbed proof={card.proof as ProofPayload} compact className="mt-0" />
        </div>
      ) : null}
      <p className="border-t border-border/50 px-3.5 py-2 text-[11px] text-accent">Open room →</p>
    </Link>
  );
}

/** Live tool receipts — BQ, GitHub, mail, flags — without leaving home. */
export function HomeGlassBox({ className }: { className?: string }) {
  const { tick, connection } = useGlobalWs();
  const worldTick = useDebouncedWorldTick(tick);
  const [proofs, setProofs] = useState<ProofPayload[]>([]);
  const [skips, setSkips] = useState<string[]>([]);
  const [featured, setFeatured] = useState<LiveWorkCard | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [needsAuth, setNeedsAuth] = useState(false);

  const loadGlass = useCallback(() => {
    setNeedsAuth(false);
    Promise.all([api.proof(), api.liveWork()])
      .then(([pf, lw]) => {
        const cards = ((pf.cards || []) as ProofPayload[]).filter((c) => c?.kind);
        const trio = [pf.github, pf.warehouse, pf.ga4, pf.workspace, pf.gateway]
          .filter(Boolean)
          .map((c) => c as ProofPayload);
        const merged = [...cards, ...trio].filter((c) => c.kind);
        const unique: ProofPayload[] = [];
        const seen = new Set<string>();
        for (const p of merged) {
          const key = `${p.kind}-${p.title}-${p.status}`;
          if (seen.has(key)) continue;
          seen.add(key);
          unique.push(p);
        }
        setProofs(unique.filter((p) => p.status !== "skipped").slice(0, 6));
        setSkips(
          merged
            .filter((p) => p.status === "skipped")
            .map((p) => String(p.detail || p.title || p.kind))
            .slice(0, 4)
        );
        const withProof = (lw.cards || []).find((c) => c.proof || c.pr_url || c.bq_url);
        setFeatured(withProof || lw.cards?.[0] || null);
        setLoaded(true);
      })
      .catch((err) => {
        if (err instanceof ApiAuthError && (err.status === 401 || err.status === 403)) {
          setNeedsAuth(true);
        }
        setProofs([]);
        setFeatured(null);
        setLoaded(true);
      });
  }, []);

  useEffect(() => {
    loadGlass();
  }, [worldTick, loadGlass]);

  const live = connection === "live";
  const empty = loaded && !needsAuth && !proofs.length && !featured;

  const authHint = useMemo(
    () =>
      needsAuth ? (
        <div className="rounded-2xl border border-dashed border-accent/40 bg-white px-4 py-6 text-center">
          <p className="text-[14px] font-medium text-foreground">Admin token required for live receipts</p>
          <p className="mt-1 text-[13px] text-[var(--dim)]">
            {hasAdminToken()
              ? "Token was rejected — re-authorize on Connect."
              : "Paste LOOP_ADMIN_TOKEN on Connect to load proof and live-work cards."}
          </p>
          <Link
            href="/connect"
            className="mt-3 inline-flex items-center gap-1 text-[13px] font-medium text-accent hover:underline"
          >
            Authorize on Connect
            <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      ) : null,
    [needsAuth]
  );

  return (
    <section className={cn("flex flex-col gap-4", className)} id="glass-box">
      <div className="flex items-end justify-between gap-2">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight">Tools in focus</h2>
          <p className="mt-0.5 text-[12px] text-[var(--faint)]">Live receipts — stay on campus</p>
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium",
            live ? "bg-ok/10 text-ok" : "bg-[var(--elev)] text-[var(--faint)]"
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", live ? "bg-ok" : "bg-[var(--faint)]")} />
          {live ? "Live" : connection === "connecting" ? "Connecting" : "Offline"}
        </span>
      </div>

      {authHint}

      {featured ? <FeaturedCard card={featured} /> : null}

      {proofs.length > 0 ? <ProofGrid cards={proofs} compact className="grid-cols-1 sm:grid-cols-2" /> : null}

      {skips.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {skips.map((s, i) => (
            <SkipChip key={`${s}-${i}`} detail={s} />
          ))}
        </div>
      ) : null}

      {empty ? (
        <div className="rounded-2xl border border-dashed border-border bg-[#eef2ee]/50 px-4 py-8 text-center">
          <p className="text-[14px] font-medium text-foreground">No tool receipts yet</p>
          <p className="mt-1 text-[13px] text-[var(--dim)]">
            When agents query warehouse, open PRs, or draft mail, the live card appears here.
          </p>
          <Link
            href="/connect"
            className="mt-3 inline-flex items-center gap-1 text-[13px] font-medium text-accent hover:underline"
          >
            Connect Product Y
            <ExternalLink className="h-3 w-3" />
          </Link>
        </div>
      ) : null}
    </section>
  );
}

/** Compact live-work strip — only when receipts exist. */
export function HomeLiveReceipts({ className }: { className?: string }) {
  const { tick } = useGlobalWs();
  const worldTick = useDebouncedWorldTick(tick);
  const [count, setCount] = useState(0);

  useEffect(() => {
    api
      .liveWork()
      .then((r) => setCount(r.cards?.length ?? 0))
      .catch(() => setCount(0));
  }, [worldTick]);

  if (!count) return null;

  return <LiveWorkBoard className={className} />;
}
