"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { Button } from "@/components/ui";

/** Eval fixture chips — product-os-v2 scenario runner energy. Not product shape. */
export function ScenarioChips() {
  const router = useRouter();
  const [items, setItems] = useState<Array<{ id: string; title?: string }>>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [roomId, setRoomId] = useState<string | null>(null);
  const [log, setLog] = useState<string[]>([]);

  useEffect(() => {
    api
      .config()
      .then((c) => {
        if (!c.eval_mode && process.env.NEXT_PUBLIC_LOOP_EVAL === "0") {
          setItems([]);
          return;
        }
        if (!c.eval_mode) {
          setItems([]);
          return;
        }
        return api.scenarios().then((r) => {
          const rows = (r.scenarios ?? []).map((s) => ({
            id: String(s.id ?? s.scenario_id ?? ""),
            title: String(s.title ?? s.id ?? ""),
          }));
          setItems(rows.filter((x) => x.id));
        });
      })
      .catch(() => setItems([]));
  }, []);

  async function run(slug: string) {
    setBusy(slug);
    setErr(null);
    setRoomId(null);
    setLog([`Running ${slug}…`, "Agents investigating"]);
    try {
      const res = await api.scenarioRun(slug);
      setLog((l) => [...l, "Done"]);
      if (res.room_id) setRoomId(res.room_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(null);
    }
  }

  if (!items.length) return null;

  return (
    <>
      {busy ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm">
          <div className="mx-4 w-full max-w-md rounded-2xl border border-border bg-white p-6 shadow-lg">
            <p className="text-[13px] text-[var(--faint)]">Eval fixture</p>
            <h2 className="mt-1 text-[20px] font-semibold tracking-tight">Running {busy}</h2>
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
    <div className="mt-6">
      <p className="text-[12px] text-[var(--faint)]">Eval fixtures</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {items.map((s) => (
          <button
            key={s.id}
            type="button"
            disabled={busy !== null}
            onClick={() => void run(s.id)}
            className="rounded-full border border-border bg-white px-3 py-1.5 text-[12px] font-medium text-[var(--dim)] hover:border-accent/40 hover:text-accent disabled:opacity-50"
          >
            {busy === s.id ? "Running…" : s.title || s.id}
          </button>
        ))}
      </div>
      {roomId ? (
        <div className="mt-3 flex flex-wrap gap-3">
          <Button variant="ghost" onClick={() => router.push(`/rooms/${roomId}`)}>
            Open room
          </Button>
          <Link href="/" className="self-center text-[13px] text-accent hover:underline">
            Watch pipeline on home →
          </Link>
        </div>
      ) : null}
      {err ? <p className="mt-2 text-[12px] text-red-600">{err}</p> : null}
    </div>
    </>
  );
}
