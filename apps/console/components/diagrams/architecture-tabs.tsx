"use client";

import { cn } from "@/lib/utils";

export const ARCH_TABS = [
  { id: "overview", label: "Overview" },
  { id: "loop", label: "Loop" },
  { id: "fleet", label: "Fleet" },
  { id: "deep", label: "Deep dive" },
] as const;

export type ArchTab = (typeof ARCH_TABS)[number]["id"];

export function ArchitectureTabs({
  tab,
  onTab,
  className,
}: {
  tab: ArchTab;
  onTab: (t: ArchTab) => void;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-wrap gap-2 border-b border-border pb-3", className)}>
      {ARCH_TABS.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={() => onTab(t.id)}
          className={cn(
            "rounded-full px-3 py-1.5 text-[13px] font-medium transition-colors",
            tab === t.id ? "bg-accent text-white" : "text-[var(--dim)] hover:bg-[var(--elev)] hover:text-foreground"
          )}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
