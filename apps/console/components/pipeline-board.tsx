"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";

const LABELS: Record<string, string> = {
  signal: "Signal",
  investigate: "Investigate",
  evidence: "Evidence",
  root_cause: "Root cause",
  code: "Code",
  product: "Product",
  experiment: "Experiment",
  risk: "Risk",
  approve: "Approve",
  verify: "Verify",
  learn: "Learn",
};

type Card = {
  room_id: string;
  title: string;
  stage: string;
  kind: string;
  tenant_product?: string | null;
  awaiting_approval?: boolean;
  pr_url?: string | null;
};

export function PipelineBoard() {
  const { tick } = useGlobalWs();
  const [columns, setColumns] = useState<string[]>([]);
  const [cards, setCards] = useState<Card[]>([]);
  const [loaded, setLoaded] = useState(false);
  const prevStages = useRef<Record<string, string>>({});

  useEffect(() => {
    api
      .pipeline()
      .then((r) => {
        setColumns(r.columns);
        setCards(r.cards);
        setLoaded(true);
      })
      .catch(() => {
        setColumns([]);
        setCards([]);
        setLoaded(true);
      });
  }, [tick]);

  useEffect(() => {
    if (!loaded) return;
    const t = window.setTimeout(() => {
      const map: Record<string, string> = {};
      for (const c of cards) map[c.room_id] = c.stage;
      prevStages.current = map;
    }, 520);
    return () => window.clearTimeout(t);
  }, [cards, loaded]);

  const cols = columns.length ? columns : ["signal", "investigate", "evidence", "approve", "verify", "learn"];

  return (
    <div className="mt-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <p className="text-[13px] text-[var(--faint)]">Pipeline</p>
          <h2 className="mt-1 text-[20px] font-semibold tracking-tight">Work in flight</h2>
        </div>
        <p className="text-[12px] text-[var(--dim)]">
          {cards.length ? `${cards.length} open` : loaded ? "Run demo to add a card" : "…"}
        </p>
      </div>
      <div className="mt-4 flex gap-3 overflow-x-auto pb-2">
        {cols.map((col) => {
          const inCol = cards.filter((c) => c.stage === col);
          return (
            <div key={col} className="min-w-[9.5rem] shrink-0 rounded-2xl bg-[#eef2ee] p-2">
              <p className="px-2 py-1 text-[11px] font-medium text-[var(--faint)]">
                {LABELS[col] || col}
                {inCol.length ? ` · ${inCol.length}` : ""}
              </p>
              <div className="mt-1 min-h-[4rem] space-y-2">
                {inCol.map((c) => {
                  const moved = prevStages.current[c.room_id] && prevStages.current[c.room_id] !== c.stage;
                  return (
                    <Link
                      key={c.room_id}
                      href={`/rooms/${c.room_id}`}
                      className={
                        "block rounded-xl border bg-white px-3 py-2 shadow-sm transition-all duration-500 hover:border-accent/40 " +
                        (c.awaiting_approval
                          ? "border-accent/50 ring-2 ring-accent/20"
                          : "border-border") +
                        (moved ? " scale-[1.02]" : "")
                      }
                    >
                      <p className="text-[13px] font-medium leading-5 text-foreground line-clamp-2">{c.title}</p>
                      {c.tenant_product ? (
                        <p className="mt-1 text-[11px] text-[var(--faint)]">{c.tenant_product}</p>
                      ) : null}
                      {c.awaiting_approval ? (
                        <p className="mt-1 text-[11px] font-medium text-accent">Needs your approval →</p>
                      ) : null}
                      {c.pr_url ? (
                        <a
                          href={c.pr_url}
                          className="mt-1 block text-[11px] text-accent hover:underline"
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                        >
                          PR opened
                        </a>
                      ) : null}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
