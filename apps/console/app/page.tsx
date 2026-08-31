"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api, type OfficeSnapshot, type Room } from "@/lib/api";
import { DemoGuideProvider, useDemoGuide } from "@/lib/demo-guide-context";
import { isFirstVisit, recordVisit } from "@/lib/first-visit";
import { buildHomePulse } from "@/lib/home-pulse";
import { useGlobalWs } from "@/lib/use-global-ws";
import { dedupeSignals, signalSegmentLabel } from "@/lib/signals";
import { pct } from "@/lib/utils";
import { ErrorState } from "@/components/ui";
import { CityMap } from "@/components/city-map";
import { HomeCommandBar } from "@/components/home-command-bar";
import { HomeBrief } from "@/components/home-brief";
import { IsoOffice } from "@/components/iso-office";
import { OfficeFloor } from "@/components/office-floor";
import { RoomCard } from "@/components/work-flipbook";
import { PipelineBoard } from "@/components/pipeline-board";
import { LiveWorkBoard } from "@/components/live-work-board";
import { ProofStrip, type ProofPayload } from "@/components/proof-embed";
import { ActivityLog } from "@/components/activity-log";
import { SevenStepLoop } from "@/components/seven-step-loop";
import { ApprovalModal } from "@/components/approval-modal";
import { GuidedDemoStrip } from "@/components/guided-demo-strip";
import { ExploreSection } from "@/components/explore-section";
import { AgentFleetPanel } from "@/components/agent-fleet-panel";
import { DataFeedPanel } from "@/components/data-feed-panel";
import { WorkflowLinksPanel } from "@/components/workflow-links";
import Link from "next/link";

