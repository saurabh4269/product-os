"use client";

import { useEffect, useState, type ReactNode } from "react";
import { getExploreOpenPreference, hasRunDemo, setExploreOpenPreference } from "@/lib/first-visit";
import { cn } from "@/lib/utils";
import { ChevronDown } from "lucide-react";

/** Progressive disclosure — office floor + rooms below the fold. */
export function ExploreSection({
  title = "Explore",
  defaultOpen,
  demoActive,
  children,
}: {
  title?: string;
  defaultOpen?: boolean;
  demoActive?: boolean;
  children: ReactNode;
}) {
  const saved = getExploreOpenPreference();
  const [open, setOpen] = useState(defaultOpen ?? saved ?? hasRunDemo());

  useEffect(() => {
    if (demoActive || hasRunDemo()) setOpen(true);
  }, [demoActive]);

  function toggle() {
    setOpen((o) => {
      const next = !o;
      setExploreOpenPreference(next);
      return next;
    });
  }

  return (
    <div id="explore">
      <button
        type="button"
        onClick={toggle}
        className="surface-lg interactive flex w-full items-center justify-between gap-3 px-4 py-3.5 text-left sm:px-5 press"
      >
        <span className="text-[16px] font-semibold tracking-tight">{title}</span>
        <ChevronDown
          className={cn("h-5 w-5 shrink-0 text-[var(--faint)] transition-transform", open && "rotate-180")}
        />
      </button>
      {open ? <div className="mt-6">{children}</div> : null}
    </div>
  );
}
