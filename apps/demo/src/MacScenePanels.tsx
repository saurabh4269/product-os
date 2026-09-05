import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import type { MacScene, MacSceneKind } from "./demoData";

const INK = "#1d1d1f";
const DIM = "#6e6e73";
const ACCENT = "#0071e3";
const GREEN = "#34c759";
const ORANGE = "#ff9500";
const RED = "#ff3b30";

type PanelProps = {
  scene: MacScene;
  localFrame: number;
};

function fadeUp(localFrame: number, delay = 4) {
  const opacity = interpolate(localFrame - delay, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const y = interpolate(localFrame - delay, [0, 14], [12, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return { opacity, transform: `translateY(${y}px)` };
}

function Chip({ label, tone = "accent" }: { label: string; tone?: "accent" | "high" | "ok" }) {
  const styles =
    tone === "high"
      ? { bg: "#fff0f0", border: RED, color: RED }
      : tone === "ok"
        ? { bg: "#e8f8ed", border: GREEN, color: "#248a3d" }
        : { bg: "#e8f1fc", border: ACCENT, color: ACCENT };
  return (
    <span
      style={{
        display: "inline-flex",
        padding: "4px 10px",
        borderRadius: 999,
        fontSize: 11,
        fontWeight: 600,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        background: styles.bg,
        border: `1px solid ${styles.border}`,
        color: styles.color,
      }}
    >
      {label}
    </span>
  );
}

function SceneHeader({ scene, localFrame }: PanelProps) {
  const anim = fadeUp(localFrame, 2);
  return (
    <div style={{ ...anim, padding: "22px 28px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
        <Chip label={scene.chip ?? "Type A · fix"} />
        <span style={{ fontSize: 12, color: DIM, letterSpacing: "0.06em", textTransform: "uppercase" }}>
          {scene.title}
        </span>
      </div>
      <p
        style={{
          margin: 0,
          fontSize: 22,
          lineHeight: 1.35,
          fontWeight: 500,
          color: INK,
          maxWidth: 760,
          letterSpacing: "-0.02em",
        }}
      >
        {scene.body}
      </p>
    </div>
  );
}

function AgentRow({ agents, localFrame, highlightIdx }: { agents: string[]; localFrame: number; highlightIdx?: number }) {
  const anim = fadeUp(localFrame, 10);
  return (
    <div style={{ ...anim, display: "flex", gap: 8, flexWrap: "wrap", padding: "0 28px", marginTop: 18 }}>
      {agents.map((a, i) => {
        const lit = highlightIdx === i || (highlightIdx === undefined && localFrame > 12 + i * 4);
        return (
          <div
            key={a}
            style={{
              padding: "8px 14px",
              borderRadius: 10,
              fontSize: 13,
              fontWeight: 500,
              background: lit ? "#e8f1fc" : "rgba(0,0,0,0.04)",
              border: lit ? `1px solid ${ACCENT}55` : "1px solid rgba(0,0,0,0.06)",
              color: lit ? ACCENT : DIM,
              transition: "none",
            }}
          >
            {a}
          </div>
        );
      })}
    </div>
  );
}

function Card({
  title,
  subtitle,
  icon,
  tone = "neutral",
  localFrame,
  delay = 14,
}: {
  title: string;
  subtitle: string;
  icon: string;
  tone?: "neutral" | "mail" | "github" | "call" | "approve" | "ok";
  localFrame: number;
  delay?: number;
}) {
  const anim = fadeUp(localFrame, delay);
  const borders: Record<string, string> = {
    neutral: "rgba(0,0,0,0.08)",
    mail: "#5ac8fa55",
    github: "#1d1d1f22",
    call: "#af52de55",
    approve: "#ff950055",
    ok: "#34c75955",
  };
  const bgs: Record<string, string> = {
    neutral: "#fafafa",
    mail: "#f0f9ff",
    github: "#f5f5f7",
    call: "#faf5ff",
    approve: "#fff8f0",
    ok: "#e8f8ed",
  };

  return (
    <div
      style={{
        ...anim,
        margin: "16px 28px 0",
        padding: "14px 16px",
        borderRadius: 12,
        background: bgs[tone],
        border: `1px solid ${borders[tone]}`,
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
      }}
    >
      <div style={{ fontSize: 22, lineHeight: 1 }}>{icon}</div>
      <div>
        <div style={{ fontSize: 14, fontWeight: 600, color: INK }}>{title}</div>
        <div style={{ fontSize: 12, color: DIM, marginTop: 4, lineHeight: 1.45 }}>{subtitle}</div>
      </div>
    </div>
  );
}

export function MacScenePanel({ scene, localFrame }: PanelProps) {
  const kind = scene.kind;

  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <SceneHeader scene={scene} localFrame={localFrame} />
      <SceneVisual kind={kind} scene={scene} localFrame={localFrame} />
    </div>
  );
}

function SceneVisual({
  kind,
  scene,
  localFrame,
}: {
  kind: MacSceneKind;
  scene: MacScene;
  localFrame: number;
}) {
  switch (kind) {
    case "signal":
      return (
        <>
          <Card
            localFrame={localFrame}
            icon="📡"
            title="Pipeline signal"
            subtitle="Tenant metric crossed threshold · routed to Product OS campus"
            tone="neutral"
          />
          <div style={{ ...fadeUp(localFrame, 22), margin: "12px 28px 0", display: "flex", gap: 8 }}>
            <Chip label="Incident" tone="high" />
            <span style={{ fontSize: 12, color: DIM }}>Auto-open room</span>
          </div>
        </>
      );

    case "room":
      return (
        <>
          <AgentRow
            agents={["Analytics", "Logs", "Code", "Research", "Customer Voice"]}
            localFrame={localFrame}
            highlightIdx={Math.min(4, Math.floor((localFrame - 8) / 6))}
          />
          <Card
            localFrame={localFrame}
            delay={28}
            icon="◫"
            title="Parallel specialists"
            subtitle="Handoffs visible in room · three-source gate before root cause"
          />
        </>
      );

    case "outreach":
      return (
        <>
          <Card
            localFrame={localFrame}
            icon="👤"
            title="Contact lookup"
            subtitle="Matched abandon cohort from registration identity"
            tone="neutral"
          />
          <Card
            localFrame={localFrame}
            delay={20}
            icon="✉️"
            title="Mail-first outreach"
            subtitle="Email sent · no spam call until mail window closes"
            tone="mail"
          />
        </>
      );

    case "root_cause":
      return (
        <>
          <Card
            localFrame={localFrame}
            icon="🎙"
            title="Customer Voice feedback"
            subtitle="Diagnostic JSON: technical friction · OTP / payment SDK path"
            tone="call"
          />
          <Card
            localFrame={localFrame}
            delay={18}
            icon="🔍"
            title="Root cause locked"
            subtitle={scene.body.length > 90 ? `${scene.body.slice(0, 88)}…` : scene.body}
            tone="neutral"
          />
        </>
      );

    case "flags_pr":
      return (
        <>
          <Card
            localFrame={localFrame}
            icon="⎇"
            title="Tenant flags PR"
            subtitle="config/flags.json · HIGH-gated · never auto-merge"
            tone="github"
          />
          <div style={{ ...fadeUp(localFrame, 24), margin: "12px 28px 0" }}>
            <Chip label="HIGH" tone="high" />
            <span style={{ marginLeft: 10, fontSize: 12, color: DIM }}>Opens on human approve</span>
          </div>
        </>
      );

    case "approve":
      return (
        <>
          <Card
            localFrame={localFrame}
            icon="✓"
            title="Human approval required"
            subtitle={scene.body}
            tone="approve"
          />
          <div
            style={{
              ...fadeUp(localFrame, 26),
              margin: "16px 28px 0",
              padding: "12px 16px",
              borderRadius: 10,
              background: ACCENT,
              color: "#fff",
              fontSize: 14,
              fontWeight: 600,
              width: "fit-content",
              boxShadow: "0 4px 14px rgba(0,113,227,0.35)",
            }}
          >
            Approve in LOOP
          </div>
        </>
      );

    case "verify_call":
      return (
        <>
          <Card
            localFrame={localFrame}
            icon="✓"
            title="Verify path"
            subtitle={scene.body.split(" Lexi")[0] || "Watching metric recovery after ship"}
            tone="ok"
          />
          <Card
            localFrame={localFrame}
            delay={20}
            icon="📞"
            title="Lexi · phone notify"
            subtitle={
              scene.body.includes("Lexi")
                ? scene.body.split("Lexi ")[1] ?? "Calls about checkout friction after mail window"
                : "Phone notify after mail-first outreach window"
            }
            tone="call"
          />
        </>
      );

    default:
      return null;
  }
}

/** Progress dots for scene index */
export function SceneProgress({ count, active, localFrame }: { count: number; active: number; localFrame: number }) {
  return (
    <div
      style={{
        position: "absolute",
        bottom: 16,
        left: 28,
        display: "flex",
        gap: 6,
        opacity: interpolate(localFrame, [0, 8], [0, 0.7], { extrapolateRight: "clamp" }),
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            width: i === active ? 18 : 6,
            height: 6,
            borderRadius: 3,
            background: i === active ? ACCENT : "rgba(0,0,0,0.12)",
          }}
        />
      ))}
    </div>
  );
}