function magLabel(raw: unknown) {
  const n = Number(raw);
  if (Number.isNaN(n)) return "";
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
  const { tick } = useGlobalWs();
  const [rooms, setRooms] = useState<Room[]>([]);
  const [office, setOffice] = useState<OfficeSnapshot | null>(null);
  const [signals, setSignals] = useState<Array<Record<string, unknown>>>([]);
  const [evalMode, setEvalMode] = useState(true);
  const [fixtureSlugs, setFixtureSlugs] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [inside, setInside] = useState<string | null>(null);
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.status>> | null>(null);
  const [visitReady, setVisitReady] = useState(false);
  const [proof, setProof] = useState<{
    warehouse?: ProofPayload | null;
    github?: ProofPayload | null;
    ga4?: ProofPayload | null;
    cards?: ProofPayload[];
  } | null>(null);
  const router = useRouter();

  const [showHint, setShowHint] = useState(false);

  useEffect(() => {
    recordVisit();
    setVisitReady(true);
    setShowHint(isFirstVisit());
  }, []);

  useEffect(() => {
    if (demo?.active) setShowHint(false);
  }, [demo?.active]);

  useEffect(() => {
    Promise.all([api.rooms(), api.signals(), api.office(), api.config(), api.status(), api.proof()])
      .then(([r, s, o, cfg, st, pf]) => {
        setRooms(r.rooms);
        setSignals(s.signals);
        setOffice(o);
        setEvalMode(cfg.eval_mode);
        setFixtureSlugs(new Set(cfg.fixture_scenarios ?? []));
        setStatus(st);
        setProof({
          warehouse: (pf.warehouse as ProofPayload) || null,
          github: (pf.github as ProofPayload) || null,
          ga4: (pf.ga4 as ProofPayload) || null,
          cards: ((pf.cards || []) as ProofPayload[]).filter((c) => c && c.kind),
        });
        setErr(null);
      })
      .catch((e) => setErr(e instanceof Error ? e.message : "API unreachable"));
  }, [tick]);

  const pulse = useMemo(() => {
    if (!visitReady) return null;
    const workingAgents = office?.desks?.filter((d) => d.status !== "idle").length ?? 0;
    return buildHomePulse({
      open: status?.rooms?.open,
      waiting: status?.approvals_pending ?? status?.funnel?.approve,
      inFlight: status?.engaged,
      workingAgents,
      verified: status?.verified,
      lessons: status?.funnel?.learn,
      workspaceConnected: status?.workspace?.connected,
    });
  }, [visitReady, status, office]);

  if (err) return <ErrorState message={err} />;

  const desks = office?.desks ?? [];
  const handoffs = office?.handoffs ?? [];
  const workingCount = office?.working ?? 0;
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

      {/* Campus — context map, not the whole dashboard */}
      <section className="relative border-b border-border">
        <CityMap
          hero
          compactHero
          showTapHint={showHint && !picked && !pulse?.campusLine}
          campusLine={pulse?.campusLine}
          campusHot={pulse?.campusHot}
          rooms={chambers}
          desks={desks}
          handoffs={handoffs}
          picked={picked}
          onPick={(id) => setPicked(id)}
          onWalkInside={walkInside}
          liveMotion={Boolean(demo?.active)}
        />
        <HomeBrief pulse={pulse} onDismiss={() => setShowHint(false)} />
        <HomeCommandBar pulse={pulse} className="absolute bottom-4 left-4 right-4 z-30 mx-auto max-w-4xl sm:bottom-6" />
      </section>

      {/* Manager desk — live work, not architecture */}
      <section id="work" className="page-pad border-b border-border bg-background">
        <SevenStepLoop activeStage={demo?.highlightStage} compact className="mt-0" />

        {demo?.active ? (
          <>
            <GuidedDemoStrip className="mt-4" />
          </>
        ) : null}

        <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <AgentFleetPanel desks={desks} handoffs={handoffs} />
          <DataFeedPanel desks={desks} />
        </div>

        <LiveWorkBoard subtitle={pulse?.pipelineSubtitle} className="mt-10" />

        {proof ? (
          <div className="mt-8">
            <div className="mb-3 flex items-end justify-between gap-3">
              <div>
                <h2 className="text-[18px] font-semibold tracking-tight">Live sources</h2>
                <p className="mt-0.5 text-[13px] text-[var(--dim)]">
                  Same data the agents read. Open the real console when you want the full tool.
                </p>
              </div>
            </div>
            <ProofStrip
              warehouse={proof.warehouse}
              github={proof.github}
              ga4={proof.ga4}
              cards={proof.cards}
            />
          </div>
        ) : null}

        <details className="mt-8 group">
          <summary className="cursor-pointer list-none text-[13px] font-medium text-[var(--dim)] hover:text-foreground">
            Stage board
            <span className="ml-2 text-[12px] font-normal text-[var(--faint)] group-open:hidden">show</span>
          </summary>
          <PipelineBoard className="mt-4" />
        </details>

        <ActivityLog
          key={demo?.active ? "demo-on" : "demo-off"}
          roomId={demo?.active && demo.roomId ? demo.roomId : undefined}
          defaultScope={demo?.active && demo.roomId ? "room" : "all"}
          defaultOpen={false}
          className="mt-8"
        />

        <WorkflowLinksPanel compact className="mt-8" />
      </section>

      {/* Campus detail — rooms & iso floor */}
      <section className="page-pad bg-[var(--floor)]">
        <ExploreSection demoActive={demo?.active || workingCount > 0} defaultOpen={workingCount > 0}>
          {signals.length > 0 ? (
            <div className="mb-8 flex flex-wrap gap-3">
              {dedupeSignals(signals).slice(0, 4).map((s) => (
                <div key={String(s.id)} className="surface px-4 py-2.5">
                  <p className="text-[11px] text-[var(--faint)]">
                    {String(s.metric).replace(/_/g, " ")} · {signalSegmentLabel(s)}
                  </p>
                  <p className="text-[18px] font-semibold tracking-tight">{magLabel(s.magnitude)}</p>
                </div>
              ))}
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
            <OfficeFloor desks={desks} handoffs={handoffs} working={workingCount} activeOnlyDefault />
          </div>

          <div className="mt-10 flex items-end justify-between gap-2">
            <h3 className="text-[20px] font-semibold tracking-tight">Rooms</h3>
            <Link href="/labs" className="text-[12px] text-accent">
              Fixtures →
            </Link>
          </div>
          <div className="rise mt-4 grid grid-cols-1 gap-6 sm:gap-8 lg:grid-cols-2 xl:grid-cols-3">
            {chambers.map((room) => (
              <RoomCard key={room.id} room={room} desks={desks} />
            ))}
          </div>
        </ExploreSection>
      </section>
    </>
  );
}
