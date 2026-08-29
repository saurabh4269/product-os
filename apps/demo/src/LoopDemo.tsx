import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import data from "../public/loop.json";

type Bundle = {
  investigation?: { id?: string; state?: string };
  hypotheses?: Array<{ statement?: string; confidence?: number }>;
  evidence?: Array<{ source_type?: string; claim?: string; independence_group?: string }>;
  actions?: Array<{ risk_tier?: string; consequence?: string }>;
  outcomes?: Array<{ verdict?: string; pre_value?: number; post_value?: number }>;
  lessons?: Array<{ statement?: string }>;
  signals?: Array<{ metric?: string; magnitude?: number }>;
};

const bundle = data as Bundle;

const SCENES = [
  {
    title: "Signal",
    body:
      bundle.signals?.[0]
        ? `Safari purchase conversion ${((bundle.signals[0].magnitude ?? 0) * 100).toFixed(1)}% vs baseline — detected unprompted.`
        : "Safari purchase conversion dropped. Detected unprompted from daily tables.",
  },
  {
    title: "Evidence",
    body: (bundle.evidence ?? [])
      .filter((e) => e.independence_group !== "github_untrusted")
      .map((e) => `${e.source_type}: ${e.independence_group}`)
      .join(" · ") || "analytics · logs · deploy",
  },
  {
    title: "Root cause",
    body: bundle.hypotheses?.[0]?.statement ?? "pay-sdk 4.3 Safari 3DS timeout",
  },
  {
    title: "HIGH approval",
    body: bundle.actions?.[0]?.consequence ?? "Rollback pay_sdk_4_3. No merge without a human.",
  },
  {
    title: "Verified",
    body: bundle.outcomes?.[0]
      ? `${bundle.outcomes[0].verdict}: Safari ${(Number(bundle.outcomes[0].pre_value) * 100).toFixed(1)}% → ${(Number(bundle.outcomes[0].post_value) * 100).toFixed(1)}%`
      : "Awaiting approval, then measured verification.",
  },
  {
    title: "Lesson",
    body: bundle.lessons?.[0]?.statement ?? "SDK upgrades need a Safari 3DS regression test.",
  },
];

export const LoopDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const scene = Math.min(SCENES.length - 1, Math.floor(frame / 60));
  const local = frame % 60;
  const opacity = interpolate(local, [0, 8, 50, 60], [0, 1, 1, 0], { extrapolateRight: "clamp" });
  const current = SCENES[scene];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: "#020617",
        color: "#F8FAFC",
        fontFamily: "Fira Sans, sans-serif",
        padding: 72,
      }}
    >
      <div style={{ fontFamily: "Fira Code, monospace", fontSize: 14, letterSpacing: "0.28em", color: "#16A34A" }}>
        LOOP · NORTHSTAR PAY
      </div>
      <div style={{ opacity, marginTop: 48 }}>
        <div style={{ fontSize: 18, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.16em" }}>
          {current.title}
        </div>
        <div style={{ fontSize: 36, lineHeight: 1.25, marginTop: 16, maxWidth: 1040 }}>{current.body}</div>
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 48,
          left: 72,
          right: 72,
          fontFamily: "Fira Code, monospace",
          fontSize: 12,
          color: "#64748B",
        }}
      >
        {bundle.investigation?.id ?? "investigation"} · real warehouse · no lorem
      </div>
    </AbsoluteFill>
  );
};
