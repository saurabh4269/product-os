"use client";

import Link from "next/link";
import { ScenarioChips } from "@/components/scenario-chips";
import { PageHeader } from "@/components/ui";

/** Labs hub — architecture diagrams + eval fixtures. */
export default function LabsPage() {
  return (
    <div className="page-pad fade-in mx-auto max-w-3xl">
      <Link href="/" className="text-[13px] text-[var(--faint)] hover:text-foreground" aria-label="Home">
        ←
      </Link>
      <PageHeader title="Labs" className="mt-6" />

      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        <Link href="/labs/architecture" className="surface-lg interactive block px-5 py-4 press">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-accent">Architecture</p>
          <h2 className="mt-1 text-[18px] font-semibold tracking-tight">Five planes + pipeline</h2>
        </Link>
        <div className="surface-lg px-5 py-4">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--faint)]">Eval</p>
          <h2 className="mt-1 text-[18px] font-semibold tracking-tight">Six fixtures</h2>
        </div>
      </div>

      <div className="mt-10">
        <ScenarioChips />
      </div>
    </div>
  );
}
