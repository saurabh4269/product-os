import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { MacDesktop } from "./MacDesktop";

const INK = "#1d1d1f";
const DIM = "rgba(255,255,255,0.78)";
const ACCENT = "#0071e3";

function fadeUp(frame: number, delay = 0) {
  const t = interpolate(frame - delay, [0, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const y = interpolate(frame - delay, [0, 18], [14, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return { opacity: t, transform: `translateY(${y}px)` };
}

const stops = ["Signal", "Room", "Outreach", "Diagnose", "Approve", "Verify"];

export const FilmTitle: React.FC = () => {
  const frame = useCurrentFrame();
  const mark = fadeUp(frame, 6);
  const title = fadeUp(frame, 12);
  const line = fadeUp(frame, 20);
  const rail = fadeUp(frame, 28);

  return (
    <MacDesktop showDock={false} drift={frame > 20}>
      <div
        style={{
          width: 880,
          padding: "48px 52px",
          borderRadius: 14,
          background: "rgba(255,255,255,0.88)",
          boxShadow: "0 24px 80px rgba(0,0,0,0.22), 0 2px 0 rgba(255,255,255,0.9) inset",
          border: "1px solid rgba(255,255,255,0.65)",
          backdropFilter: "blur(20px)",
        }}
      >
        <div style={{ ...mark, display: "flex", alignItems: "center", gap: 14, marginBottom: 28 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: "linear-gradient(180deg, #3d9eff, #0071e3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 14,
              fontWeight: 700,
              color: "#fff",
              boxShadow: "0 6px 20px rgba(0,113,227,0.35)",
            }}
          >
            OS
          </div>
          <span style={{ fontSize: 20, fontWeight: 600, letterSpacing: "-0.02em", color: INK }}>Product OS</span>
        </div>
        <h1
          style={{
            ...title,
            margin: 0,
            fontSize: 52,
            fontWeight: 600,
            lineHeight: 1.08,
            letterSpacing: "-0.03em",
            maxWidth: 720,
            color: INK,
          }}
        >
          Your product team, watching the numbers.
        </h1>
        <p style={{ ...line, margin: "20px 0 0", fontSize: 22, color: "#3c3c43", maxWidth: 620, lineHeight: 1.45 }}>
          Observe → rooms → specialists → human approve → tenant PR. One campus, one loop.
        </p>
        <div style={{ ...rail, marginTop: 32, display: "flex", gap: 10, flexWrap: "wrap" }}>
          {stops.map((s) => (
            <span
              key={s}
              style={{
                padding: "8px 16px",
                borderRadius: 999,
                background: "rgba(0,0,0,0.04)",
                border: "1px solid rgba(0,0,0,0.06)",
                fontSize: 15,
                fontWeight: 500,
                color: INK,
              }}
            >
              {s}
            </span>
          ))}
        </div>
      </div>
    </MacDesktop>
  );
};

export const FilmEnd: React.FC = () => {
  const frame = useCurrentFrame();
  const block = fadeUp(frame, 8);
  const cta = fadeUp(frame, 18);

  return (
    <MacDesktop showDock={true} drift={false}>
      <div
        style={{
          textAlign: "center",
          color: "#fff",
          textShadow: "0 2px 24px rgba(0,0,0,0.22)",
        }}
      >
        <p
          style={{
            ...block,
            margin: 0,
            fontSize: 56,
            fontWeight: 600,
            letterSpacing: "-0.03em",
            lineHeight: 1.1,
          }}
        >
          Start on campus.
        </p>
        <p style={{ ...cta, margin: "20px 0 0", fontSize: 24, color: DIM }}>
          Observe. Investigate. Gate. Ship. Measure. Remember.
        </p>
        <div
          style={{
            ...cta,
            marginTop: 36,
            padding: "14px 30px",
            borderRadius: 999,
            background: ACCENT,
            color: "#fff",
            fontSize: 20,
            fontWeight: 600,
            display: "inline-block",
            boxShadow: "0 8px 28px rgba(0,113,227,0.45)",
          }}
        >
          productos.heisenbug.in
        </div>
      </div>
    </MacDesktop>
  );
};
