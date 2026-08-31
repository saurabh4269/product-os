"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { LOOPS_STEPS, type LoopStep } from "@/lib/demo-guide-context";
import { setPipelineHighlight, usePipelineHighlight } from "@/lib/pipeline-highlight";

/** Tier A — seven-step product loop (always visible on homepage, like their process-steps). */
export function SevenStepLoop({
  activeStage,
  compact,
  className,
}: {
  activeStage?: string | null;
  compact?: boolean;
  className?: string;
}) {
  const wsStage = usePipelineHighlight();
  const current = activeStage ?? wsStage;

  function go(step: LoopStep) {
    setPipelineHighlight(step.stage);
    document.getElementById(`pipeline-col-${step.stage}`)?.scrollIntoView({
      behavior: "smooth",
      inline: "center",
      block: "nearest",
    });
  }

  return (
    <div className={cn("rounded-2xl border border-border bg-white px-4 py-3", className)}>
      {!compact ? (
        <div className="mb-2 flex justify-end">
          <Link href="/labs/architecture?tab=loop" className="text-[12px] text-accent hover:underline">
            Architecture
          </Link>
        </div>
      ) : null}
      <ol className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
        {LOOPS_STEPS.map((step) => {
          const hot = current === step.stage || (step.altStages?.includes(current || "") ?? false);
          const idx = LOOPS_STEPS.findIndex((s) => s.n === step.n);
          const done =
            current &&
            LOOPS_STEPS.findIndex((s) => s.stage === current || s.altStages?.includes(current)) > idx;
          return (
            <li key={step.n}>
              <button
                type="button"
                onClick={() => go(step)}
                className={cn(
                  "h-full w-full rounded-xl border px-3 py-2.5 text-left transition-all duration-300",
                  hot && "border-accent bg-[color-mix(in_srgb,var(--accent)_8%,white)] ring-2 ring-accent/20",
                  !hot && done && "border-border bg-[#eef2ee]",
                  !hot && !done && "border-border bg-white hover:border-accent/30"
                )}
              >
                <p className={cn("text-[11px] font-semibold", hot ? "text-accent" : "text-[var(--faint)]")}>
                  {step.n} · {step.short}
                </p>
                <p className="mt-1 text-[12px] font-medium leading-4 text-foreground">{step.label}</p>
                {!compact ? <p className="mt-1 text-[11px] leading-4 text-[var(--dim)]">{step.detail}</p> : null}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
