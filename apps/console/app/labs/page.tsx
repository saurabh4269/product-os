"use client";

import Link from "next/link";
import { ScenarioChips } from "@/components/scenario-chips";

/** Eval fixtures — hidden from the main demo path (SalesShortcut: one vertical slice on home). */
export default function LabsPage() {
  return (
    <div className="page-pad mx-auto max-w-3xl">
      <Link href="/" className="text-[13px] text-[var(--faint)] hover:text-foreground">
        ← Home
      </Link>
      <header className="mt-6 max-w-xl">
        <p className="text-[13px] text-[var(--faint)]">Labs</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-tight">Eval fixtures</h1>
        <p className="mt-3 text-[15px] leading-6 text-[var(--dim)]">
          Six regression scenarios (Safari, Android, exfil, etc.) share one pipeline. Use these to test gates and
          agents — not the default tenant demo on the homepage.
        </p>
      </header>
      <div className="mt-10">
        <ScenarioChips />
      </div>
    </div>
  );
}
