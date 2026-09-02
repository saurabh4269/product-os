"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { ExternalLink, GitPullRequest, Mail, Phone } from "lucide-react";
import { api } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { AgentBadge } from "@/components/agent-badge";
import { ProofEmbed, type ProofPayload } from "@/components/proof-embed";
import { cn } from "@/lib/utils";

export type LiveWorkCard = {
  id: string;
  column: string;
  badge: string;
  text: string;
  agent: string;
  room_id: string;
  room_title?: string;
  tenant_product?: string | null;
  artifact_type?: string | null;
  phone?: string | null;
  metric?: string | null;
  source?: string | null;
  created_at?: string;
  pr_url?: string | null;
  gmail_url?: string | null;
  calendar_url?: string | null;
  meet_url?: string | null;
  bq_url?: string | null;
  action_id?: string;
  proof?: ProofPayload | null;
};

type Column = { id: string; label: string; count: number };

const BADGE_TONE: Record<string, string> = {
  Found: "bg-sky-50 text-sky-800",
  Voice: "bg-violet-50 text-violet-800",
  Contact: "bg-violet-50 text-violet-800",
  Queried: "bg-emerald-50 text-emerald-800",
  Packed: "bg-emerald-50 text-emerald-800",
  BigQuery: "bg-amber-50 text-amber-900",
  Claim: "bg-emerald-50 text-emerald-800",
  Lookup: "bg-violet-50 text-violet-800",
  Patch: "bg-sky-50 text-sky-900",
  Brief: "bg-sky-50 text-sky-900",
  "PR open": "bg-ok/10 text-ok",
  Proposal: "bg-sky-50 text-sky-900",
  Experiment: "bg-sky-50 text-sky-900",
  Risk: "bg-orange-50 text-orange-900",
  Waiting: "bg-accent/10 text-accent",
  Notify: "bg-orange-50 text-orange-900",
  Calling: "bg-fuchsia-50 text-fuchsia-900",
  Feedback: "bg-fuchsia-50 text-fuchsia-900",
  Call: "bg-fuchsia-50 text-fuchsia-900",
  "Mail sent": "bg-ok/10 text-ok",
  Draft: "bg-[var(--elev)] text-[var(--dim)]",
  Mail: "bg-ok/10 text-ok",
  Verified: "bg-ok/10 text-ok",
  Lesson: "bg-ok/10 text-ok",
};

function agentLabel(id: string) {
  return id.replace(/_agent$/, "").replace(/_/g, " ");
}

