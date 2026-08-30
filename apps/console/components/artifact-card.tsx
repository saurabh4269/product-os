"use client";

import { useState } from "react";
import type { RoomMessage } from "@/lib/api";

export function ArtifactCard({ msg }: { msg: RoomMessage }) {
  const [flip, setFlip] = useState(false);
  const type = (msg.artifact_type ?? "note").replace(/_/g, " ");
  const rows = Object.entries(msg.artifact ?? {})
    .filter(([, v]) => v != null && typeof v !== "object")
    .slice(0, 8) as Array<[string, string]>;

  return (
    <button
      type="button"
      onClick={() => setFlip((f) => !f)}
      className="mt-2 w-full max-w-[620px] cursor-pointer rounded-xl border border-border bg-[var(--elev)] px-4 py-3 text-left transition hover:border-accent/40"
      aria-pressed={flip}
    >
      {!flip ? (
        <>
          <p className="text-[12px] font-medium capitalize text-[var(--faint)]">{type}</p>
          <p className="mt-1 text-[14px] leading-6 text-[var(--ink)]">{msg.text}</p>
          <p className="mt-2 text-[11px] text-[var(--faint)]">Flip for fields</p>
        </>
      ) : (
        <>
          <p className="text-[12px] font-medium capitalize text-accent">{type} · fields</p>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[12px]">
            {rows.length === 0 ? (
              <dd className="col-span-2 text-[var(--dim)]">{msg.text}</dd>
            ) : (
              rows.map(([k, v]) => (
                <span key={k} className="contents">
                  <dt className="text-[var(--faint)]">{k}</dt>
                  <dd className="truncate text-[var(--ink)]">{String(v)}</dd>
                </span>
              ))
            )}
          </dl>
        </>
      )}
    </button>
  );
}
