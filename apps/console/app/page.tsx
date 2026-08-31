"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type OfficeSnapshot, type Room } from "@/lib/api";
import { pct } from "@/lib/utils";
import { ErrorState } from "@/components/ui";
import { CityMap } from "@/components/city-map";
import { IsoOffice } from "@/components/iso-office";
import { OfficeFloor } from "@/components/office-floor";
import { RoomCard } from "@/components/work-flipbook";
import { StatusStrip } from "@/components/status-strip";
import { PipelineBoard } from "@/components/pipeline-board";
import { ActivityLog } from "@/components/activity-log";
import { DemoRunner } from "@/components/demo-runner";
import Link from "next/link";

function magLabel(raw: unknown) {
  const n = Number(raw);
  if (Number.isNaN(n)) return "—";
  return Math.abs(n) > 1 ? String(Math.round(n)) : pct(n);
}

export default function HomePage() {
  const [rooms, setRooms] = useState<Room[]>([]);
  const [office, setOffice] = useState<OfficeSnapshot | null>(null);
  const [signals, setSignals] = useState<Array<Record<string, unknown>>>([]);
  const [evalMode, setEvalMode] = useState(true);
  const [fixtureSlugs, setFixtureSlugs] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [inside, setInside] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    Promise.all([api.rooms(), api.signals(), api.office(), api.config()])
      .then(([r, s, o, cfg]) => {
        setRooms(r.rooms);
        setSignals(s.signals);
        setOffice(o);
        setEvalMode(cfg.eval_mode);
        setFixtureSlugs(new Set(cfg.fixture_scenarios ?? []));
        setErr(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "API unreachable"));
  }, []);

  if (err) return <ErrorState message={err} />;

  const desks = office?.desks ?? [];
  const handoffs = office?.handoffs ?? [];
  const chambers = rooms.filter((r) => {
    const isFixture = r.scenario_id && fixtureSlugs.has(r.scenario_id);
    if (!evalMode && isFixture) return false;
    return Boolean(r.scenario_id) || ["review", "research", "ops"].includes(r.kind);
  });

  function walkInside(district: string) {
    setInside(district);
    window.requestAnimationFrame(() => {
      document.getElementById("inside")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  return (
    <>
      {/* SalesShortcut energy: command center first — pipeline + activity before the campus metaphor */}
      <section className="page-pad border-b border-border bg-background">
        <header className="max-w-xl">
          <p className="text-[13px] text-[var(--faint)]">Product OS</p>
          <h1 className="mt-1 text-[28px] font-semibold tracking-tight sm:text-[32px]">Watch work move</h1>
          <p className="mt-3 text-[15px] leading-6 text-[var(--dim)]">
            Signals become investigations. Agents gather evidence. You approve risky changes. The fleet verifies and
            remembers.
          </p>
        </header>
        <div className="mt-8">
          <StatusStrip />
        </div>
        <div className="mt-6">
          <DemoRunner />
        </div>
        <PipelineBoard />
        <ActivityLog />
      </section>

      <section className="relative shrink-0 min-h-[min(52vh,420px)] sm:min-h-[min(58vh,480px)] lg:h-[min(72vh,640px)]">
        <CityMap
          rooms={chambers}
          desks={desks}
          handoffs={handoffs}
          picked={picked}
          onPick={(id) => setPicked(id)}
          onWalkInside={walkInside}
        />
      </section>

      <section className="page-pad bg-background">
        <header className="max-w-xl mt-4 sm:mt-6">
          <p className="text-[13px] text-[var(--faint)]">Campus</p>
          <h2 className="mt-1 text-[24px] font-semibold tracking-tight sm:text-[28px]">The office, up close</h2>
          <p className="mt-3 text-[15px] leading-6 text-[var(--dim)]">
            Walk the isometric floor, then flip a piece of work until you are in the room.{" "}
            <Link href="/labs" className="text-accent hover:underline">
              Eval fixtures
            </Link>{" "}
            live in Labs.
          </p>
        </header>

        {signals.length > 0 ? (
          <div className="mt-10 flex flex-wrap gap-x-10 gap-y-4">
            {signals.map((s) => {
              const segs =
                (s.affected_segments as Array<{ browser?: string; os?: string; platform?: string; geo?: string }>) ?? [];
              const who = segs[0]?.browser || segs[0]?.os || segs[0]?.platform || segs[0]?.geo || "all";
              return (
                <div key={String(s.id)}>
                  <p className="text-[12px] text-[var(--faint)]">
                    {String(s.metric).replace(/_/g, " ")} · {who}
                  </p>
                  <p className="mt-0.5 text-[20px] font-semibold tracking-tight text-foreground">{magLabel(s.magnitude)}</p>
                </div>
              );
            })}
          </div>
        ) : null}

        <div id="inside" className="mt-12 scroll-mt-6">
          <IsoOffice
            desks={desks}
            rooms={chambers}
            handoffs={handoffs}
            focus={inside}
            picked={picked}
            onPickRoom={(id, district) => {
              setPicked(id);
              if (district) setInside(district);
              if (id) router.push(`/rooms/${id}`);
            }}
            onPickDistrict={(d) => setInside(d || null)}
          />
        </div>

        <div className="mt-12">
          <OfficeFloor desks={desks} handoffs={handoffs} working={office?.working ?? 0} />
        </div>

        <div className="mt-12 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <h3 className="mt-0 text-[22px] font-semibold tracking-tight">Rooms</h3>
          <p className="text-[13px] text-[var(--dim)]">Click the work to go deeper</p>
        </div>
        <div className="rise mt-5 grid grid-cols-1 gap-8 sm:gap-10 lg:grid-cols-2 xl:grid-cols-3">
          {chambers.map((room) => (
            <RoomCard key={room.id} room={room} desks={desks} />
          ))}
        </div>
      </section>
    </>
  );
}
