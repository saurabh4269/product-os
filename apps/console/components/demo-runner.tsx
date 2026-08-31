"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useGlobalWs } from "@/lib/use-global-ws";
import { Button } from "@/components/ui";

export function DemoRunner() {
  const router = useRouter();
  const { activity } = useGlobalWs();
  const [busy, setBusy] = useState(false);
  const [log, setLog] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [roomId, setRoomId] = useState<string | null>(null);

  useEffect(() => {
    if (!busy) return;
    const latest = activity[0];
    if (!latest?.message) return;
    const line = `${latest.agent_id || "system"} · ${latest.message}`;
    setLog((prev) => (prev[0] === line ? prev : [line, ...prev].slice(0, 12)));
  }, [activity, busy]);

  async function run() {
    setBusy(true);
    setErr(null);
    setRoomId(null);
    setLog(["Posting tenant signal…", "Fleet assembling…"]);
    try {
      const out = await api.demoRun();
      setLog((l) => [
        ...l,
        out.joined ? "Joined open investigation" : "Investigation opened",
        "Watch the pipeline board — card should move as agents work",
      ]);
      if (out.room_id) setRoomId(out.room_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Demo failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {busy ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-lg">
            <p className="text-[13px] text-[var(--faint)]">Fleet working</p>
            <h2 className="mt-1 text-[20px] font-semibold tracking-tight">Running tenant signal</h2>
            <ul className="mt-4 space-y-1.5 text-[13px] text-[var(--dim)]">
              {log.map((line, i) => (
                <li key={i} className={i === 0 ? "font-medium text-foreground" : ""}>
                  · {line}
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}

      <div id="demo" className="rounded-2xl border border-border bg-white px-5 py-4">
        <p className="text-[13px] text-[var(--faint)]">Try it</p>
        <h2 className="mt-1 text-[20px] font-semibold tracking-tight">Run a tenant checkout drop</h2>
        <p className="mt-2 max-w-lg text-[14px] leading-6 text-[var(--dim)]">
          One click posts a real signal, runs investigate → evidence → risk, and moves a card on the pipeline board.
          Approve in the room when it lands in Approve.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <Button onClick={() => void run()} disabled={busy}>
            {busy ? "Fleet working…" : "Run demo"}
          </Button>
          {roomId ? (
            <Button variant="ghost" onClick={() => router.push(`/rooms/${roomId}`)}>
              Open room
            </Button>
          ) : null}
          <Link href="/labs" className="text-[13px] text-[var(--dim)] hover:text-accent">
            Eval fixtures →
          </Link>
          {err ? <p className="text-[13px] text-red-600">{err}</p> : null}
        </div>
        {!busy && log.length ? (
          <ul className="mt-4 space-y-1 text-[12px] text-[var(--dim)]">
            {log.slice(0, 6).map((line, i) => (
              <li key={i}>· {line}</li>
            ))}
          </ul>
        ) : null}
      </div>
    </>
  );
}
