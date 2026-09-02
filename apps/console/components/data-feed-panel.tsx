"use client";

import { useEffect, useState } from "react";
import type { OfficeDesk } from "@/lib/api";
import { api } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { cn } from "@/lib/utils";
import { ProofEmbed, type ProofPayload } from "@/components/proof-embed";
import { MIcon } from "@/components/ref/icon";

function shortAgent(id: string) {
  return id.replace(/_agent$/, "").replace(/_/g, " ");
}

/** Transparent data plane — embedded tool surfaces, not a text inbox. */
export function DataFeedPanel({ className, desks = [] }: { className?: string; desks?: OfficeDesk[] }) {
  const { tick } = useGlobalWs();
  const [cards, setCards] = useState<ProofPayload[]>([]);

  useEffect(() => {
    api
      .proofResources()
      .then((r) => setCards((r.cards || []).filter((c): c is ProofPayload => Boolean(c && (c as ProofPayload).kind))))
      .catch(() => setCards([]));
  }, [tick]);

  const activeDesk = desks.find((d) => d.status !== "idle");

  return (
    <section className={cn("scroll-mt-6", className)}>
      <h2 className="flex items-center gap-2 text-[20px] font-semibold tracking-tight">
        <MIcon name="cloud_sync" className="text-accent" />
        Data plane
      </h2>
      <p className="mt-1 text-[13px] text-[var(--dim)]">Live connector surfaces — same GA4, BQ, and GitHub agents query.</p>
      {activeDesk?.doing ? (
        <p className="mt-2 rounded-lg border border-accent/20 bg-accent/[0.04] px-3 py-2 text-[12px] text-[var(--dim)]">
          <span className="font-medium text-accent">{shortAgent(activeDesk.id)}</span> · {activeDesk.doing}
        </p>
      ) : null}
      <div className="mt-4 space-y-3">
        {cards.length > 0 ? (
          cards.slice(0, 4).map((p, i) => <ProofEmbed key={`${p.kind}-${i}`} proof={p} compact className="mt-0" />)
        ) : (
          <p className="text-[13px] text-[var(--faint)]">Connect tenant warehouse on Connect to see live tables here.</p>
        )}
      </div>
    </section>
  );
}
