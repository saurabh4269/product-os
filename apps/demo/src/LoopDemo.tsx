import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import data from "../public/loop.json";

type Scene = { title: string; body: string };

type DemoPayload = {
  meta?: { pipeline?: string; exported_at?: string };
  scenes?: Scene[];
  investigation?: { id?: string; state?: string; loop_type?: string };
};

const payload = data as DemoPayload;

const SCENES: Scene[] =
  payload.scenes && payload.scenes.length > 0
    ? payload.scenes
    : [
        {
          title: "Export required",
          body: "Run python3 -m loop.cli export-demo to generate loop.json from the live pipeline.",
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
        {payload.investigation?.id ?? "investigation"} · {payload.meta?.pipeline ?? "generic"} · real pipeline
      </div>
    </AbsoluteFill>
  );
};
