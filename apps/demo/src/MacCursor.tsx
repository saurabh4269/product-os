import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export type CursorPoint = { x: number; y: number };

type MacCursorProps = {
  /** Normalized 0–1 position inside the window content area */
  position: CursorPoint;
  /** Local frame when click pulse happens */
  clickAt?: number;
  /** Local frame offset for entrance */
  localFrame: number;
  /** Window content offset from composition origin */
  windowOffset?: { left: number; top: number; width: number; height: number };
  visible?: boolean;
};

export const MacCursor: React.FC<MacCursorProps> = ({
  position,
  clickAt = 30,
  localFrame,
  windowOffset = { left: 180, top: 100, width: 920, height: 482 },
  visible = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const enter = spring({
    frame: localFrame,
    fps,
    config: { damping: 18, stiffness: 120 },
  });

  const x = windowOffset.left + position.x * windowOffset.width;
  const y = windowOffset.top + position.y * windowOffset.height;

  const clickPulse = interpolate(
    localFrame - clickAt,
    [-2, 0, 6, 14],
    [1, 0.82, 1.08, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    },
  );

  const ring =
    localFrame >= clickAt
      ? interpolate(localFrame - clickAt, [0, 18], [0.4, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 0;

  const opacity = visible ? interpolate(enter, [0, 1], [0, 1]) : 0;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        zIndex: 100,
        pointerEvents: "none",
        opacity,
        transform: `scale(${clickPulse}) translate(-4px, -2px)`,
        transformOrigin: "top left",
        filter: "drop-shadow(0 2px 6px rgba(0,0,0,0.25))",
      }}
    >
      {ring > 0 ? (
        <div
          style={{
            position: "absolute",
            left: -18,
            top: -18,
            width: 36,
            height: 36,
            borderRadius: "50%",
            border: "2px solid rgba(0,113,227,0.55)",
            opacity: ring,
            transform: `scale(${1 + (1 - ring) * 0.6})`,
          }}
        />
      ) : null}
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path
          d="M4 3L4 23L10.5 16.5L15 24L18.5 22.5L14 15L22 14L4 3Z"
          fill="#fff"
          stroke="#1d1d1f"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
      </svg>
      {/* Subtle breathing when idle */}
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          opacity: 0.15 + 0.05 * Math.sin(frame / 12),
        }}
      />
    </div>
  );
};

/** Ease cursor between two hotspots over local frames */
export function cursorBetween(
  localFrame: number,
  from: CursorPoint,
  to: CursorPoint,
  moveStart = 0,
  moveEnd = 20,
): CursorPoint {
  const t = interpolate(localFrame, [moveStart, moveEnd], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });
  return {
    x: from.x + (to.x - from.x) * t,
    y: from.y + (to.y - from.y) * t,
  };
}
