"use client";

import Link from "next/link";
import { LOOPS_STEPS, useDemoGuide } from "@/lib/demo-guide-context";
import { setPipelineHighlight } from "@/lib/pipeline-highlight";
import { cn } from "@/lib/utils";

export function GuidedDemoStrip() {
  const demo = useDemoGuide();
  if (!demo?.active) return null;

  return (
    <div className="mt-4 rounded-2xl border border-accent/25 bg-[color-mix(in_srgb,var(--accent)_6%,white)] px-4 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-accent">Guided demo · live</p>
        {demo.roomId ? (
          <button
            type="button"
            onClick={() => demo.requestFlowView()}
            className="text-[11px] font-medium text-accent hover:underline"
          >
            Open flow overlay
          </button>
        ) : null}
      </div>
      <ol className="mt-2 flex flex-wrap gap-x-2 gap-y-2">
        {LOOPS_STEPS.map((ch) => {
          const idx = LOOPS_STEPS.findIndex((s) => s.n === ch.n);
          const done = demo.chapterIndex > idx;
          const current =
            demo.highlightStage === ch.stage || ch.altStages?.includes(demo.highlightStage || "") || false;
          return (
            <li key={ch.n}>
              <button
                type="button"
                onClick={() => {
                  demo.setHighlightStage(ch.stage);
                  setPipelineHighlight(ch.stage);
                  document.getElementById(`pipeline-col-${ch.stage}`)?.scrollIntoView({
                    behavior: "smooth",
                    inline: "center",
                    block: "nearest",
                  });
                }}
                className={cn(
                  "rounded-full border px-2.5 py-1 text-[12px] font-medium transition-all duration-300",
                  current && "border-accent bg-white text-accent shadow-sm ring-2 ring-accent/20",
                  done && !current && "border-border bg-white/80 text-[var(--dim)]",
                  !done && !current && "border-transparent text-[var(--faint)]"
                )}
              >
                <span className="mr-1 opacity-70">{ch.n}.</span>
                {ch.short}
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
