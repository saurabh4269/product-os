"use client";

import type { Bundle, Room } from "@/lib/api";
import { cn } from "@/lib/utils";

function pathLabel(bundle: Bundle | null, room: Room) {
  const hyp = bundle?.hypotheses?.[0];
  const cls = hyp?.classification?.toUpperCase();
  const lt = (room.loop_type || "").toLowerCase();
  if (cls === "BUG" || lt === "type_a") return { label: "Type A", sub: "Find and fix", tone: "bug" as const };
  if (cls === "OPPORTUNITY" || lt === "type_b") return { label: "Type B", sub: "Find and improve", tone: "feature" as const };
  return null;
}

export function roomLoopLabel(bundle: Bundle | null, room: Room) {
  return pathLabel(bundle, room);
}

/** Type A/B, risk tier, recalled lessons, investigation state — visible in chat, not buried in lab. */
export function RoomCaseBanner({
  room,
  bundle,
  className,
}: {
  room: Room;
  bundle: Bundle | null;
  className?: string;
}) {
  const path = pathLabel(bundle, room);
  const action = bundle?.actions?.find((a) => ["proposed", "awaiting_approval"].includes(a.status)) || bundle?.actions?.[0];
  const recalled = bundle?.investigation?.recalled_lessons ?? [];
  const hyp = bundle?.hypotheses?.[0];
  const state = bundle?.investigation?.state;

  if (!path && !action && !recalled.length && !hyp) return null;

  return (
    <div className={cn("mb-4 space-y-2", className)}>
      <div className="flex flex-wrap items-center gap-2">
        {path ? (
          <span
            className={cn(
              "rounded-full px-2.5 py-1 text-[11px] font-semibold",
              path.tone === "bug" ? "bg-sky-50 text-sky-900" : "bg-emerald-50 text-emerald-900"
            )}
          >
            {path.label} · {path.sub}
          </span>
        ) : null}
        {action?.risk_tier ? (
          <span
            className={cn(
              "rounded-full px-2.5 py-1 text-[11px] font-semibold",
              action.risk_tier === "HIGH"
                ? "bg-orange-50 text-orange-900 ring-1 ring-orange-200/80"
                : action.risk_tier === "MEDIUM"
                  ? "bg-amber-50 text-amber-900"
                  : "bg-[var(--elev)] text-[var(--dim)]"
            )}
          >
            {action.risk_tier} risk
            {action.gate_mode ? ` · ${action.gate_mode}` : ""}
          </span>
        ) : null}
        {state ? (
          <span className="rounded-full bg-[var(--elev)] px-2.5 py-1 text-[11px] font-medium text-[var(--dim)]">
            {state.replace(/_/g, " ")}
          </span>
        ) : null}
        {hyp ? (
          <span className="text-[12px] text-[var(--faint)]">
            {Math.round((hyp.confidence || 0) * 100)}% confidence · {hyp.independence_groups?.length || 0} evidence arms
          </span>
        ) : null}
      </div>
      {hyp?.statement ? (
        <p className="text-[14px] font-medium leading-5 text-foreground">{hyp.statement}</p>
      ) : null}
      {recalled.length > 0 ? (
        <div className="rounded-xl border border-accent/20 bg-accent/[0.04] px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-accent">Memory recall</p>
          <ul className="mt-1 space-y-0.5">
            {recalled.slice(0, 3).map((lesson) => (
              <li key={lesson} className="text-[12px] leading-5 text-[var(--dim)]">
                {lesson}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {bundle?.verdicts?.length ? (
        <div className="rounded-xl border border-danger/25 bg-danger/[0.04] px-3 py-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-danger">Gateway deny · identity</p>
          {bundle.verdicts.map((v) => (
            <p key={String(v.id)} className="mt-1 text-[12px] text-[var(--dim)]">
              {String(v.tool)} — {String(v.verdict)}. {String(v.rationale)}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
