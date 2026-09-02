"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type OfficeSnapshot, type Room } from "@/lib/api";
import { DemoGuideProvider, useDemoGuide } from "@/lib/demo-guide-context";
import { isFirstVisit, recordVisit } from "@/lib/first-visit";
import { buildHomePulse } from "@/lib/home-pulse";
import { useGlobalWs } from "@/lib/use-global-ws";
import { ErrorState } from "@/components/ui";
import { CityMap } from "@/components/city-map";
import { HomeCommandBar } from "@/components/home-command-bar";
import { HomeBrief } from "@/components/home-brief";
import { PipelineBoard } from "@/components/pipeline-board";
import { LiveWorkBoard } from "@/components/live-work-board";
import { ActivityLog } from "@/components/activity-log";
import { SevenStepLoop } from "@/components/seven-step-loop";
import { ApprovalModal } from "@/components/approval-modal";
import { GuidedDemoStrip } from "@/components/guided-demo-strip";

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
  const [evalMode, setEvalMode] = useState(true);
  const [fixtureSlugs, setFixtureSlugs] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [status, setStatus] = useState<Awaited<ReturnType<typeof api.status>> | null>(null);
  const [visitReady, setVisitReady] = useState(false);

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
    Promise.all([api.rooms(), api.office(), api.config(), api.status()])
      .then(([r, o, cfg, st]) => {
        setRooms(r.rooms);
        setOffice(o);
        setEvalMode(cfg.eval_mode);
        setFixtureSlugs(new Set(cfg.fixture_scenarios ?? []));
        setStatus(st);
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
  const chambers = rooms.filter((r) => {
    const isFixture = r.scenario_id && fixtureSlugs.has(r.scenario_id);
    if (!evalMode && isFixture) return false;
    return Boolean(r.scenario_id) || ["review", "research", "ops"].includes(r.kind);
  });

  function walkInside(_district: string) {
    window.requestAnimationFrame(() => {
      document.getElementById("work")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  return (
    <>
      <ApprovalModal />

      <section className="relative border-b border-border">
        <CityMap
          hero
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
        <HomeCommandBar
          pulse={pulse}
          evalMode={evalMode}
          className="absolute bottom-4 left-4 right-4 z-30 mx-auto max-w-4xl sm:bottom-6"
        />
      </section>

      <section id="work" className="page-pad border-b border-border bg-[#F8FAFC]">
        <SevenStepLoop activeStage={demo?.highlightStage} compact className="mt-0" />

        {demo?.active ? <GuidedDemoStrip className="mt-4" /> : null}

        <LiveWorkBoard subtitle={pulse?.pipelineSubtitle} className="mt-10" />

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
      </section>
    </>
  );
}
