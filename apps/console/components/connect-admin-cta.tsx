"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

/** Prompt unauthenticated visitors to paste LOOP_ADMIN_TOKEN on Connect. */
export function ConnectAdminCta({
  variant = "inline",
  className,
  title = "Authorize to see office and rooms",
  detail = "Campus stays live — paste LOOP_ADMIN_TOKEN on Connect to hydrate agents.",
}: {
  variant?: "inline" | "overlay";
  className?: string;
  title?: string;
  detail?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-dashed border-accent/40 bg-white/95 px-4 py-3 text-center shadow-sm backdrop-blur-sm",
        variant === "overlay" && "pointer-events-auto absolute bottom-24 left-4 right-4 z-30 mx-auto max-w-md sm:left-8 sm:bottom-28 sm:right-auto",
        className
      )}
    >
      <p className="text-[13px] font-medium text-foreground">{title}</p>
      <p className="mt-0.5 text-[12px] text-[var(--dim)]">{detail}</p>
      <Link
        href="/connect"
        className="mt-2 inline-flex items-center gap-1 text-[13px] font-medium text-accent hover:underline"
      >
        Open Connect
        <ExternalLink className="h-3 w-3" />
      </Link>
    </div>
  );
}
