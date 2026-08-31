"use client";

import Link from "next/link";
import { StatusStrip } from "@/components/status-strip";
import { DemoRunner } from "@/components/demo-runner";
import { cn } from "@/lib/utils";

/** Floating campus controls — live stats + demo CTA (Grok / Buzz energy, minimal copy). */
export function HomeCommandBar({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-black/8 bg-white/92 px-3 py-2.5 shadow-[0_8px_32px_rgba(0,0,0,0.08)] backdrop-blur-md sm:px-4 sm:py-3",
        className
      )}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <StatusStrip compact />
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <DemoRunner variant="bar" />
          <Link
            href="#work"
            className="rounded-full px-3 py-1.5 text-[12px] font-medium text-[var(--dim)] transition hover:bg-[var(--elev)] hover:text-foreground"
          >
            Pipeline ↓
          </Link>
        </div>
      </div>
    </div>
  );
}
