import React from "react";
import { Easing, interpolate } from "remotion";

type VoCaptionProps = {
  text: string;
  localFrame: number;
  durationFrames: number;
};

/** Subtle bottom caption aligned to VO — not shouty subtitles */
export const VoCaption: React.FC<VoCaptionProps> = ({ text, localFrame, durationFrames }) => {
  const fadeIn = interpolate(localFrame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const fadeOut = interpolate(
    localFrame,
    [durationFrames - 14, durationFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
  );
  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <div
      style={{
        position: "absolute",
        bottom: 52,
        left: "50%",
        transform: "translateX(-50%)",
        width: "min(880px, 92%)",
        opacity,
        zIndex: 50,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          padding: "14px 22px",
          borderRadius: 12,
          background: "rgba(0,0,0,0.52)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255,255,255,0.12)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.2)",
        }}
      >
        <p
          style={{
            margin: 0,
            fontSize: 17,
            lineHeight: 1.45,
            fontWeight: 400,
            color: "rgba(255,255,255,0.92)",
            letterSpacing: "-0.01em",
            textAlign: "center",
          }}
        >
          {text}
        </p>
      </div>
    </div>
  );
};
