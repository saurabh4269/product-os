"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { LOOPS_STEPS, useDemoGuide } from "@/lib/demo-guide-context";
import { setPipelineHighlight } from "@/lib/pipeline-highlight";
import { useGlobalWs } from "@/lib/use-global-ws";
import { cn } from "@/lib/utils";

type Step = {
  n: number;
  short: string;
  stage: string;
  altStages?: string[];
};

export function GuidedDemoStrip({ className }: { className?: string }) {
  const demo = useDemoGuide();
  const router = useRouter();
  const { tick } = useGlobalWs();
  const [steps, setSteps] = useState<Step[]>(LOOPS_STEPS);

  useEffect(() => {
    api
      .workflowFocus()
      .then((r) => {
        if (r.steps?.length) {
          setSteps(
            r.steps.map((s) => ({
              n: s.n,
              short: s.short,
              stage: s.stage,
            }))
          );
        }
      })
      .catch(() => {
        /* keep fallback */
      });
  }, [tick, demo?.roomId, demo?.active]);

  if (!demo?.active) return null;

  return (
    <div className={cn("rounded-2xl border border-accent/25 bg-[color-mix(in_srgb,var(--accent)_6%,white)] px-4 py-3", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-accent">Live walkthrough</p>
        {demo.roomId ? (
          <button
            type="button"
            onClick={() => router.push(`/rooms/${demo.roomId}`)}
            className="text-[11px] font-medium text-accent hover:underline"
          >
            Open chat →
          </button>
        ) : null}
      </div>
      <ol className="mt-2 flex flex-wrap gap-x-2 gap-y-2">
        {steps.map((ch, idx) => {
          const done = demo.chapterIndex > idx;
          const current =
            demo.highlightStage === ch.stage || ch.altStages?.includes(demo.highlightStage || "") || false;
          return (
            <li key={`${ch.stage}-${ch.n}`}>
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
