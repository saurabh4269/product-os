"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { MIcon } from "@/components/ref/icon";

const SECTIONS = [
  { id: "connect", label: "Connect", href: "/settings", icon: "add_link" },
] as const;

/** Settings chrome — Connect lives here; data plane & architecture stay in main rail. */
export function SettingsChrome({ active = "connect" }: { active?: (typeof SECTIONS)[number]["id"] }) {
  return (
    <header className="mb-margin-lg space-y-4">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div className="max-w-2xl">
          <h1 className="text-display-lg font-bold tracking-tight text-text-primary">Settings</h1>
        </div>
        <Link
          href="/data"
          className="inline-flex items-center gap-2 rounded-lg border border-surface-subtle bg-white px-4 py-2.5 text-label-lg text-primary shadow-sm hover:bg-surface-container-low"
        >
          <MIcon name="database" className="text-[18px]" />
          Data plane
        </Link>
      </div>
      <nav className="flex flex-wrap gap-2 border-b border-surface-subtle pb-3">
        {SECTIONS.map((section) => (
          <Link
            key={section.id}
            href={section.href}
            className={cn(
              "inline-flex items-center gap-2 rounded-full px-4 py-2 text-label-lg transition-colors",
              active === section.id
                ? "bg-primary text-on-primary"
                : "bg-surface-subtle text-text-secondary hover:bg-surface-container-high"
            )}
          >
            <MIcon name={section.icon} className="text-[18px]" />
            {section.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
