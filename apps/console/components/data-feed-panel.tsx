"use client";

import { useEffect, useMemo, useState } from "react";
import type { OfficeDesk } from "@/lib/api";
import { api } from "@/lib/api";
import { useGlobalWs, type ActivityEvent } from "@/lib/use-global-ws";
import { cn } from "@/lib/utils";
import { Database, Radio, Webhook, BarChart3, Shield } from "lucide-react";

type FeedItem = {
  id: string;
  kind: "ingest" | "warehouse" | "signal" | "gateway" | "other";
  label: string;
  detail: string;
  ts?: string;
  hot?: boolean;
};

const KIND_ICON = {
  ingest: Webhook,
  warehouse: Database,
  signal: Radio,
  gateway: Shield,
  other: BarChart3,
};

function classify(e: ActivityEvent): FeedItem | null {
  const msg = (e.message || "").toLowerCase();
  const agent = e.agent_id || "system";
  const ts = e.ts;
  const text = e.message || "";

  if (/bigquery|bq|warehouse|ga4|analytics|metrics|loop_raw|ads/.test(msg)) {
    return {
      id: `${ts}-wh-${agent}`,
      kind: "warehouse",
      label: "BigQuery",
      detail: text.slice(0, 72),
      ts,
      hot: true,
    };
  }
  if (/ingest|webhook|tenant|signal posted|cove|api\/t\//.test(msg)) {
    return {
      id: `${ts}-in-${agent}`,
      kind: "ingest",
      label: "Ingest",
      detail: text.slice(0, 72),
      ts,
      hot: true,
    };
  }
  if (/signal|anomaly|detect|metric/.test(msg) && agent.includes("signal")) {
    return {
      id: `${ts}-sig-${agent}`,
      kind: "signal",
      label: "Signal",
      detail: text.slice(0, 72),
      ts,
    };
  }
  if (/deny|gateway|exfil|armor|blocked/.test(msg)) {
    return {
      id: `${ts}-gw-${agent}`,
      kind: "gateway",
      label: "Gateway",
      detail: text.slice(0, 72),
      ts,
      hot: true,
    };
  }
  if (/evidence|query|read|fetch|pull/.test(msg)) {
    return {
      id: `${ts}-ot-${agent}`,
      kind: "warehouse",
      label: shortAgent(agent),
      detail: text.slice(0, 72),
      ts,
    };
  }
  return null;
}

function shortAgent(id: string) {
  return id.replace(/_agent$/, "").replace(/_/g, " ");
}

/** Transparent data plane — what's being fetched, not a black box. */
export function DataFeedPanel({ className, desks = [] }: { className?: string; desks?: OfficeDesk[] }) {
  const { activity: live, tick } = useGlobalWs();
  const [seed, setSeed] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    api
      .activity()
      .then((r) => setSeed(r.events))
      .catch(() => setSeed([]));
  }, [tick]);

  const items = useMemo(() => {
    const seen = new Set<string>();
    const out: FeedItem[] = [];
    for (const e of [...live, ...seed]) {
      const item = classify(e);
      if (!item || seen.has(item.id)) continue;
      seen.add(item.id);
      out.push(item);
      if (out.length >= 6) break;
    }
    for (const desk of desks) {
      if (desk.status === "idle" || out.length >= 6) continue;
      const doing = desk.doing || "";
      const lower = doing.toLowerCase();
      let kind: FeedItem["kind"] = "other";
      if (/bigquery|bq|warehouse|ga4|analytics|metric|conversion/.test(lower)) kind = "warehouse";
      else if (/log|error|timeout|stack/.test(lower)) kind = "warehouse";
      else if (/deploy|release|version/.test(lower)) kind = "warehouse";
      else if (/ingest|signal|demo|checkout/.test(lower)) kind = "ingest";
      const id = `desk-${desk.id}`;
      if (seen.has(id)) continue;
      seen.add(id);
      out.push({
        id,
        kind,
        label: shortAgent(desk.id),
        detail: doing.slice(0, 72),
        hot: true,
      });
    }
    return out;
  }, [live, seed, desks]);

  const defaults: FeedItem[] = [
    { id: "default-bq", kind: "warehouse", label: "BigQuery", detail: "GA4, Ads, loop_raw" },
    { id: "default-ingest", kind: "ingest", label: "Ingest", detail: "Signals from Product Y" },
    { id: "default-gw", kind: "gateway", label: "Gateway", detail: "Exfil blocked by default" },
  ];

  const show = items.length > 0 ? items : defaults;

  return (
    <section className={cn("scroll-mt-6", className)}>
      <h2 className="text-[20px] font-semibold tracking-tight">Data</h2>
      <ul className="mt-4 space-y-2">
        {show.map((item) => {
          const Icon = KIND_ICON[item.kind];
          return (
            <li
              key={item.id}
              className={cn(
                "flex items-start gap-3 rounded-xl border px-3 py-2.5",
                item.hot ? "border-accent/25 bg-accent/[0.04]" : "border-border bg-white"
              )}
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0 text-accent" strokeWidth={1.75} />
              <span className="min-w-0 flex-1">
                <span className="block text-[13px] font-medium">{item.label}</span>
                <span className="mt-0.5 block text-[12px] leading-5 text-[var(--dim)]">{item.detail}</span>
              </span>
              {item.hot ? (
                <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-accent animate-pulse" aria-label="Live" />
              ) : null}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
