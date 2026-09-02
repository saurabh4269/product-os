"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type OfficeDesk } from "@/lib/api";
import { mergeProofCatalog } from "@/lib/collect-proofs";
import { agentHref, shortName } from "@/lib/names";
import { useGlobalWs } from "@/lib/use-global-ws";
import { cn } from "@/lib/utils";
import { AgentBadge } from "@/components/agent-badge";
import { ProofEmbed, type ProofPayload } from "@/components/proof-embed";
import { MIcon } from "./icon";

const FILTERS: Array<{ id: string; label: string; kinds: string[] | null }> = [
  { id: "all", label: "All", kinds: null },
  { id: "analytics", label: "Analytics", kinds: ["ga4", "ads"] },
  { id: "warehouse", label: "Warehouse", kinds: ["warehouse", "bq"] },
  { id: "engineering", label: "Engineering", kinds: ["github", "deploys", "logs"] },
  { id: "gateway", label: "Gateway", kinds: ["gateway", "gmail", "calendar", "meet", "slack", "workspace"] },
];

function isLive(proof: ProofPayload) {
  return Boolean(proof.live || (proof.rows && proof.rows.length > 0) || proof.console_url || proof.url);
}

function proofScore(proof: ProofPayload) {
  let score = 0;
  if (proof.live) score += 4;
  if (proof.rows?.length) score += proof.rows.length;
  if (proof.console_url || proof.url) score += 2;
  if (proof.sql) score += 1;
  return score;
}

function pickSpotlight(cards: ProofPayload[]) {
  const candidates = cards.filter((c) => isLive(c) && ["ga4", "warehouse", "bq", "github"].includes(String(c.kind)));
  if (!candidates.length) return null;
  return [...candidates].sort((a, b) => proofScore(b) - proofScore(a))[0];
}

function cardKey(proof: ProofPayload, index: number) {
  return `${proof.kind}-${proof.title}-${proof.url || proof.console_url || index}`;
}

