"use client";

import Link from "next/link";
import { useState } from "react";
import { usePipelineHighlight } from "@/lib/pipeline-highlight";
import { cn } from "@/lib/utils";

const STAGE_FOCUS: Record<string, string> = {
  signal: "cove",
  investigate: "agents",
  evidence: "engine",
  root_cause: "engine",
  code: "github",
  product: "engine",
  risk: "gateway",
  approve: "operator",
  verify: "bq",
  learn: "engine",
};

const WORKFLOW_FOCUS: Record<string, string> = {
  signal: "alert",
  investigate: "triage",
  evidence: "contain",
  root_cause: "declare",
  code: "recover",
  product: "recover",
  experiment: "recover",
  risk: "verify",
  approve: "update",
  verify: "verify",
  learn: "close",
};

export type ArchifyDiagram = {
  id: string;
  label: string;
  src: string;
  title: string;
  focusMap?: Record<string, string>;
};

export const DEFAULT_DIAGRAMS: ArchifyDiagram[] = [
  {
    id: "system",
    label: "System",
    src: "/architecture/product-os.architecture.html",
    title: "Product OS topology",
    focusMap: STAGE_FOCUS,
  },
  {
    id: "investigation",
    label: "Investigation",
    src: "/architecture/product-os.investigation.html",
    title: "Investigation workflow",
    focusMap: WORKFLOW_FOCUS,
  },
];

/** Real Archify interactive viewer — search /, route probe R, guided stories P. */
export function ArchifyEmbed({
  diagrams = DEFAULT_DIAGRAMS,
  className,
  compact,
  hero,
  hideHeader,
  eager,
  defaultDiagram = "system",
}: {
  diagrams?: ArchifyDiagram[];
  className?: string;
  compact?: boolean;
  hero?: boolean;
  hideHeader?: boolean;
  eager?: boolean;
  defaultDiagram?: string;
}) {
  const stage = usePipelineHighlight();
  const [picked, setPicked] = useState(defaultDiagram);
  const active = diagrams.find((d) => d.id === picked) ?? diagrams[0];
  const focusMap = active?.focusMap ?? STAGE_FOCUS;
  const focus = stage ? focusMap[stage] : null;
  const hash = focus ? `#focus=${focus}` : "";
  const uri = `${active.src}?theme=light${hash}`;

  return (
    <section id="architecture" className={cn("scroll-mt-6", className)}>
      {hideHeader ? null : (
        <>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-[20px] font-semibold tracking-tight sm:text-[22px]">
                {active.title}
              </h2>
            </div>
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              {diagrams.length > 1 ? (
                <div className="flex rounded-full border border-border bg-[var(--elev)] p-0.5 text-[12px]">
                  {diagrams.map((d) => (
                    <button
                      key={d.id}
                      type="button"
                      onClick={() => setPicked(d.id)}
                      className={cn(
                        "rounded-full px-3 py-1 font-medium transition-colors",
                        picked === d.id ? "bg-white text-foreground shadow-sm" : "text-[var(--dim)] hover:text-foreground"
                      )}
                    >
                      {d.label}
                    </button>
                  ))}
                </div>
              ) : null}
              {stage ? (
                <span className="rounded-full bg-accent/10 px-2.5 py-1 text-[12px] font-medium text-accent">
                  {stage.replace(/_/g, " ")}
                </span>
              ) : null}
              <a href={uri} target="_blank" rel="noreferrer" className="text-[13px] font-medium text-accent">
                Full screen
              </a>
              <Link href="/labs/architecture" className="text-[13px] text-[var(--faint)] hover:text-foreground">
                Architecture
              </Link>
            </div>
          </div>
        </>
      )}
      <div
        className={cn(
          "surface-lg overflow-hidden ring-1 ring-black/[0.04]",
          hideHeader ? "mt-0" : "mt-4",
          hero ? "h-[min(72vh,680px)]" : compact ? "h-[min(52vh,420px)]" : "h-[min(62vh,560px)]"
        )}
      >
        <iframe
          key={`${active.id}-${uri}`}
          src={uri}
          title={active.title}
          className="h-full w-full border-0 bg-white"
          loading={hero || eager ? "eager" : "lazy"}
        />
      </div>
    </section>
  );
}
