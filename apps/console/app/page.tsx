"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type OfficeSnapshot, type Room } from "@/lib/api";
import { DemoGuideProvider, useDemoGuide } from "@/lib/demo-guide-context";
import { pct } from "@/lib/utils";
import { ErrorState } from "@/components/ui";
import { CityMap } from "@/components/city-map";
import { HomeCommandBar } from "@/components/home-command-bar";
import { IsoOffice } from "@/components/iso-office";
import { OfficeFloor } from "@/components/office-floor";
import { RoomCard } from "@/components/work-flipbook";
import { PipelineBoard } from "@/components/pipeline-board";
import { ActivityLog } from "@/components/activity-log";
import { SevenStepLoop } from "@/components/seven-step-loop";
import { ApprovalModal } from "@/components/approval-modal";
import { GuidedDemoStrip } from "@/components/guided-demo-strip";
import Link from "next/link";

function magLabel(raw: unknown) {
  const n = Number(raw);
  if (Number.isNaN(n)) return "—";
  return Math.abs(n) > 1 ? String(Math.round(n)) : pct(n);
}

export default function HomePage() {
  return (
    <DemoGuideProvider>
      <HomeContent />
    </DemoGuideProvider>
  );
}

function HomeContent() {
  const demo = useDemoGuide();
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
      <ApprovalModal />

      {/* Campus hero — visual first, agents on the map */}
      <section className="relative border-b border-border">
        <CityMap
          hero
          rooms={chambers}
          desks={desks}
          handoffs={handoffs}
          picked={picked}
          onPick={(id) => setPicked(id)}
          onWalkInside={walkInside}
        />
        <HomeCommandBar className="absolute bottom-4 left-4 right-4 z-30 mx-auto max-w-4xl sm:bottom-6" />
      </section>

      {/* Work panel — pipeline + live feed */}
      <section id="work" className="page-pad border-b border-border bg-background">
        {demo?.active ? (
          <>
            <GuidedDemoStrip />
            <SevenStepLoop activeStage={demo.highlightStage} compact className="mt-4" />
          </>
        ) : null}
        <PipelineBoard />
        <ActivityLog
          roomId={demo?.active && demo.roomId ? demo.roomId : undefined}
          defaultScope={demo?.active && demo.roomId ? "room" : "all"}
          defaultOpen={false}
          compact
        />
      </section>

      {/* Office floor — tap through to rooms */}
      <section className="page-pad bg-[var(--floor)]">
        {signals.length > 0 ? (
          <div className="mb-8 flex flex-wrap gap-3">
            {signals.slice(0, 4).map((s) => {
              const segs =
                (s.affected_segments as Array<{ browser?: string; os?: string; platform?: string; geo?: string }>) ??
                [];
              const who = segs[0]?.browser || segs[0]?.os || segs[0]?.platform || segs[0]?.geo || "all";
              return (
                <div
                  key={String(s.id)}
                  className="rounded-xl border border-border bg-white px-4 py-2.5 shadow-sm"
                >
                  <p className="text-[11px] text-[var(--faint)]">
                    {String(s.metric).replace(/_/g, " ")} · {who}
                  </p>
                  <p className="text-[18px] font-semibold tracking-tight">{magLabel(s.magnitude)}</p>
                </div>
              );
            })}
          </div>
        ) : null}

        <div id="inside" className="scroll-mt-6">
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

        <div className="mt-10">
          <OfficeFloor desks={desks} handoffs={handoffs} working={office?.working ?? 0} />
        </div>

        <div className="mt-10 flex items-end justify-between gap-2">
          <h3 className="text-[20px] font-semibold tracking-tight">Rooms</h3>
          <Link href="/labs" className="text-[12px] text-accent hover:underline">
            Fixtures
          </Link>
        </div>
        <div className="rise mt-4 grid grid-cols-1 gap-6 sm:gap-8 lg:grid-cols-2 xl:grid-cols-3">
          {chambers.map((room) => (
            <RoomCard key={room.id} room={room} desks={desks} />
          ))}
        </div>
      </section>
    </>
  );
}