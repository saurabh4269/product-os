"use client";

import { ProofGrid, type ProofPayload } from "@/components/proof-embed";
import { MIcon } from "./icon";

/**
 * Reference: investigation lab "tools" column + nerve center integrations —
 * live connector cards, not an activity inbox.
 */
export function ToolSurfaceRail({
  title = "Live sources",
  subtitle,
  cards,
  className,
}: {
  title?: string;
  subtitle?: string;
  cards: ProofPayload[];
  className?: string;
}) {
  return (
    <div className={className}>
      <div className="mb-stack-sm">
        <h3 className="flex items-center gap-2 text-headline-sm text-on-surface">
          <MIcon name="cloud_sync" className="text-secondary" />
          {title}
          <span className="h-2 w-2 animate-pulse rounded-full bg-accent-success" />
        </h3>
        {subtitle ? <p className="mt-1 text-body-sm text-on-surface-variant">{subtitle}</p> : null}
      </div>
      <div className="po-card po-ambient-shadow rounded-xl bg-[#FAFAFA] p-stack-md">
        {cards.length > 0 ? (
          <ProofGrid cards={cards} className="grid-cols-1 gap-3" compact />
        ) : (
          <div className="space-y-3 py-4 text-center">
            <MIcon name="database" className="text-[32px] text-outline-variant" />
          </div>
        )}
      </div>
    </div>
  );
}
