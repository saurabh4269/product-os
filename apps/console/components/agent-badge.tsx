"use client";

import { agentPalette, shortName } from "@/lib/names";
import { cn } from "@/lib/utils";

export type AgentStatus = "idle" | "working" | "handing_off" | "thinking" | "tool";

function MiniFace({ fg, size, sleepy }: { fg: string; size: number; sleepy?: boolean }) {
  const dot = Math.max(2, Math.round(size * 0.1));
  const gap = Math.max(2, Math.round(size * 0.13));
  return (
    <span className="inline-flex items-center justify-center" style={{ gap }} aria-hidden>
      <span
        className={cn("rounded-full", sleepy ? "opacity-35" : "opacity-80")}
        style={{ width: dot, height: dot, backgroundColor: fg }}
      />
      <span
        className={cn("rounded-full", sleepy ? "opacity-35" : "opacity-80")}
        style={{ width: dot, height: dot, backgroundColor: fg }}
      />
    </span>
  );
}

const STATUS_PIP: Record<AgentStatus, string | null> = {
  idle: null,
  working: "bg-accent",
  handing_off: "bg-warn",
  thinking: "bg-accent animate-pulse",
  tool: "bg-warn",
};

/** Minimal cute agent avatar — muted when idle, pip when active. */
export function AgentBadge({
  name,
  working,
  status,
  size = 20,
  variant = "auto",
  className,
}: {
  name: string;
  working?: boolean;
  status?: AgentStatus;
  size?: number;
  variant?: "auto" | "face" | "initial";
  className?: string;
}) {
  const resolved: AgentStatus =
    status ?? (working ? "working" : "idle");
  const { bg, fg } = agentPalette(name);
  const label = shortName(name).charAt(0).toUpperCase();
  const showFace = variant === "face" || (variant === "auto" && size >= 26);
  const pip = Math.max(5, Math.round(size * 0.22));
  const pipClass = STATUS_PIP[resolved];
  const isIdle = resolved === "idle";

  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-full border border-black/[0.04] shadow-sm ring-2 ring-white/80 transition-opacity duration-300",
        isIdle && "opacity-50 saturate-[0.85]",
        className
      )}
      style={{ width: size, height: size, background: bg, color: fg }}
      title={shortName(name)}
    >
      {showFace ? (
        <MiniFace fg={fg} size={size} sleepy={isIdle} />
      ) : (
        <span className="font-semibold leading-none" style={{ fontSize: Math.max(8, Math.round(size * 0.38)) }}>
          {label}
        </span>
      )}
      {pipClass ? (
        <span
          className={cn("absolute -bottom-0.5 -right-0.5 rounded-full ring-2 ring-white", pipClass)}
          style={{ width: pip, height: pip }}
          aria-hidden
        />
      ) : null}
    </span>
  );
}

export function AgentStack({
  names,
  working,
  size = 20,
  max = 3,
  className,
}: {
  names: string[];
  working?: Set<string> | string[];
  size?: number;
  max?: number;
  className?: string;
}) {
  const work = working instanceof Set ? working : new Set(working ?? []);
  const shown = names.filter((n) => n !== "system").slice(0, max);
  const extra = names.length - shown.length;
  if (!shown.length) return null;

  return (
    <span className={cn("inline-flex items-center", className)}>
      {shown.map((name, i) => (
        <AgentBadge
          key={name}
          name={name}
          status={work.has(name) ? "working" : "idle"}
          size={size}
          variant={size >= 24 ? "face" : "initial"}
          className={cn(i > 0 && "-ml-1.5 ring-2 ring-white")}
        />
      ))}
      {extra > 0 ? (
        <span className="ml-1 text-[10px] font-medium tabular-nums text-[var(--faint)]">+{extra}</span>
      ) : null}
    </span>
  );
}
