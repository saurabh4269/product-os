"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type Investigation, type Room } from "@/lib/api";
import { ArchifyEmbed } from "@/components/archify-embed";
import { PageHeader, PageStatPill } from "@/components/page-header";
import { ScenarioChips } from "@/components/scenario-chips";

const CLOSED = new Set(["RESOLVED", "NOT_RESOLVED", "INCONCLUSIVE", "PARTIALLY_RESOLVED"]);

function stateLabel(state: string) {
  return state.replace(/_/g, " ").toLowerCase();
}

/** Labs — live architecture + eval fixtures + open fixture runs. */
export function LabsHub() {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [evalMode, setEvalMode] = useState(false);
  const [fixtures, setFixtures] = useState<string[]>([]);

  useEffect(() => {
    Promise.all([api.investigations(), api.rooms(), api.config()])
      .then(([inv, r, cfg]) => {
        setInvestigations(inv.investigations);
        setRooms(r.rooms);
        setEvalMode(cfg.eval_mode);
        setFixtures(cfg.fixture_scenarios ?? []);
      })
      .catch(() => undefined);
  }, []);

  const roomByInv = useMemo(() => {
    const m: Record<string, Room> = {};
    for (const room of rooms) {
      if (room.investigation_id) m[room.investigation_id] = room;
    }
    return m;
  }, [rooms]);

  const openRuns = useMemo(
    () => investigations.filter((i) => !CLOSED.has(i.state)),
    [investigations]
  );

  const resolved = useMemo(
    () => investigations.filter((i) => ["RESOLVED", "PARTIALLY_RESOLVED"].includes(i.state)).length,
    [investigations]
  );

  return (
    <div className="mx-auto max-w-container-max space-y-margin-lg">
      <PageHeader title="Labs">
        <PageStatPill>
          Eval <span className="font-semibold text-text-primary">{evalMode ? "on" : "off"}</span>
        </PageStatPill>
        <PageStatPill>
          <span className="font-semibold text-text-primary">{openRuns.length}</span> open
        </PageStatPill>
        <PageStatPill>
          <span className="font-semibold text-ok">{resolved}</span> resolved
        </PageStatPill>
      </PageHeader>

      <ArchifyEmbed compact eager defaultDiagram="system" />

      {openRuns.length > 0 ? (
        <section className="space-y-3">
          <h2 className="text-[13px] font-semibold uppercase tracking-wide text-[var(--dim)]">Open runs</h2>
          <ul className="space-y-2">
            {openRuns.map((inv) => {
              const room = roomByInv[inv.id];
              const href = room ? `/rooms/${room.id}` : inv.room_id ? `/rooms/${inv.room_id}` : null;
              const title = room?.title || inv.scenario_id?.replace(/_/g, " ") || inv.id;
              return (
                <li key={inv.id}>
                  {href ? (
                    <Link
                      href={href}
                      className="flex items-center justify-between gap-3 rounded-xl border border-border bg-white px-4 py-3 shadow-[0_1px_2px_rgba(29,29,31,0.04)] transition hover:border-accent/30"
                    >
                      <span className="min-w-0 truncate text-[14px] font-medium text-foreground">{title}</span>
                      <span className="shrink-0 rounded-full bg-[var(--elev)] px-2 py-0.5 text-[11px] capitalize text-[var(--dim)]">
                        {stateLabel(inv.state)}
                      </span>
                    </Link>
                  ) : (
                    <div className="flex items-center justify-between gap-3 rounded-xl border border-border bg-white px-4 py-3">
                      <span className="text-[14px] font-medium text-foreground">{title}</span>
                      <span className="rounded-full bg-[var(--elev)] px-2 py-0.5 text-[11px] capitalize text-[var(--dim)]">
                        {stateLabel(inv.state)}
                      </span>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      <section className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-[13px] font-semibold uppercase tracking-wide text-[var(--dim)]">Eval fixtures</h2>
          <Link href="/labs/architecture" className="text-[13px] font-medium text-accent hover:underline">
            Architecture
          </Link>
        </div>
        {evalMode ? (
          <ScenarioChips />
        ) : (
          <div className="rounded-xl border border-dashed border-border bg-[#f8fafc] px-4 py-5">
            <p className="text-[13px] text-[var(--dim)]">Eval mode is off on this deployment.</p>
            {fixtures.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {fixtures.map((id) => (
                  <span
                    key={id}
                    className="rounded-full border border-border bg-white px-3 py-1 font-mono text-[11px] text-[var(--dim)]"
                  >
                    {id}
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        )}
      </section>
    </div>
  );
}
