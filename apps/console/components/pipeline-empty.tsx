"use client";

import Link from "next/link";
import { Play } from "lucide-react";
import { useDemoGuide } from "@/lib/demo-guide-context";
import { hasRunDemo } from "@/lib/first-visit";
import { Button } from "@/components/ui";

export function PipelineEmpty() {
  const demo = useDemoGuide();
  const returning = hasRunDemo();

  return (
    <div className="mt-4 rounded-2xl border border-dashed border-border bg-[#eef2ee]/60 px-6 py-10 text-center">
      <p className="text-[15px] font-semibold tracking-tight">{returning ? "Clear" : "Ready"}</p>
      <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
        <Button onClick={() => demo?.triggerDemo?.()} className={!returning ? "cta-pulse gap-2" : "gap-2"}>
          <Play size={14} strokeWidth={2} aria-hidden />
          See a scenario
        </Button>
        {returning ? (
          <>
            <Link
              href="/labs"
              className="inline-flex items-center rounded-xl border border-border bg-white px-4 py-2 text-[13px] font-medium text-foreground hover:bg-[var(--elev)]"
            >
              Labs
            </Link>
            <Link
              href="/connect"
              className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-accent hover:bg-[var(--elev)]"
              aria-label="Connect Product Y"
              title="Connect"
            >
              +
            </Link>
          </>
        ) : null}
      </div>
    </div>
  );
}
