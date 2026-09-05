import React from "react";
import { Easing, interpolate } from "remotion";
import type { ScriptBeat, ScriptBeatKind } from "./script";
import {
  lessonLine,
  loopChip,
  rootCauseLine,
  sceneTitle,
  signalDetail,
  signalMetric,
  specialistLabels,
  tenantRepoLabel,
  verifyMetricLine,
  voiceDiagnostic,
} from "./demoData";

const INK = "#1d1d1f";
const DIM = "#6e6e73";
const ACCENT = "#0071e3";
const GREEN = "#34c759";
const RED = "#ff3b30";

type PanelProps = {
  beat: ScriptBeat;
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

function SceneHeader({ beat, localFrame }: PanelProps) {
  const anim = fadeUp(localFrame, 2);
  return (
    <div style={{ ...anim, padding: "20px 28px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
        <Chip label={loopChip()} />
        <span style={{ fontSize: 12, color: DIM, letterSpacing: "0.05em" }}>
          {sceneTitle(beat.kind)}
        </span>
      </div>
    </div>
  );
}

function Card({
  title,
  subtitle,
  meta,
  tone = "neutral",
  localFrame,
  delay = 10,
}: {
  title: string;
  subtitle: string;
  meta?: string;
  tone?: "neutral" | "mail" | "github" | "call" | "approve" | "ok" | "signal";
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
    signal: "#0071e355",
  };
  const bgs: Record<string, string> = {
    neutral: "#fafafa",
    mail: "#f0f9ff",
    github: "#f5f5f7",
    call: "#faf5ff",
    approve: "#fff8f0",
    ok: "#e8f8ed",
    signal: "#f0f7ff",
  };

  return (
    <div
      style={{
        ...anim,
        margin: "12px 28px 0",
        padding: "13px 15px",
        borderRadius: 11,
        background: bgs[tone],
        border: `1px solid ${borders[tone]}`,
      }}
    >
      <div style={{ fontSize: 14, fontWeight: 600, color: INK }}>{title}</div>
      <div style={{ fontSize: 12, color: DIM, marginTop: 4, lineHeight: 1.45 }}>{subtitle}</div>
      {meta ? (
        <div style={{ fontSize: 11, color: DIM, marginTop: 6, fontFamily: "ui-monospace, monospace" }}>
          {meta}
        </div>
      ) : null}
    </div>
  );
}

function HandoffRow({ localFrame }: { localFrame: number }) {
  const pairs = [
    { from: "investigator", to: "analytics", label: "Asked Analytics for the numbers" },
    { from: "investigator", to: "logs", label: "Asked Logs for the logs" },
    { from: "orchestrator", to: "customer voice", label: "Asked Voice for customer notes" },
  ];
  const idx = Math.min(pairs.length - 1, Math.floor((localFrame - 20) / 45));

  return (
    <div style={{ ...fadeUp(localFrame, 18), margin: "10px 28px 0" }}>
      {pairs.slice(0, idx + 1).map((p, i) => (
        <div
          key={i}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "7px 0",
            borderBottom: i < idx ? "1px solid rgba(0,0,0,0.05)" : "none",
            opacity: i === idx ? 1 : 0.55,
          }}
        >
          <span style={{ fontSize: 11, color: ACCENT, fontWeight: 600 }}>{p.from}</span>
          <span style={{ fontSize: 11, color: DIM }}>→</span>
          <span style={{ fontSize: 11, color: INK, fontWeight: 500 }}>{p.to}</span>
          <span style={{ fontSize: 11, color: DIM, marginLeft: 4 }}>{p.label}</span>
        </div>
      ))}
    </div>
  );
}

export function MacScenePanel({ beat, localFrame }: PanelProps) {
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <SceneHeader beat={beat} localFrame={localFrame} />
      <SceneVisual kind={beat.kind} localFrame={localFrame} />
    </div>
  );
}

