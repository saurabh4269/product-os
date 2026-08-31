"use client";

import Link from "next/link";
import { WorkflowLinksPanel } from "@/components/workflow-links";
import { PageHeader } from "@/components/ui";

export default function WorkflowsPage() {
  return (
    <div className="page-pad fade-in mx-auto max-w-3xl">
      <Link href="/" className="text-[13px] text-[var(--faint)] hover:text-foreground" aria-label="Home">
        ←
      </Link>
      <PageHeader title="Workflows" className="mt-6" />
      <WorkflowLinksPanel className="mt-8" />
    </div>
  );
}
