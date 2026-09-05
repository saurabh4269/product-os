"use client";

import { useEffect, useMemo, useState } from "react";
import { api, hasAdminToken, tryConfig, tryGet, type OfficeSnapshot, type Room } from "@/lib/api";
import { isFirstVisit, recordVisit } from "@/lib/first-visit";
import { buildHomePulse } from "@/lib/home-pulse";
import { useGlobalWs } from "@/lib/use-global-ws";
import { useDebouncedWorldTick, useSlowWorldTick } from "@/lib/world-refresh";
import { ErrorState } from "@/components/ui";
import { CityMap } from "@/components/city-map";
import { HomeCommandBar } from "@/components/home-command-bar";
import { HomeBrief } from "@/components/home-brief";
import { HandoffGraph } from "@/components/handoff-graph";
import { HomeGlassBox, HomeLiveReceipts } from "@/components/home-glass-box";
import { LiveRoomsRail } from "@/components/live-rooms-rail";
import { SevenStepLoop } from "@/components/seven-step-loop";
import { ApprovalModal } from "@/components/approval-modal";
import { ConnectAdminCta } from "@/components/connect-admin-cta";
import { ProductFilmBanner } from "@/components/product-film-banner";

export default function HomePage() {
  const { tick, connection } = useGlobalWs();
  const worldTick = useDebouncedWorldTick(tick);
  const slowTick = useSlowWorldTick(tick);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [office, setOffice] = useState<OfficeSnapshot | null>(null);
  const [evalMode, setEvalMode] = useState(false);
  const [configLoaded, setConfigLoaded] = useState(false);
  const [fixtureSlugs, setFixtureSlugs] = useState<Set<string>>(new Set());
  const [err, setErr] = useState<string | null>(null);
  const [adminAuthRequired, setAdminAuthRequired] = useState(false);
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
    let cancelled = false;
    (async () => {
      try {
        const cfg = await tryConfig();
        if (cancelled) return;
        setEvalMode(cfg.eval_mode);
        setFixtureSlugs(new Set(cfg.fixture_scenarios ?? []));
        setConfigLoaded(true);
      } catch {
        if (!cancelled) setConfigLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const roomsRes = await tryGet(() => api.rooms());
        if (cancelled) return;
        setRooms(roomsRes.data?.rooms ?? []);
        setAdminAuthRequired((prev) => prev || roomsRes.authRequired);
        setErr(null);
      } catch (e) {
        if (!cancelled && hasAdminToken()) {
          setErr(e instanceof Error ? e.message : "API unreachable");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [worldTick]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [officeRes, statusRes] = await Promise.all([
          tryGet(() => api.office()),
          tryGet(() => api.status()),
        ]);
        if (cancelled) return;
        setOffice(officeRes.data);
        setStatus(statusRes.data);
        setAdminAuthRequired(
          (prev) => prev || officeRes.authRequired || statusRes.authRequired
        );
        setErr(null);
      } catch (e) {
        if (!cancelled) {
          if (!hasAdminToken()) {
            setAdminAuthRequired(true);
            setErr(null);
          } else {
            setErr(e instanceof Error ? e.message : "API unreachable");
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slowTick]);

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
      adminAuthRequired,
    });
  }, [visitReady, status, office, adminAuthRequired]);

  if (err && hasAdminToken()) return <ErrorState message={err} />;

  const desks = office?.desks ?? [];
  const handoffs = office?.handoffs ?? [];
  const live = connection === "live";

  const chambers = rooms.filter((r) => {
    const isFixture = r.scenario_id && fixtureSlugs.has(r.scenario_id);
    if (configLoaded && !evalMode && isFixture) return false;
    return Boolean(r.scenario_id) || ["review", "research", "ops", "incident", "opportunity"].includes(r.kind);
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
          liveMotion={live}
        />
        <HomeBrief pulse={pulse} onDismiss={() => setShowHint(false)} />
        {adminAuthRequired ? <ConnectAdminCta variant="overlay" /> : null}
        <HomeCommandBar
          pulse={pulse}
          evalMode={evalMode}
          className="absolute bottom-4 left-4 right-4 z-30 mx-auto max-w-4xl sm:bottom-6"
        />
      </section>

      <section id="work" className="page-pad space-y-8 bg-[#f5f5f7]">
        <div className="grid gap-6 lg:grid-cols-12 lg:items-start">
          <div className="space-y-6 lg:col-span-7">
            <HandoffGraph desks={desks} handoffs={handoffs} live={live} />
            <SevenStepLoop compact />
            <LiveRoomsRail rooms={chambers} desks={desks} />
          </div>
          <div className="lg:col-span-5">
            <HomeGlassBox />
          </div>
        </div>

        <HomeLiveReceipts className="border-t border-border pt-8" />
        <ProductFilmBanner className="border-t border-border pt-8" />
      </section>
    </>
  );
}