function SceneVisual({ kind, localFrame }: { kind: ScriptBeatKind; localFrame: number }) {
  switch (kind) {
    case "cold_open":
      return (
        <Card
          localFrame={localFrame}
          delay={30}
          tone="signal"
          title="Checkout stall detected"
          subtitle="Tenant metric crossed threshold"
          meta={signalDetail()}
        />
      );

    case "signal":
      return (
        <>
          <Card
            localFrame={localFrame}
            tone="signal"
            title={`Signal · ${signalMetric()}`}
            subtitle="Ingest from demo tenant · generic pipeline"
            meta="Cove = demo tenant · Product OS = control plane"
          />
          <Card
            localFrame={localFrame}
            delay={24}
            title="Room opened"
            subtitle="Incident room · specialists assigned"
            meta="Type A · fix"
          />
        </>
      );

    case "room": {
      const agents = specialistLabels().map(
        (a) => a.charAt(0).toUpperCase() + a.slice(1),
      );
      const lit = Math.min(agents.length - 1, Math.floor((localFrame - 12) / 28));
      return (
        <>
          <div style={{ ...fadeUp(localFrame, 8), display: "flex", gap: 7, flexWrap: "wrap", padding: "8px 28px 0" }}>
            {agents.map((a, i) => (
              <div
                key={a}
                style={{
                  padding: "7px 12px",
                  borderRadius: 9,
                  fontSize: 12,
                  fontWeight: 500,
                  background: i <= lit ? "#e8f1fc" : "rgba(0,0,0,0.04)",
                  border: i <= lit ? `1px solid ${ACCENT}44` : "1px solid rgba(0,0,0,0.06)",
                  color: i <= lit ? ACCENT : DIM,
                }}
              >
                {a}
              </div>
            ))}
          </div>
          <HandoffRow localFrame={localFrame} />
        </>
      );
    }

    case "outreach":
      return (
        <>
          <Card
            localFrame={localFrame}
            title="Contact lookup"
            subtitle="Abandon cohort · registration identity"
            meta="12 users matched mid-checkout"
            tone="neutral"
          />
          <Card
            localFrame={localFrame}
            delay={22}
            title="Gmail · mail-first"
            subtitle="What did you see at checkout? — no call yet"
            tone="mail"
          />
        </>
      );

    case "root_cause":
      return (
        <>
          <Card
            localFrame={localFrame}
            title="Customer Voice"
            subtitle={voiceDiagnostic()}
            tone="call"
          />
          <Card
            localFrame={localFrame}
            delay={20}
            title="Hypothesis locked"
            subtitle={rootCauseLine()}
            meta="otp_verify_timeout · not “payments feel slow”"
          />
        </>
      );

    case "high_gate": {
      const showPr = localFrame > 180;
      return (
        <>
          <Card
            localFrame={localFrame}
            title="HIGH gate"
            subtitle="Human must open the door — auth/payment surface"
            tone="approve"
          />
          {showPr ? (
            <Card
              localFrame={localFrame}
              delay={0}
              title="GitHub · flags PR"
              subtitle={`config/flags.json on ${tenantRepoLabel()}`}
              meta="OPEN · never auto-merge"
              tone="github"
            />
          ) : (
            <div
              style={{
                ...fadeUp(localFrame, 40),
                margin: "14px 28px 0",
                padding: "11px 16px",
                borderRadius: 10,
                background: ACCENT,
                color: "#fff",
                fontSize: 13,
                fontWeight: 600,
                width: "fit-content",
                boxShadow: "0 4px 14px rgba(0,113,227,0.35)",
              }}
            >
              Approve →
            </div>
          )}
        </>
      );
    }

    case "call_close":
      return (
        <>
          <Card
            localFrame={localFrame}
            title="Lexi · phone notify"
            subtitle="“It’s fixed — sorry for the wait.” Short, human."
            meta="+1 · outbound after mail window"
            tone="call"
          />
          <Card
            localFrame={localFrame}
            delay={24}
            title="Verify + remember"
            subtitle={verifyMetricLine()}
            meta={lessonLine()}
            tone="ok"
          />
        </>
      );

    case "end_card":
      return null;

    default:
      return null;
  }
}

export function SceneProgress({
  count,
  active,
  localFrame,
}: {
  count: number;
  active: number;
  localFrame: number;
}) {
  return (
    <div
      style={{
        position: "absolute",
        bottom: 14,
        left: 28,
        display: "flex",
        gap: 5,
        opacity: interpolate(localFrame, [0, 8], [0, 0.65], { extrapolateRight: "clamp" }),
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            width: i === active ? 16 : 5,
            height: 5,
            borderRadius: 3,
            background: i === active ? ACCENT : "rgba(0,0,0,0.1)",
          }}
        />
      ))}
    </div>
  );
}

/** Cold-open window scale-in */
export function windowOpenScale(localFrame: number): number {
  return interpolate(localFrame, [20, 50], [0.92, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
}

export function windowOpenOpacity(localFrame: number): number {
  return interpolate(localFrame, [18, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
}
