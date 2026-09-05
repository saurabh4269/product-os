"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { type GeapStatusPayload } from "@/lib/api";
import {
  geapDisplayName,
  geapEngineShortId,
  geapMemoryBankUri,
  geapMemoryOperational,
  geapOperational,
  geapRoutingLine,
  geapVertexConsoleUrl,
} from "@/lib/geap-display";
import { fetchWorldGeap } from "@/lib/world-data";
import { useGlobalWs } from "@/lib/use-global-ws";
import { useSlowWorldTick, useWorldPollEnabled } from "@/lib/world-refresh";
import { cn } from "@/lib/utils";

function StatusDot({ live }: { live: boolean }) {
  return (
    <span
      className={cn("h-1.5 w-1.5 shrink-0 rounded-full", live ? "bg-ok" : "bg-[var(--faint)]")}
      aria-hidden
    />
  );
}

function EngineChip({
  payload,
  className,
}: {
  payload: GeapStatusPayload;
  className?: string;
}) {
  const short = geapEngineShortId(payload);
  const href = geapVertexConsoleUrl(payload);
  if (!short) return null;
  const inner = (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-border bg-[var(--elev)] px-2 py-0.5 font-mono text-[10px] text-[var(--dim)]",
        className
      )}
    >
      {short}
    </span>
  );
  if (!href) return inner;
  return (
    <a href={href} target="_blank" rel="noreferrer" className="hover:border-accent/40" title="Open in Vertex AI">
      {inner}
    </a>
  );
}

function MemoryChip({ payload, className }: { payload: GeapStatusPayload; className?: string }) {
  const uri = geapMemoryBankUri(payload);
  if (!uri) return null;
  return (
    <span
      className={cn(
        "inline-flex max-w-full items-center truncate rounded-full border border-dashed border-[var(--faint)]/40 bg-white px-2 py-0.5 font-mono text-[10px] text-[var(--faint)]",
        className
      )}
      title={uri}
    >
      {uri.length > 28 ? `${uri.slice(0, 26)}…` : uri}
    </span>
  );
}

/** Compact campus chip — fits status strip / command bar. */
export function GeapStatusChip({ className }: { className?: string }) {
  const { tick, connection } = useGlobalWs();
  const slowTick = useSlowWorldTick(tick, connection === "live");
  const pollEnabled = useWorldPollEnabled();
  const [payload, setPayload] = useState<GeapStatusPayload | null>(null);

  useEffect(() => {
    if (!pollEnabled) return;
    fetchWorldGeap()
      .then(setPayload)
      .catch(() => setPayload(null));
  }, [slowTick, pollEnabled]);

  if (!payload?.geap?.enabled) return null;

  const live = geapOperational(payload);
  const name = geapDisplayName(payload);

  return (
    <Link
      href="/labs/architecture?tab=deep"
      className={cn(
        "inline-flex max-w-[min(100%,18rem)] items-center gap-1.5 rounded-full border border-border bg-white px-2.5 py-1 text-[12px] transition hover:border-accent/30",
        live && "border-ok/30",
        className
      )}
      title={`Gemini Enterprise Agent Platform · ${geapRoutingLine(payload)}`}
    >
      <StatusDot live={live} />
      <span className="truncate font-medium text-foreground">GEAP</span>
      <span className="truncate text-[var(--faint)]">{name}</span>
      <EngineChip payload={payload} />
    </Link>
  );
}

/** Quiet glass card — home glass box, Connect, Architecture. */
export function GeapStatusCard({
  className,
  compact,
}: {
  className?: string;
  compact?: boolean;
}) {
  const { tick, connection } = useGlobalWs();
  const slowTick = useSlowWorldTick(tick, connection === "live");
  const pollEnabled = useWorldPollEnabled();
  const [payload, setPayload] = useState<GeapStatusPayload | null>(null);
  const [loaded, setLoaded] = useState(false);

  const load = useCallback(() => {
    fetchWorldGeap()
      .then((p) => {
        setPayload(p);
        setLoaded(true);
      })
      .catch(() => {
        setPayload(null);
        setLoaded(true);
      });
  }, []);

  useEffect(() => {
    if (!pollEnabled) return;
    load();
  }, [slowTick, load, pollEnabled]);

  if (!loaded) return null;
  if (!payload?.geap?.enabled) return null;

  const live = geapOperational(payload);
  const memoryLive = geapMemoryOperational(payload);
  const name = geapDisplayName(payload);
  const routing = geapRoutingLine(payload);

  if (compact) {
    return (
      <div
        className={cn(
          "rounded-xl border border-border/80 bg-white/90 px-3 py-2.5 text-[12px] text-[var(--dim)]",
          className
        )}
      >
        <div className="flex flex-wrap items-center gap-2">
          <StatusDot live={live} />
          <span className="font-medium text-foreground">Gemini Enterprise Agent Platform</span>
          <span className="text-[var(--faint)]">· {name}</span>
        </div>
        <div className="mt-1.5 flex flex-wrap gap-1.5">
          <EngineChip payload={payload} />
          <MemoryChip payload={payload} />
        </div>
        <p className="mt-1.5 text-[11px] text-[var(--faint)]">{routing}</p>
      </div>
    );
  }

  return (
    <section
      className={cn(
        "overflow-hidden rounded-2xl border border-border bg-white shadow-sm",
        className
      )}
    >
      <div className="border-b border-border/60 px-3.5 py-2.5">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <StatusDot live={live} />
              <h3 className="text-[13px] font-semibold tracking-tight text-foreground">
                Gemini Enterprise Agent Platform
              </h3>
            </div>
            <p className="mt-1 text-[12px] text-[var(--dim)]">
              Running on managed Agent Runtime · <span className="font-medium text-foreground">{name}</span>
            </p>
          </div>
          <span
            className={cn(
              "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
              live ? "bg-ok/10 text-ok" : "bg-[var(--elev)] text-[var(--faint)]"
            )}
          >
            {live ? "Live" : "Standby"}
          </span>
        </div>
      </div>
      <div className="space-y-2 px-3.5 py-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--faint)]">Engine</span>
          <EngineChip payload={payload} />
          {geapVertexConsoleUrl(payload) ? (
            <a
              href={geapVertexConsoleUrl(payload)!}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-0.5 text-[11px] text-accent hover:underline"
            >
              Vertex
              <ExternalLink className="h-3 w-3" />
            </a>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--faint)]">
            Memory Bank
          </span>
          <MemoryChip payload={payload} />
          <span
            className={cn(
              "rounded-full px-1.5 py-0.5 text-[10px] font-medium",
              memoryLive ? "bg-ok/10 text-ok" : "text-[var(--faint)]"
            )}
          >
            {memoryLive ? "operational" : "fallback"}
          </span>
        </div>
        <p className="text-[11px] leading-5 text-[var(--faint)]">
          <span className="font-medium text-[var(--dim)]">Routing</span> · {routing}
        </p>
        <p className="text-[11px] text-[var(--faint)]">
          Agent Gateway remains plan-only ·{" "}
          <Link href="/labs/architecture?tab=deep" className="text-accent hover:underline">
            Architecture
          </Link>
        </p>
      </div>
    </section>
  );
}
