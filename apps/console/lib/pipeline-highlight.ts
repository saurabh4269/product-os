"use client";

import { useSyncExternalStore } from "react";

let highlightStage: string | null = null;
const listeners = new Set<() => void>();

export function setPipelineHighlight(stage: string | null) {
  if (highlightStage === stage) return;
  highlightStage = stage;
  listeners.forEach((l) => l());
}

export function getPipelineHighlight() {
  return highlightStage;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function usePipelineHighlight() {
  return useSyncExternalStore(subscribe, getPipelineHighlight, () => null);
}

/** Map pipeline stage → diagram node ids (mermaid / SVG). */
export const STAGE_NODE_IDS: Record<string, string[]> = {
  signal: ["signal", "stage_signal", "s1", "P1", "P3", "HUB", "SIG"],
  investigate: ["investigate", "stage_investigate", "fanout", "s2", "INV", "JOIN"],
  evidence: ["evidence", "stage_evidence", "join", "s3", "EV"],
  root_cause: ["root_cause", "stage_root_cause", "path", "s4"],
  code: ["code", "stage_code", "ship", "s6"],
  product: ["product", "stage_product"],
  experiment: ["experiment", "stage_experiment"],
  risk: ["risk", "stage_risk", "hitl", "s5", "H1"],
  approve: ["approve", "stage_approve", "hitl_gate", "s6", "YOU"],
  verify: ["verify", "stage_verify", "s7", "learn"],
  learn: ["learn", "stage_learn"],
  reviews: ["deny", "stage_deny", "reviews", "BLOCK", "EX"],
};
