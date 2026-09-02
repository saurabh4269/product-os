"use client";

import Link from "next/link";
import { StatusStrip } from "@/components/status-strip";
import { DemoRunner } from "@/components/demo-runner";
import type { HomePulse, PulseAction } from "@/lib/home-pulse";
import { cn } from "@/lib/utils";

function actionHref(action: PulseAction) {
  if (action === "pipeline" || action === "approvals") return "#work";
  if (action === "connect") return "/connect";
  return "#work";
}

/** Floating campus controls — live stats + contextual pulse + demo CTA. */
export function HomeCommandBar({
  pulse,
  className,
  evalMode = true,
}: {
  pulse?: HomePulse | null;
  className?: string;
  evalMode?: boolean;
}) {
  const hot = pulse?.campusHot;

  return (
    <div
      className={cn(
        "surface-glass px-3 py-2.5 sm:px-4 sm:py-3",
        hot ? "border-accent/25" : "",
        className
      )}
    >
      {pulse?.commandLine && hot ? (
        <p className="mb-2 text-[12px] font-medium leading-5 text-accent sm:text-[13px]">
          {pulse.commandAction ? (
            <Link href={actionHref(pulse.commandAction)} className="hover:underline">
              {pulse.commandLine}
            </Link>
          ) : (
            pulse.commandLine
          )}
        </p>
      ) : null}
      <div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 overflow-x-auto">
          <StatusStrip compact />
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {evalMode ? <DemoRunner variant="bar" /> : null}
          <Link
            href="#work"
            className="rounded-full px-3 py-1.5 text-[12px] font-medium text-[var(--dim)] transition hover:bg-[var(--elev)] hover:text-foreground"
          >
            Work ↓
          </Link>
        </div>
      </div>
    </div>
  );
}
