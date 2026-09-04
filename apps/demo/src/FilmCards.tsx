import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

const INK = "#1d1d1f";
const MIST = "#f5f5f7";
const CAMPUS = "#eef2ee";
const ACCENT = "#0071e3";
const DIM = "#6e6e73";

function fadeUp(frame: number, fps: number, delay = 0) {
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

const stops = ["Campus", "Room", "Diagnose", "Approve", "Ship"];

export const FilmTitle: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const mark = fadeUp(frame, fps, 6);
  const title = fadeUp(frame, fps, 12);
  const line = fadeUp(frame, fps, 20);
  const rail = fadeUp(frame, fps, 28);

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(165deg, ${MIST} 0%, ${CAMPUS} 48%, ${MIST} 100%)`,
        fontFamily: '"Inter", system-ui, sans-serif',
        color: INK,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          opacity: 0.35,
          background:
            "radial-gradient(ellipse 80% 60% at 72% 18%, rgba(0,113,227,0.12), transparent 60%)",
        }}
      />
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 120px",
          height: "100%",
          maxWidth: 1200,
        }}
      >
        <div style={{ ...mark, display: "flex", alignItems: "center", gap: 16, marginBottom: 36 }}>
          <div
            style={{
              width: 52,
              height: 52,
              borderRadius: 14,
              background: "#fff7e8",
              border: "1px solid rgba(0,0,0,0.06)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 15,
              fontWeight: 700,
              color: ACCENT,
            }}
          >
            OS
          </div>
          <span style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em" }}>Product OS</span>
        </div>
        <h1
          style={{
            ...title,
            margin: 0,
            fontFamily: '"Georgia", "Times New Roman", serif',
            fontSize: 72,
            fontWeight: 500,
            lineHeight: 1.05,
            letterSpacing: "-0.03em",
            maxWidth: 900,
          }}
        >
          Your product team, watching the numbers.
        </h1>
        <p style={{ ...line, margin: "28px 0 0", fontSize: 26, color: DIM, maxWidth: 720, lineHeight: 1.45 }}>
          Observe → rooms → specialists → human approve → tenant PR. One campus, one loop.
        </p>
        <div style={{ ...rail, marginTop: 48, display: "flex", gap: 14, flexWrap: "wrap" }}>
          {stops.map((s) => (
            <span
              key={s}
              style={{
                padding: "10px 18px",
                borderRadius: 999,
                background: "rgba(255,255,255,0.72)",
                border: "1px solid rgba(0,0,0,0.06)",
                fontSize: 18,
                fontWeight: 500,
                color: INK,
              }}
            >
              {s}
            </span>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const FilmEnd: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const block = fadeUp(frame, fps, 8);
  const cta = fadeUp(frame, fps, 18);

  return (
    <AbsoluteFill
      style={{
        background: INK,
        fontFamily: '"Inter", system-ui, sans-serif',
        color: MIST,
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          textAlign: "center",
          padding: "0 80px",
        }}
      >
        <p
          style={{
            ...block,
            margin: 0,
            fontFamily: '"Georgia", "Times New Roman", serif',
            fontSize: 64,
            fontWeight: 500,
            letterSpacing: "-0.03em",
            lineHeight: 1.1,
          }}
        >
          Start on campus.
        </p>
        <p style={{ ...cta, margin: "24px 0 0", fontSize: 28, color: "rgba(245,245,247,0.72)" }}>
          Two minutes to Connect Product Y.
        </p>
        <div
          style={{
            ...cta,
            marginTop: 40,
            padding: "16px 32px",
            borderRadius: 999,
            background: ACCENT,
            color: "#fff",
            fontSize: 22,
            fontWeight: 600,
          }}
        >
          productos.heisenbug.in
        </div>
      </div>
    </AbsoluteFill>
  );
};
