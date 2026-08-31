"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { setPipelineHighlight } from "@/lib/pipeline-highlight";
import { useDemoWsBridge } from "@/lib/use-global-ws";

export type LoopStep = {
  n: number;
  short: string;
  label: string;
  detail: string;
  stage: string;
  altStages?: string[];
};

/** Tier A — seven-step product loop (demo narrator + homepage). */
export const LOOPS_STEPS: LoopStep[] = [
  {
    n: 1,
    short: "Signal",
    label: "Signal detected",
    detail: "Cove checkout drop or BQ anomaly",
    stage: "signal",
  },
  {
    n: 2,
    short: "Investigate",
    label: "Investigators fan out",
    detail: "Analytics · Logs · Deploy in parallel",
    stage: "investigate",
  },
  {
    n: 3,
    short: "Diagnose",
    label: "Evidence merged",
    detail: "Root cause from ≥3 sources",
    stage: "evidence",
    altStages: ["root_cause"],
  },
  {
    n: 4,
    short: "Decide",
    label: "BUG vs FEATURE",
    detail: "Fix path or experiment path",
    stage: "root_cause",
    altStages: ["code", "product", "experiment", "risk"],
  },
  {
    n: 5,
    short: "Approve",
    label: "Waiting on you",
    detail: "HIGH changes need your look",
    stage: "approve",
  },
  {
    n: 6,
    short: "Ship",
    label: "PR on Product Y",
    detail: "GitHub opened — OS never merges",
    stage: "code",
    altStages: ["verify"],
  },
  {
    n: 7,
    short: "Verify",
    label: "Verify & learn",
    detail: "Metric window → memory",
    stage: "verify",
    altStages: ["learn"],
  },
];

export const DEMO_CHAPTERS = LOOPS_STEPS.map((s) => ({ n: s.n, stage: s.stage, label: s.label }));

export type PendingApproval = {
  action_id: string;
  room_id?: string;
  investigation_id?: string;
  risk_tier?: string;
  consequence?: string;
  title?: string;
};

type DemoGuideContextValue = {
  active: boolean;
  roomId: string | null;
  highlightStage: string | null;
  fleetWorking: boolean;
  pendingApproval: PendingApproval | null;
  startDemo: (roomId?: string | null) => void;
  endDemo: () => void;
  setHighlightStage: (stage: string | null) => void;
  setFleetWorking: (on: boolean) => void;
  setPendingApproval: (payload: PendingApproval | null) => void;
  chapterIndex: number;
  flowRequest: number;
  requestFlowView: () => void;
};

const DemoGuideContext = createContext<DemoGuideContextValue | null>(null);

export function DemoGuideProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState(false);
  const [roomId, setRoomId] = useState<string | null>(null);
  const [highlightStage, setHighlightStage] = useState<string | null>(null);
  const [fleetWorking, setFleetWorking] = useState(false);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);
  const [flowRequest, setFlowRequest] = useState(0);

  const requestFlowView = useCallback(() => {
    setFlowRequest((n) => n + 1);
  }, []);

  const startDemo = useCallback((rid?: string | null) => {
    setActive(true);
    setRoomId(rid ?? null);
    setHighlightStage("signal");
    setPipelineHighlight("signal");
    setFleetWorking(true);
    setPendingApproval(null);
  }, []);

  const endDemo = useCallback(() => {
    setActive(false);
    setRoomId(null);
    setHighlightStage(null);
    setFleetWorking(false);
  }, []);

  const chapterIndex = useMemo(() => {
    if (!highlightStage) return 0;
    const i = LOOPS_STEPS.findIndex(
      (c) => c.stage === highlightStage || c.altStages?.includes(highlightStage)
    );
    return i >= 0 ? i : 0;
  }, [highlightStage]);

  const value = useMemo(
    () => ({
      active,
      roomId,
      highlightStage,
      fleetWorking,
      pendingApproval,
      startDemo,
      endDemo,
      setHighlightStage,
      setFleetWorking,
      setPendingApproval,
      chapterIndex,
      flowRequest,
      requestFlowView,
    }),
    [active, roomId, highlightStage, fleetWorking, pendingApproval, startDemo, endDemo, chapterIndex, flowRequest, requestFlowView]
  );

  useDemoWsBridge(value);

  return <DemoGuideContext.Provider value={value}>{children}</DemoGuideContext.Provider>;
}

export function useDemoGuide() {
  return useContext(DemoGuideContext);
}
