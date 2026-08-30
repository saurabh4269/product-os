"use client";

export type FunnelStep = { id: string; label: string; on: boolean };

/** Handoff rail — product-os-v2 presence + investigation stage. */
export function FunnelChips({
  steps,
  current,
  presence,
}: {
  steps: FunnelStep[];
  current?: string;
  presence?: Record<string, string>;
}) {
  if (!steps?.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-1 text-[12px]">
      {steps.map((s, i) => {
        const st = presence?.[s.id] || "";
        const live = Boolean(st && st !== "idle");
        const on = live || s.id === current || s.on;
        return (
          <span key={s.id} className="flex items-center gap-1">
            {i > 0 ? (
              <span className={on ? "text-accent" : "text-[var(--faint)]"} aria-hidden>
                →
              </span>
            ) : null}
            <span
              className={
                "rounded-full border px-2 py-0.5 font-medium " +
                (on
                  ? "border-accent/40 bg-[color-mix(in_srgb,var(--accent)_12%,transparent)] text-accent"
                  : "border-border text-[var(--faint)]")
              }
            >
              {s.label}
              {live ? <span className="ml-1 font-mono text-[9px] opacity-80">{st}</span> : null}
            </span>
          </span>
        );
      })}
    </div>
  );
}
