"use client";

import Link from "next/link";
import { LOOPS_STEPS, useDemoGuide } from "@/lib/demo-guide-context";
import { setPipelineHighlight } from "@/lib/pipeline-highlight";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui";

export function PipelineFlowOverlay({
  open,
  onClose,
  title,
  stage,
  roomId,
  evidenceSnippet,
  voiceSnippet,
  calendarSnippet,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  stage: string;
  roomId: string;
  evidenceSnippet?: string | null;
  voiceSnippet?: string | null;
  calendarSnippet?: string | null;
}) {
  const demo = useDemoGuide();
  if (!open) return null;

  const idx = LOOPS_STEPS.findIndex((s) => s.stage === stage || s.altStages?.includes(stage));

  function goStep(stepStage: string) {
    setPipelineHighlight(stepStage);
    demo?.setHighlightStage(stepStage);
    document.getElementById(`pipeline-col-${stepStage}`)?.scrollIntoView({ behavior: "smooth", inline: "center" });
  }

  return (
    <div className="fixed inset-0 z-[55] flex items-end justify-center bg-black/15 p-4 sm:items-center" onClick={onClose}>
      <div
        className="w-full max-w-lg rounded-2xl border border-border bg-white p-6 shadow-xl"
        role="dialog"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-[13px] text-[var(--faint)]">Investigation flow</p>
        <h2 className="mt-1 text-[18px] font-semibold tracking-tight">{title}</h2>
        {evidenceSnippet ? (
          <p className="mt-2 text-[12px] leading-5 text-[var(--dim)] line-clamp-3">{evidenceSnippet}</p>
        ) : null}
        {voiceSnippet ? (
          <p className="mt-1 text-[12px] italic text-[var(--dim)] line-clamp-2">“{voiceSnippet}”</p>
        ) : null}
        {calendarSnippet ? <p className="mt-1 text-[12px] font-medium text-accent">{calendarSnippet}</p> : null}
        <ol className="mt-4 space-y-2">
          {LOOPS_STEPS.map((step, i) => {
            const current = step.stage === stage || step.altStages?.includes(stage);
            const done = idx > i;
            return (
              <li key={step.n}>
                <button
                  type="button"
                  onClick={() => goStep(step.stage)}
                  className={cn(
                    "flex w-full items-start gap-3 rounded-xl border px-3 py-2 text-left transition-colors",
                    current && "border-accent bg-[color-mix(in_srgb,var(--accent)_8%,white)]",
                    done && !current && "border-border bg-[#eef2ee]",
                    !done && !current && "border-transparent text-[var(--faint)]"
                  )}
                >
                  <span className="mt-0.5 text-[11px] font-semibold text-[var(--faint)]">{step.n}</span>
                  <span>
                    <span className="block text-[13px] font-medium text-foreground">{step.label}</span>
                    <span className="block text-[11px] text-[var(--dim)]">{step.detail}</span>
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link href={`/rooms/${roomId}`}>
            <Button>Open room</Button>
          </Link>
          <Button variant="ghost" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
