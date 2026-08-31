"use client";

import { cn } from "@/lib/utils";

/** Detail panel shown when a diagram node / lane is selected. */
export function DiagramDetailPanel({
  title,
  subtitle,
  body,
  meta,
  onClear,
  className,
}: {
  title: string;
  subtitle?: string;
  body?: string;
  meta?: Array<{ label: string; value: string }>;
  onClear?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-accent/30 bg-[color-mix(in_srgb,var(--accent)_5%,white)] px-4 py-3",
        className
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[11px] font-medium uppercase tracking-wide text-accent">{title}</p>
          {subtitle ? <p className="mt-1 text-[15px] font-semibold">{subtitle}</p> : null}
        </div>
        {onClear ? (
          <button type="button" className="text-[11px] text-[var(--dim)] hover:text-foreground" onClick={onClear}>
            Clear
          </button>
        ) : null}
      </div>
      {body ? <p className="mt-2 text-[13px] leading-5 text-[var(--dim)]">{body}</p> : null}
      {meta?.length ? (
        <dl className="mt-3 grid gap-2 sm:grid-cols-2">
          {meta.map((m) => (
            <div key={m.label}>
              <dt className="text-[10px] uppercase tracking-wide text-[var(--faint)]">{m.label}</dt>
              <dd className="text-[13px] font-medium">{m.value}</dd>
            </div>
          ))}
        </dl>
      ) : null}
    </div>
  );
}