/** Nerve center — one catalog of connector surfaces, no duplicate chrome around ProofEmbed. */
export function DataPlaneHub() {
  const { tick } = useGlobalWs();
  const [cards, setCards] = useState<ProofPayload[]>([]);
  const [desks, setDesks] = useState<OfficeDesk[]>([]);
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.status>> | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    Promise.all([api.proof(), api.proofResources(), api.office(), api.status()])
      .then(([pf, res, office, st]) => {
        setCards(mergeProofCatalog(pf, (res.cards || []) as ProofPayload[]));
        setDesks(office.desks);
        setStatus(st);
      })
      .catch(() => undefined);
  }, [tick]);

  const activeDesks = useMemo(() => desks.filter((d) => d.status !== "idle"), [desks]);
  const liveCount = useMemo(() => cards.filter(isLive).length, [cards]);
  const spotlight = useMemo(() => pickSpotlight(cards), [cards]);

  const catalog = useMemo(() => {
    const q = query.trim().toLowerCase();
    const activeFilter = FILTERS.find((f) => f.id === filter);

    return cards.filter((card) => {
      if (spotlight && card === spotlight) return false;
      if (activeFilter?.kinds && !activeFilter.kinds.includes(String(card.kind || ""))) return false;
      if (!q) return true;
      return [card.kind, card.title, card.subtitle, card.detail, card.source, card.repo, card.table]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [cards, filter, query, spotlight]);

  const filterCounts = useMemo(() => {
    const counts: Record<string, number> = { all: cards.length };
    for (const f of FILTERS) {
      if (!f.kinds) continue;
      counts[f.id] = cards.filter((c) => f.kinds?.includes(String(c.kind || ""))).length;
    }
    return counts;
  }, [cards]);

  return (
    <div className="mx-auto max-w-container-max space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-display-lg font-bold tracking-tight text-text-primary">Data plane</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-body-sm text-text-secondary">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-accent-success/10 px-2.5 py-1 text-accent-success">
              <span className="h-1.5 w-1.5 rounded-full bg-accent-success" />
              {liveCount} live
            </span>
            <span className="rounded-full bg-surface-subtle px-2.5 py-1">{cards.length} connectors</span>
            <span className="rounded-full bg-surface-subtle px-2.5 py-1">{activeDesks.length} agents querying</span>
            {!status?.workspace?.connected ? (
              <Link href="/settings" className="rounded-full bg-primary/10 px-2.5 py-1 text-primary hover:underline">
                Workspace not wired
              </Link>
            ) : null}
          </div>
        </div>
        <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row sm:items-center">
          <div className="relative min-w-[220px] flex-1 sm:w-64">
            <MIcon name="search" className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search connectors…"
              className="w-full rounded-full border-none bg-surface-subtle py-2 pl-10 pr-4 text-body-sm outline-none focus:bg-white focus:ring-2 focus:ring-primary/20"
            />
          </div>
          <Link
            href="/settings"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-label-lg text-on-primary shadow-sm hover:bg-primary/90"
          >
            <MIcon name="add_link" className="text-[18px]" />
            Wire in Settings
          </Link>
        </div>
      </header>

      {cards.length === 0 ? (
        <div className="po-card rounded-2xl p-12 text-center">
          <MIcon name="database" className="mx-auto text-[40px] text-outline" />
          <p className="mt-4 text-body-md text-text-secondary">
            <Link href="/settings" className="text-primary hover:underline">
              Settings
            </Link>
          </p>
        </div>
      ) : (
        <>
          {spotlight ? (
            <section className="po-card overflow-hidden rounded-2xl border border-primary/15">
              <div className="border-b border-surface-subtle/60 bg-primary/[0.03] px-4 py-2.5">
                <p className="text-label-caps uppercase tracking-wider text-primary">Primary surface</p>
              </div>
              <ProofEmbed proof={spotlight} className="mt-0 rounded-none border-0 shadow-none" />
            </section>
          ) : null}

          <div className="flex flex-wrap gap-2">
            {FILTERS.map((f) => {
              const count = filterCounts[f.id] ?? 0;
              if (f.id !== "all" && count === 0) return null;
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => setFilter(f.id)}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-label-lg transition-colors",
                    filter === f.id
                      ? "bg-primary text-on-primary"
                      : "bg-surface-subtle text-text-secondary hover:bg-surface-container-high"
                  )}
                >
                  {f.label}
                  <span className="ml-1 opacity-70">{count}</span>
                </button>
              );
            })}
          </div>

          {catalog.length > 0 ? (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {catalog.map((proof, i) => (
                <ProofEmbed key={cardKey(proof, i)} proof={proof} className="mt-0" />
              ))}
            </div>
          ) : (
            <p className="py-8 text-center text-body-md text-text-secondary">No connectors match this filter.</p>
          )}
        </>
      )}

      {activeDesks.length > 0 ? (
        <section className="po-card rounded-2xl p-5">
          <div className="mb-4 flex items-center justify-between gap-2">
            <h2 className="flex items-center gap-2 text-headline-sm text-text-primary">
              <MIcon name="smart_toy" className="text-primary" />
              Agents on the wire
            </h2>
            <Link href="/registry" className="text-label-lg text-primary hover:underline">
              Agent registry
            </Link>
          </div>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {activeDesks.slice(0, 6).map((desk) => (
              <Link
                key={desk.id}
                href={desk.room_id ? `/rooms/${desk.room_id}` : agentHref(desk.id)}
                className="flex items-start gap-3 rounded-xl border border-transparent p-3 transition-colors hover:border-surface-subtle hover:bg-surface-base"
              >
                <AgentBadge
                  name={desk.id}
                  status={desk.status === "handing_off" ? "handing_off" : "working"}
                  size={36}
                  variant="face"
                />
                <div className="min-w-0">
                  <p className="text-label-lg text-text-primary">{shortName(desk.id)}</p>
                  <p className="line-clamp-2 text-body-sm text-text-secondary">{desk.doing}</p>
                </div>
              </Link>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
