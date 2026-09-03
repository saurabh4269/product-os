import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import data from "../public/loop.json";

type Scene = { title: string; body: string };

type Bundle = {
  meta?: { pipeline?: string; exported_at?: string };
  investigation?: { id?: string; state?: string; recalled_lessons?: string[] };
  signals?: Array<{ metric?: string; magnitude?: number; baseline?: number }>;
  evidence?: Array<{ independence_group?: string; trust_level?: string }>;
  hypotheses?: Array<{ statement?: string }>;
  actions?: Array<{ risk_tier?: string; consequence?: string; tier_rationale?: string }>;
  outcomes?: Array<{ verdict?: string; metric?: string; pre_value?: number; post_value?: number }>;
  lessons?: Array<{ statement?: string }>;
};

const bundle = data as Bundle;

const WAITING = {
  signal: "Signal stage is waiting — no metric from the pipeline yet.",
  evidence: "Evidence stage is waiting — specialists have not grouped sources yet.",
  rootCause: "Root cause stage is waiting — hypothesis not locked yet.",
  approval: "Approval stage is waiting — no HIGH consequence drafted yet.",
  verified: "Verify stage is waiting — outcome not measured yet.",
  lesson: "Memory stage is waiting — lesson not captured yet.",
} as const;

function buildScenes(payload: Bundle): Scene[] {
  const sig = payload.signals?.[0];
  const signalBody =
    sig?.metric != null
      ? `${sig.metric} moved ${((sig.magnitude ?? 0) * 100).toFixed(1)}% vs baseline ${((sig.baseline ?? 0) * 100).toFixed(1)}% — detected from the pipeline.`
      : WAITING.signal;

  const groups = [
    ...new Set(
      (payload.evidence ?? [])
        .filter((e) => (e.trust_level ?? "trusted") !== "untrusted")
        .map((e) => e.independence_group)
        .filter((g): g is string => Boolean(g)),
    ),
  ].sort();
  const evidenceBody =
    groups.length > 0
      ? `Parallel specialists · ${groups.slice(0, 6).join(" · ")}. Three-source gate before root cause.`
      : WAITING.evidence;

  const hypothesis = payload.hypotheses?.[0]?.statement;
  const rootBody = hypothesis ?? WAITING.rootCause;

  const highAction = (payload.actions ?? []).find((a) => (a.risk_tier ?? "").toUpperCase() === "HIGH");
  const approvalBody =
    highAction?.consequence ?? highAction?.tier_rationale ?? WAITING.approval;

  const outcome = payload.outcomes?.[0];
  const verifiedBody =
    outcome?.verdict && outcome.verdict.toUpperCase() !== "NOT_RESOLVED"
      ? `${outcome.verdict}: ${outcome.metric ?? "metric"} ${Number(outcome.pre_value ?? 0).toPrecision(3)} → ${Number(outcome.post_value ?? 0).toPrecision(3)}.`
      : WAITING.verified;

  const lessonBody = payload.lessons?.[0]?.statement ?? WAITING.lesson;

  return [
    { title: "Signal", body: signalBody },
    { title: "Evidence", body: evidenceBody },
    { title: "Root cause", body: rootBody },
    { title: "HIGH approval", body: approvalBody },
    { title: "Verified", body: verifiedBody },
    { title: "Lesson", body: lessonBody },
  ];
}

const SCENES = buildScenes(bundle);

export const LoopDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const scene = Math.min(SCENES.length - 1, Math.floor(frame / 60));
  const local = frame % 60;
  const opacity = interpolate(local, [0, 8, 50, 60], [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const current = SCENES[scene];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#f5f5f7",
        color: "#1d1d1f",
        fontFamily: "Inter, system-ui, sans-serif",
        padding: 72,
      }}
    >
      <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 14, letterSpacing: "0.2em", color: "#0071e3" }}>
        LOOP · PRODUCT OS
      </div>
      <div style={{ opacity, marginTop: 48 }}>
        <div style={{ fontSize: 18, color: "#6e6e73", textTransform: "uppercase", letterSpacing: "0.12em" }}>
          {current.title}
        </div>
        <div style={{ fontSize: 34, lineHeight: 1.28, marginTop: 16, maxWidth: 1040, fontWeight: 500 }}>
          {current.body}
        </div>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 48,
          left: 72,
          right: 72,
          fontFamily: "ui-monospace, monospace",
          fontSize: 12,
          color: "#86868b",
        }}
      >
        {bundle.investigation?.id ?? "investigation"} · {bundle.meta?.pipeline ?? "generic"} · real pipeline
      </div>
    </AbsoluteFill>
  );
};
