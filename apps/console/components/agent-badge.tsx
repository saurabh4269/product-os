"use client";

import { hashHue, shortName } from "@/lib/names";
import { cn } from "@/lib/utils";

/** Static agent mark for dense UI — no leg-bob animation. */
export function AgentBadge({
  name,
  working,
  size = 20,
  className,
}: {
  name: string;
  working?: boolean;
  size?: number;
  className?: string;
}) {
  const hue = hashHue(name);
  const initial = shortName(name).charAt(0).toUpperCase();
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white",
        working && "ring-2 ring-accent/45",
        className
      )}
      style={{
        width: size,
        height: size,
        fontSize: Math.max(9, Math.round(size * 0.42)),
        background: `hsl(${hue} 28% 42%)`,
      }}
      title={shortName(name)}
      aria-hidden
    >
      {initial}
    </span>
  );
}
