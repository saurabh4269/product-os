"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useGlobalWs, type ActivityEvent } from "@/lib/use-global-ws";

function Row({ e }: { e: ActivityEvent }) {
  const who = e.agent_id || "system";
  const room = e.room_id;
  return (
    <div className="flex gap-2 text-[12px] leading-5 text-[var(--dim)]">
      <span className="shrink-0 text-[var(--faint)]">{who}</span>
      <span className="min-w-0 flex-1 truncate">{e.message}</span>
      {room ? (
        <Link href={`/rooms/${room}`} className="shrink-0 text-accent hover:underline">
          room
        </Link>
      ) : null}
    </div>
  );
}

export function ActivityLog() {
  const { activity: live, tick } = useGlobalWs();
  const [seed, setSeed] = useState<ActivityEvent[]>([]);

  useEffect(() => {
    api
      .activity()
      .then((r) => setSeed(r.events))
      .catch(() => setSeed([]));
  }, [tick]);

  const rows = [...live, ...seed].slice(0, 40);

  return (
    <div className="mt-8 rounded-2xl border border-border bg-white px-4 py-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-[var(--faint)]">Activity</p>
      <div className="mt-2 max-h-36 space-y-1 overflow-y-auto">
        {rows.length ? (
          rows.map((e, i) => <Row key={`${e.ts}-${i}`} e={e} />)
        ) : (
          <p className="text-[12px] text-[var(--faint)]">Fleet idle — run demo to see agents work.</p>
        )}
      </div>
    </div>
  );
}
