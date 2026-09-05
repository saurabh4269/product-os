import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

const WALLPAPER =
  "radial-gradient(ellipse 120% 80% at 20% 10%, #c8d8f0 0%, transparent 55%), " +
  "radial-gradient(ellipse 90% 70% at 85% 20%, #e8c4d8 0%, transparent 50%), " +
  "linear-gradient(145deg, #8eb5e8 0%, #b8a4d4 38%, #d4c4e8 62%, #a8c8e8 100%)";

type MacDesktopProps = {
  children: React.ReactNode;
  showDock?: boolean;
  /** Subtle parallax drift on wallpaper */
  drift?: boolean;
};

export const MacDesktop: React.FC<MacDesktopProps> = ({
  children,
  showDock = true,
  drift = true,
}) => {
  const frame = useCurrentFrame();
  const driftX = drift ? interpolate(frame % 180, [0, 90, 180], [0, 6, 0]) : 0;
  const driftY = drift ? interpolate(frame % 240, [0, 120, 240], [0, -4, 0]) : 0;

  return (
    <AbsoluteFill
      style={{
        background: WALLPAPER,
        fontFamily:
          '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Inter, system-ui, sans-serif',
        color: "#1d1d1f",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `translate(${driftX}px, ${driftY}px)`,
          background:
            "radial-gradient(ellipse 60% 40% at 50% 100%, rgba(255,255,255,0.18), transparent 70%)",
        }}
      />
      <div
        style={{
          position: "relative",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          padding: showDock ? "28px 48px 72px" : "28px 48px",
        }}
      >
        {children}
      </div>
      {showDock ? <MacDock /> : null}
    </AbsoluteFill>
  );
};

function MacDock() {
  const apps = [
    { label: "Product OS", color: "#0071e3", glyph: "OS" },
    { label: "Rooms", color: "#34c759", glyph: "◫" },
    { label: "Mail", color: "#5ac8fa", glyph: "✉" },
    { label: "GitHub", color: "#1d1d1f", glyph: "⎇" },
  ];

  return (
    <div
      style={{
        position: "absolute",
        bottom: 14,
        left: "50%",
        transform: "translateX(-50%)",
        display: "flex",
        gap: 10,
        padding: "8px 14px",
        borderRadius: 18,
        background: "rgba(255,255,255,0.42)",
        border: "1px solid rgba(255,255,255,0.55)",
        boxShadow: "0 12px 40px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.65)",
        backdropFilter: "blur(24px)",
      }}
    >
      {apps.map((app) => (
        <div
          key={app.label}
          title={app.label}
          style={{
            width: 44,
            height: 44,
            borderRadius: 11,
            background: `linear-gradient(180deg, ${app.color}ee, ${app.color})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: app.glyph.length > 2 ? 11 : 18,
            fontWeight: 700,
            color: "#fff",
            boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
          }}
        >
          {app.glyph}
        </div>
      ))}
    </div>
  );
}

type MacWindowProps = {
  title: string;
  children: React.ReactNode;
  width?: number;
  height?: number;
};

export const MacWindow: React.FC<MacWindowProps> = ({
  title,
  children,
  width = 920,
  height = 520,
}) => {
  return (
    <div
      style={{
        width,
        height,
        borderRadius: 12,
        overflow: "hidden",
        background: "rgba(255,255,255,0.94)",
        boxShadow:
          "0 2px 0 rgba(255,255,255,0.8) inset, 0 24px 80px rgba(0,0,0,0.28), 0 8px 24px rgba(0,0,0,0.12)",
        border: "1px solid rgba(0,0,0,0.08)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          height: 38,
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          padding: "0 14px",
          background: "linear-gradient(180deg, #f8f8f8 0%, #ececec 100%)",
          borderBottom: "1px solid rgba(0,0,0,0.08)",
          gap: 10,
        }}
      >
        <div style={{ display: "flex", gap: 7 }}>
          <TrafficLight color="#ff5f57" />
          <TrafficLight color="#febc2e" />
          <TrafficLight color="#28c840" />
        </div>
        <div
          style={{
            flex: 1,
            textAlign: "center",
            fontSize: 13,
            fontWeight: 500,
            color: "#3c3c43",
            letterSpacing: "-0.01em",
            marginRight: 52,
          }}
        >
          {title}
        </div>
      </div>
      <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>{children}</div>
    </div>
  );
};

function TrafficLight({ color }: { color: string }) {
  return (
    <div
      style={{
        width: 12,
        height: 12,
        borderRadius: "50%",
        background: color,
        boxShadow: "inset 0 -1px 2px rgba(0,0,0,0.15), 0 0 0 0.5px rgba(0,0,0,0.06)",
      }}
    />
  );
}
