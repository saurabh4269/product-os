/** Locked VO script — timing @ 30 fps. See ../SCRIPT.md */

export const FPS = 30;

export type ScriptBeatKind =
  | "cold_open"
  | "signal"
  | "room"
  | "outreach"
  | "root_cause"
  | "high_gate"
  | "call_close"
  | "end_card";

export type ScriptBeat = {
  kind: ScriptBeatKind;
  label: string;
  /** VO line burned as caption */
  caption: string;
  /** Start time in seconds (for SCRIPT.md) */
  startSec: number;
  /** Duration in frames */
  durationFrames: number;
  windowTitle: string;
  hotspot: { x: number; y: number };
  clickAt: number;
};

export const SCRIPT_BEATS: ScriptBeat[] = [
  {
    kind: "cold_open",
    label: "Cold open",
    caption: "Checkout just stalled for a bunch of people. Not a ticket. A signal.",
    startSec: 0,
    durationFrames: 8 * FPS,
    windowTitle: "Product OS",
    hotspot: { x: 0.5, y: 0.45 },
    clickAt: 60,
  },
  {
    kind: "signal",
    label: "Signal",
    caption:
      "Product OS opens a room the moment the metric breaks. Same generic pipeline we’d use for any product — Cove is just the tenant we’re demoing.",
    startSec: 8,
    durationFrames: 12 * FPS,
    windowTitle: "Product OS · Signal",
    hotspot: { x: 0.68, y: 0.32 },
    clickAt: 90,
  },
  {
    kind: "room",
    label: "Specialists",
    caption:
      "Specialists fan out in parallel — analytics, logs, code, research, customer voice. You can see them hand work to each other. No black box.",
    startSec: 20,
    durationFrames: 18 * FPS,
    windowTitle: "Room · parallel specialists",
    hotspot: { x: 0.4, y: 0.44 },
    clickAt: 120,
  },
  {
    kind: "outreach",
    label: "Outreach",
    caption:
      "We don’t guess. We look up people who abandoned mid-checkout and ask what they saw. Mail first — calls only if they don’t respond.",
    startSec: 38,
    durationFrames: 14 * FPS,
    windowTitle: "Outreach · contact lookup",
    hotspot: { x: 0.56, y: 0.52 },
    clickAt: 100,
  },
  {
    kind: "root_cause",
    label: "Root cause",
    caption:
      "Feedback lines up with the logs: OTP verify is hanging. That’s the root cause — not a vague “payments feel slow.”",
    startSec: 52,
    durationFrames: 16 * FPS,
    windowTitle: "Customer Voice · diagnose",
    hotspot: { x: 0.46, y: 0.48 },
    clickAt: 110,
  },
  {
    kind: "high_gate",
    label: "HIGH gate + PR",
    caption:
      "Fix is HIGH risk, so a human has to open the door. One click — flags PR on the tenant repo. We never auto-merge.",
    startSec: 68,
    durationFrames: 20 * FPS,
    windowTitle: "Approvals · HIGH gate",
    hotspot: { x: 0.64, y: 0.58 },
    clickAt: 180,
  },
  {
    kind: "call_close",
    label: "Call + verify",
    caption:
      "If someone’s still stuck after the fix, Lexi calls — short, human, “it’s fixed, sorry for the wait.” Then we measure whether checkout recovers, and we remember the lesson.",
    startSec: 88,
    durationFrames: 22 * FPS,
    windowTitle: "Verify · phone notify",
    hotspot: { x: 0.52, y: 0.56 },
    clickAt: 200,
  },
  {
    kind: "end_card",
    label: "End",
    caption: "Observe. Investigate. Gate. Ship. Measure. Remember.",
    startSec: 110,
    durationFrames: 8 * FPS,
    windowTitle: "Product OS",
    hotspot: { x: 0.5, y: 0.5 },
    clickAt: 999,
  },
];

export const MACOS_DEMO_DURATION = SCRIPT_BEATS.reduce((n, b) => n + b.durationFrames, 0);

/** Frame offset for each beat */
export function beatOffsets(): number[] {
  let acc = 0;
  return SCRIPT_BEATS.map((b) => {
    const at = acc;
    acc += b.durationFrames;
    return at;
  });
}