function WorkCard({
  card,
  fresh,
}: {
  card: LiveWorkCard;
  fresh?: boolean;
}) {
  const deep =
    card.pr_url || card.gmail_url || card.calendar_url || card.meet_url || card.bq_url || null;
  return (
    <article
      className={cn(
        "group overflow-hidden rounded-2xl border border-border bg-white shadow-[0_1px_2px_rgba(29,29,31,0.04)] transition duration-300",
        fresh && "ring-2 ring-accent/20 transition duration-500",
        card.badge === "Waiting" && "border-accent/40 ring-1 ring-accent/15",
        card.badge === "PR open" && "border-ok/35",
        card.badge === "Mail sent" && "border-ok/30"
      )}
    >
      <Link href={`/rooms/${card.room_id}`} className="block px-3.5 py-3">
        <div className="flex items-start gap-2.5">
          <AgentBadge name={card.agent || "orchestrator"} size={26} variant="face" />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                  BADGE_TONE[card.badge] || "bg-[var(--elev)] text-[var(--faint)]"
                )}
              >
                {card.badge}
              </span>
              {card.tenant_product ? (
                <span className="text-[10px] text-[var(--faint)]">{card.tenant_product}</span>
              ) : null}
            </div>
            <p className="mt-1.5 text-[13px] font-medium leading-5 text-foreground line-clamp-3">
              {card.text}
            </p>
            {card.phone ? (
              <p className="mt-1.5 flex items-center gap-1 font-mono text-[12px] tabular-nums text-[var(--dim)]">
                <Phone className="h-3 w-3 shrink-0 opacity-60" />
                {card.phone}
              </p>
            ) : null}
            {card.room_title ? (
              <p className="mt-1 text-[11px] text-[var(--faint)] line-clamp-1">{card.room_title}</p>
            ) : null}
          </div>
        </div>
      </Link>
      {(deep || card.pr_url || card.gmail_url) && (
        <div className="flex flex-wrap gap-1.5 border-t border-border/70 bg-[var(--elev)]/50 px-3 py-1.5">
          {card.pr_url ? (
            <a
              href={card.pr_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-ok hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              <GitPullRequest className="h-3 w-3" />
              PR
            </a>
          ) : null}
          {card.gmail_url ? (
            <a
              href={card.gmail_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-[var(--dim)] hover:text-accent"
              onClick={(e) => e.stopPropagation()}
            >
              <Mail className="h-3 w-3" />
              Mail
            </a>
          ) : null}
          {card.calendar_url || card.meet_url ? (
            <a
              href={card.meet_url || card.calendar_url || "#"}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-[var(--dim)] hover:text-accent"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink className="h-3 w-3" />
              Calendar
            </a>
          ) : null}
          {card.bq_url ? (
            <a
              href={card.bq_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-amber-800 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              BQ
            </a>
          ) : null}
        </div>
      )}
      {card.proof ? (
        <div className="border-t border-border/60 px-2.5 py-2" onClick={(e) => e.preventDefault()}>
          <ProofEmbed proof={card.proof} compact className="mt-0" />
        </div>
      ) : null}
      <p className="border-t border-border/50 px-3.5 py-1.5 text-[10px] text-[var(--faint)]">
        <span className="font-medium text-[var(--dim)]">{agentLabel(card.agent)}</span>
        {" · open room"}
      </p>
    </article>
  );
}

export function LiveWorkBoard({
  subtitle,
  className,
}: {
  subtitle?: string;
  className?: string;
}) {
  const { tick, connection } = useGlobalWs();
  const [columns, setColumns] = useState<Column[]>([]);
  const [cards, setCards] = useState<LiveWorkCard[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [loaded, setLoaded] = useState(false);
  const [freshIds, setFreshIds] = useState<Set<string>>(new Set());
  const seen = useRef<Set<string>>(new Set());

  useEffect(() => {
    api
      .liveWork()
      .then((r) => {
        const next = r.cards || [];
        const newcomers = next.filter((c) => seen.current.size && !seen.current.has(c.id)).map((c) => c.id);
        for (const c of next) seen.current.add(c.id);
        if (newcomers.length) {
          setFreshIds(new Set(newcomers));
          window.setTimeout(() => setFreshIds(new Set()), 1200);
        }
        setColumns(r.columns || []);
        setCards(next);
        setStats(r.stats || {});
        setLoaded(true);
      })
      .catch(() => {
        setColumns([]);
        setCards([]);
        setLoaded(true);
      });
  }, [tick]);

  const byCol = useMemo(() => {
    const map: Record<string, LiveWorkCard[]> = {};
    for (const col of columns) map[col.id] = [];
    for (const c of cards) {
      if (!map[c.column]) map[c.column] = [];
      map[c.column].push(c);
    }
    return map;
  }, [cards, columns]);

  const live = connection === "live";
  const connectionLabel =
    live ? "Live" : connection === "connecting" ? "Connecting" : connection === "reconnecting" ? "Reconnecting" : "Offline";

  return (
    <div id="live-work" className={cn(className)}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-[18px] font-semibold tracking-tight">Live work</h2>
            <span
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium",
                live ? "bg-ok/10 text-ok" : "bg-[var(--elev)] text-[var(--faint)]"
              )}
            >
              <span className={cn("h-1.5 w-1.5 rounded-full", live ? "bg-ok animate-pulse" : "bg-[var(--faint)]")} />
              {connectionLabel}
            </span>
          </div>
          {subtitle ? (
            <p className="mt-0.5 text-[13px] text-[var(--dim)]">{subtitle}</p>
          ) : null}
        </div>
        {loaded && cards.length > 0 ? (
          <p className="text-[12px] text-[var(--faint)]">{stats.total ?? cards.length} receipts</p>
        ) : null}
      </div>

      {loaded && cards.length > 0 ? (
        <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {[
            { label: "Evidence", value: stats.evidence ?? 0 },
            { label: "Code / PRs", value: stats.code ?? 0, hot: (stats.with_pr ?? 0) > 0 },
            { label: "Awaiting you", value: stats.approve ?? 0, hot: (stats.approve ?? 0) > 0 },
            { label: "Verified / mail", value: stats.verify ?? 0 },
          ].map((k) => (
            <div
              key={k.label}
              className={cn(
                "rounded-2xl border px-3.5 py-2.5",
                k.hot ? "border-accent/35 bg-accent/[0.04]" : "border-border bg-white"
              )}
            >
              <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--faint)]">{k.label}</p>
              <p className="mt-0.5 text-[22px] font-semibold tabular-nums tracking-tight text-foreground">
                {k.value}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      {loaded && cards.length === 0 ? (
        <div className="mt-4 rounded-2xl border border-dashed border-border bg-[#eef2ee]/60 px-5 py-10 text-center">
          <p className="text-[15px] font-medium text-foreground">No live receipts yet</p>
        </div>
      ) : null}

      {loaded && cards.length > 0 ? (
        <div className="mt-4 flex gap-3 overflow-x-auto pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {(columns.length
            ? columns
            : ["signal", "evidence", "code", "approve", "verify"].map((id) => ({
                id,
                label: id,
                count: 0,
              }))
          ).map((col) => {
            const list = byCol[col.id] || [];
            const shown = list.slice(0, 8);
            const more = list.length - shown.length;
            const hot = list.some((c) => freshIds.has(c.id) || c.badge === "Waiting");
            return (
              <div
                key={col.id}
                id={`live-col-${col.id}`}
                className={cn(
                  "flex w-[min(16.5rem,78vw)] shrink-0 flex-col rounded-[1.25rem] p-2.5 transition-colors duration-300",
                  hot ? "bg-[color-mix(in_srgb,var(--accent)_10%,#eef2ee)]" : "bg-[#eef2ee]"
                )}
              >
                <div className="flex items-center justify-between gap-2 px-2 py-1.5">
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        list.length ? "bg-accent" : "bg-[var(--faint)]/40"
                      )}
                    />
                    <p className="text-[12px] font-semibold tracking-tight text-foreground">{col.label}</p>
                  </div>
                  <span className="text-[11px] tabular-nums text-[var(--faint)]">{list.length}</span>
                </div>
                <div className="mt-1 flex min-h-[6rem] flex-col gap-2.5">
                  {shown.map((c) => (
                    <WorkCard key={c.id} card={c} fresh={freshIds.has(c.id)} />
                  ))}
                  {more > 0 ? (
                    <p className="px-2 text-[11px] text-[var(--faint)]">+{more} more in rooms</p>
                  ) : null}
                  {list.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-black/5 bg-white/40 px-3 py-6 text-center text-[11px] text-[var(--faint)]">
                      Waiting
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
