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
import { MacScenePanel, SceneProgress } from "./MacScenePanels";
import { MAC_SCENES, INVESTIGATION_ID, LOOP_CHIP, bundle } from "./demoData";

export const FPS = 30;
export const FRAMES_PER_SCENE = 80;
export const INTRO_FRAMES = 50;
export const OUTRO_FRAMES = 60;
export const MACOS_DEMO_DURATION =
  INTRO_FRAMES + MAC_SCENES.length * FRAMES_PER_SCENE + OUTRO_FRAMES;

const WINDOW = { left: 180, top: 100, width: 920, height: 482 };

function IntroBeat() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 12, INTRO_FRAMES - 10, INTRO_FRAMES], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [0, 18], [20, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const scale = interpolate(frame, [0, 18], [0.96, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <MacDesktop showDock={false} drift={false}>
      <div
        style={{
          opacity,
          transform: `translateY(${y}px) scale(${scale})`,
          textAlign: "center",
          color: "#fff",
          textShadow: "0 2px 24px rgba(0,0,0,0.25)",
        }}
      >
        <div
          style={{
            width: 72,
            height: 72,
            margin: "0 auto 20px",
            borderRadius: 18,
            background: "linear-gradient(180deg, #3d9eff, #0071e3)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 22,
            fontWeight: 700,
            boxShadow: "0 12px 40px rgba(0,0,0,0.25)",
          }}
        >
          OS
        </div>
        <h1
          style={{
            margin: 0,
            fontSize: 48,
            fontWeight: 600,
            letterSpacing: "-0.03em",
          }}
        >
          Product OS
        </h1>
        <p style={{ margin: "12px 0 0", fontSize: 20, opacity: 0.88, fontWeight: 400 }}>
          Autonomous loop · observe to verify
        </p>
        <div
          style={{
            marginTop: 20,
            display: "inline-flex",
            padding: "6px 14px",
            borderRadius: 999,
            background: "rgba(255,255,255,0.22)",
            border: "1px solid rgba(255,255,255,0.35)",
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          {LOOP_CHIP}
        </div>
      </div>
    </MacDesktop>
  );
}

function OutroBeat() {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 14, OUTRO_FRAMES - 12, OUTRO_FRAMES], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });
  const y = interpolate(frame, [0, 16], [16, 0], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <MacDesktop showDock={true} drift={false}>
      <div style={{ opacity, transform: `translateY(${y}px)`, textAlign: "center" }}>
        <p
          style={{
            margin: 0,
            fontSize: 36,
            fontWeight: 600,
            color: "#fff",
            letterSpacing: "-0.02em",
            textShadow: "0 2px 20px rgba(0,0,0,0.2)",
          }}
        >
          Start on campus.
        </p>
        <p style={{ margin: "14px 0 0", fontSize: 18, color: "rgba(255,255,255,0.85)" }}>
          Connect your product · one loop
        </p>
        <div
          style={{
            marginTop: 28,
            display: "inline-flex",
            padding: "12px 28px",
            borderRadius: 999,
            background: "#0071e3",
            color: "#fff",
            fontSize: 17,
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

function StoryScene({ sceneIndex }: { sceneIndex: number }) {
  const frame = useCurrentFrame();
  const scene = MAC_SCENES[sceneIndex];
  const prev = sceneIndex > 0 ? MAC_SCENES[sceneIndex - 1] : null;

  const fadeIn = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: "clamp" });
  const fadeOut = interpolate(
    frame,
    [FRAMES_PER_SCENE - 10, FRAMES_PER_SCENE],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  const cursorPos = prev
    ? cursorBetween(frame, prev.hotspot, scene.hotspot, 0, 22)
    : cursorBetween(frame, { x: 0.5, y: 0.7 }, scene.hotspot, 0, 22);

  const windowTitle =
    scene.kind === "room"
      ? "Room · parallel specialists"
      : scene.kind === "approve"
        ? "Approvals"
        : "Product OS";

  return (
    <MacDesktop>
      <div style={{ opacity }}>
        <MacWindow title={windowTitle}>
          <MacScenePanel scene={scene} localFrame={frame} />
          <SceneProgress count={MAC_SCENES.length} active={sceneIndex} localFrame={frame} />
        </MacWindow>
      </div>
      <MacCursor
        position={cursorPos}
        clickAt={scene.clickAt}
        localFrame={frame}
        windowOffset={WINDOW}
        visible={opacity > 0.2}
      />
      <div
        style={{
          position: "absolute",
          bottom: 88,
          right: 56,
          fontSize: 11,
          color: "rgba(255,255,255,0.75)",
          fontFamily: "ui-monospace, monospace",
          opacity: 0.85 * opacity,
        }}
      >
        {INVESTIGATION_ID} · {bundle.meta?.pipeline ?? "generic"}
      </div>
    </MacDesktop>
  );
}

export const MacOsDemo: React.FC = () => {
  let offset = 0;

  return (
    <AbsoluteFill>
      <Sequence from={offset} durationInFrames={INTRO_FRAMES}>
        <IntroBeat />
      </Sequence>
      {offset += INTRO_FRAMES}

      {MAC_SCENES.map((_, i) => {
        const from = offset + i * FRAMES_PER_SCENE;
        return (
          <Sequence key={i} from={from} durationInFrames={FRAMES_PER_SCENE}>
            <StoryScene sceneIndex={i} />
          </Sequence>
        );
      })}
      {offset += MAC_SCENES.length * FRAMES_PER_SCENE}

      <Sequence from={offset} durationInFrames={OUTRO_FRAMES}>
        <OutroBeat />
      </Sequence>
    </AbsoluteFill>
  );
};
