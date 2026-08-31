"use client";

import Link from "next/link";
import { ScenarioChips } from "@/components/scenario-chips";

/** Labs hub — architecture diagrams + eval fixtures. */
export default function LabsPage() {
  return (
    <div className="page-pad mx-auto max-w-3xl">
      <Link href="/" className="text-[13px] text-[var(--faint)] hover:text-foreground">
        ← Home
      </Link>
      <header className="mt-6 max-w-xl">
        <p className="text-[13px] text-[var(--faint)]">Labs</p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-tight">Diagrams &amp; eval fixtures</h1>
        <p className="mt-3 text-[15px] leading-6 text-[var(--dim)]">
          Architecture for judges and operators. Eval scenarios for regression — not the default tenant demo on the
          homepage.
        </p>
      </header>

      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        <Link
          href="/labs/architecture"
          className="rounded-2xl border border-border bg-white px-5 py-4 transition-colors hover:border-accent/40"
        >
          <p className="text-[11px] font-medium uppercase tracking-wide text-accent">Architecture</p>
          <h2 className="mt-1 text-[18px] font-semibold tracking-tight">Five planes + pipeline</h2>
          <p className="mt-2 text-[14px] leading-6 text-[var(--dim)]">
            Mermaid flow, fleet swimlanes, tenant wire — syncs with live pipeline highlight.
          </p>
        </Link>
        <div className="rounded-2xl border border-border bg-[#eef2ee] px-5 py-4">
          <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--faint)]">Eval</p>
          <h2 className="mt-1 text-[18px] font-semibold tracking-tight">Six fixtures</h2>
          <p className="mt-2 text-[14px] leading-6 text-[var(--dim)]">
            Safari, Android, exfil DENY, and more — one pipeline, regression only.
          </p>
        </div>
      </div>

      <div className="mt-10">
        <ScenarioChips />
      </div>
    </div>
  );
}
