"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

/** Eval fixture chips — product-os-v2 scenario runner energy. Not product shape. */
export function ScenarioChips() {
  const router = useRouter();
  const [items, setItems] = useState<Array<{ id: string; title?: string }>>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .scenarios()
      .then((r) => {
        const rows = (r.scenarios ?? []).map((s) => ({
          id: String(s.id ?? s.scenario_id ?? ""),
          title: String(s.title ?? s.id ?? ""),
        }));
        setItems(rows.filter((x) => x.id));
      })
      .catch(() => setItems([]));
  }, []);

  async function run(slug: string) {
    setBusy(slug);
    setErr(null);
    try {
      const res = await api.scenarioRun(slug);
      router.push(`/rooms/${res.room_id}`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "failed");
    } finally {
      setBusy(null);
    }
  }

  if (!items.length) return null;

  return (
    <div className="mt-6">
      <p className="text-[12px] text-[var(--faint)]">Eval fixtures — run the fleet live</p>
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
      {err ? <p className="mt-2 text-[12px] text-red-600">{err}</p> : null}
    </div>
  );
}
