import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  Sequence,
  useCurrentFrame,
} from "remotion";
import { MacDesktop, MacWindow } from "./MacDesktop";
import { MacCursor, cursorBetween } from "./MacCursor";
import { MacScenePanel, SceneProgress, windowOpenOpacity, windowOpenScale } from "./MacScenePanels";
import { VoCaption } from "./VoCaption";
import { INVESTIGATION_ID, bundle } from "./demoData";
import { FPS, SCRIPT_BEATS, MACOS_DEMO_DURATION, beatOffsets } from "./script";

export { FPS, MACOS_DEMO_DURATION };

const WINDOW = { left: 180, top: 100, width: 920, height: 482 };
const OFFSETS = beatOffsets();

function EndCardBeat() {
  const frame = useCurrentFrame();
  const beat = SCRIPT_BEATS[SCRIPT_BEATS.length - 1];
  const opacity = interpolate(frame, [0, 14, beat.durationFrames - 10, beat.durationFrames], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [0, 16], [12, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <MacDesktop showDock={true} drift={false}>
      <div style={{ opacity, transform: `translateY(${y}px)`, textAlign: "center" }}>
        <div
          style={{
            width: 64,
            height: 64,
            margin: "0 auto 18px",
            borderRadius: 16,
            background: "linear-gradient(180deg, #3d9eff, #0071e3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 20,
            fontWeight: 700,
            color: "#fff",
            boxShadow: "0 12px 40px rgba(0,0,0,0.22)",
          }}
        >
          OS
        </div>
        <p
          style={{
            margin: 0,
            fontSize: 32,
            fontWeight: 600,
            color: "#fff",
            letterSpacing: "-0.02em",
            lineHeight: 1.35,
            textShadow: "0 2px 20px rgba(0,0,0,0.2)",
            maxWidth: 720,
          }}
        >
          {beat.caption}
        </p>
        <div
          style={{
            marginTop: 28,
            display: "inline-flex",
            padding: "11px 26px",
            borderRadius: 999,
            background: "#0071e3",
            color: "#fff",
            fontSize: 16,
            fontWeight: 600,
            boxShadow: "0 8px 28px rgba(0,113,227,0.45)",
          }}
        >
          productos.heisenbug.in
        </div>
      </div>
    </MacDesktop>
  );
}

function BeatScene({ beatIndex }: { beatIndex: number }) {
  const frame = useCurrentFrame();
  const beat = SCRIPT_BEATS[beatIndex];
  const prev = beatIndex > 0 ? SCRIPT_BEATS[beatIndex - 1] : null;
  const isColdOpen = beat.kind === "cold_open";

  const fadeIn = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(
    frame,
    [beat.durationFrames - 12, beat.durationFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const cursorPos = prev
    ? cursorBetween(frame, prev.hotspot, beat.hotspot, 0, Math.min(28, beat.durationFrames * 0.15))
    : cursorBetween(frame, { x: 0.55, y: 0.62 }, beat.hotspot, 0, 30);

  const winScale = isColdOpen ? windowOpenScale(frame) : 1;
  const winOpacity = isColdOpen ? windowOpenOpacity(frame) : 1;

  const showWindow = !isColdOpen || frame > 15;

  return (
    <MacDesktop showDock={isColdOpen && frame < 40}>
      {showWindow ? (
        <div
          style={{
            opacity: opacity * winOpacity,
            transform: `scale(${winScale})`,
            transformOrigin: "center center",
          }}
        >
          <MacWindow title={beat.windowTitle}>
            <MacScenePanel beat={beat} localFrame={frame} />
            {beat.kind !== "cold_open" && beat.kind !== "end_card" ? (
              <SceneProgress
                count={SCRIPT_BEATS.length - 1}
                active={beatIndex}
                localFrame={frame}
              />
            ) : null}
          </MacWindow>
        </div>
      ) : null}

      <MacCursor
        position={cursorPos}
        clickAt={beat.clickAt}
        localFrame={frame}
        windowOffset={WINDOW}
        visible={opacity > 0.15 && (showWindow || isColdOpen)}
      />

      <VoCaption text={beat.caption} localFrame={frame} durationFrames={beat.durationFrames} />

      {beat.kind !== "end_card" ? (
        <div
          style={{
            position: "absolute",
            bottom: 88,
            right: 56,
            fontSize: 10,
            color: "rgba(255,255,255,0.65)",
            fontFamily: "ui-monospace, monospace",
            opacity: 0.8 * opacity,
          }}
        >
          {INVESTIGATION_ID} · {bundle.investigation?.room_id ?? bundle.meta?.room_id ?? "room"}
        </div>
      ) : null}
    </MacDesktop>
  );
}

export const MacOsDemo: React.FC = () => {
  const storyBeats = SCRIPT_BEATS.filter((b) => b.kind !== "end_card");
  const endBeat = SCRIPT_BEATS[SCRIPT_BEATS.length - 1];

  return (
    <AbsoluteFill>
      {storyBeats.map((beat, i) => (
        <Sequence key={beat.kind} from={OFFSETS[i]} durationInFrames={beat.durationFrames}>
          <BeatScene beatIndex={i} />
        </Sequence>
      ))}
      <Sequence from={OFFSETS[SCRIPT_BEATS.length - 1]} durationInFrames={endBeat.durationFrames}>
        <EndCardBeat />
      </Sequence>
    </AbsoluteFill>
  );
};
