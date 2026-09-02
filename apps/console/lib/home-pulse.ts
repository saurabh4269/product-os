import { getDemoCount, getVisitCount, hoursSinceLastVisit, isFirstVisit } from "@/lib/first-visit";

export type PulseAction = "pipeline" | "approvals" | "connect" | "explore";

export type HomePulse = {
  campusLine: string;
  campusHot?: boolean;
  commandLine: string;
  commandAction?: PulseAction;
  pipelineSubtitle: string;
  exploreHint: string;
  brief: {
    kicker: string;
    title: string;
    body: string;
    primary: { label: string; action: PulseAction };
    secondary?: { label: string; href: string };
    steps?: Array<{ n: string; label: string; hint: string }>;
    full?: boolean;
  } | null;
};

export type PulseInput = {
  open?: number;
  waiting?: number;
  inFlight?: number;
  workingAgents?: number;
  verified?: number;
  lessons?: number;
  workspaceConnected?: boolean;
  adminAuthRequired?: boolean;
};

const QUIET_TITLES = ["Quiet", "Ready", "Idle"] as const;

export function demoToastMessage(_demoCount: number) {
  return "Investigation started";
}

export function buildHomePulse(input: PulseInput): HomePulse {
  const visitCount = getVisitCount();
  const demoCount = getDemoCount();
  const hoursAway = hoursSinceLastVisit();
  const first = isFirstVisit();

  const open = input.open ?? 0;
  const waiting = input.waiting ?? 0;
  const inFlight = input.inFlight ?? 0;
  const workingAgents = input.workingAgents ?? 0;
  const verified = input.verified ?? 0;
  const wired = input.workspaceConnected ?? false;
  const needsAdmin = input.adminAuthRequired ?? false;

  const countSubtitle =
    open > 0 ? `${open} open` : inFlight > 0 ? `${inFlight} in flight` : verified > 0 ? `${verified} verified` : "";

  if (needsAdmin && !wired) {
    return {
      campusLine: "",
      commandLine: "Connect",
      commandAction: "connect",
      pipelineSubtitle: "",
      exploreHint: "",
      brief: {
        kicker: "Authorize",
        title: "Connect Product Y",
        body: "Paste LOOP_ADMIN_TOKEN on Connect to load office, rooms, and live receipts.",
        primary: { label: "Open Connect", action: "connect" },
      },
    };
  }

  if (first) {
    return {
      campusLine: "",
      commandLine: "Get started",
      commandAction: "connect",
      pipelineSubtitle: "",
      exploreHint: "",
      brief: {
        kicker: "Welcome",
        title: "Product OS",
        body: "",
        primary: { label: "Connect Product Y", action: "connect" },
        secondary: { label: "Outcomes", href: "/outcomes" },
        steps: [
          { n: "1", label: "Watch", hint: "Signal agent polls telemetry" },
          { n: "2", label: "Work", hint: "Agents appear as the case needs them" },
          { n: "3", label: "Gate", hint: "You approve real side effects" },
        ],
        full: true,
      },
    };
  }

  if (waiting > 0) {
    const n = waiting === 1 ? "1 waiting" : `${waiting} waiting`;
    return {
      campusLine: n,
      campusHot: true,
      commandLine: n,
      commandAction: "approvals",
      pipelineSubtitle: n,
      exploreHint: "",
      brief: {
        kicker: "Approve",
        title: waiting === 1 ? "1 change" : `${waiting} changes`,
        body: "",
        primary: { label: "Review", action: "pipeline" },
        secondary: { label: "Approvals", href: "/approvals" },
      },
    };
  }

  if (inFlight > 0 || open > 0) {
    const n = open || inFlight;
    return {
      campusLine:
        workingAgents > 0
          ? `${workingAgents} active`
          : `${n} open`,
      commandLine: `${n} open`,
      commandAction: "pipeline",
      pipelineSubtitle: countSubtitle,
      exploreHint: "",
      brief:
        hoursAway !== null && hoursAway >= 2
          ? {
              kicker: "Back",
              title: `${n} open`,
              body: "",
              primary: { label: "Pipeline", action: "pipeline" },
            }
          : null,
    };
  }

  const quietTitle = QUIET_TITLES[visitCount % QUIET_TITLES.length];

  return {
    campusLine: workingAgents > 0 ? `${workingAgents} active` : "",
    commandLine: wired ? "Open pipeline" : "Connect",
    commandAction: demoCount > 2 && !wired ? "connect" : wired ? "explore" : "connect",
    pipelineSubtitle: countSubtitle,
    exploreHint: "",
    brief: {
      kicker: hoursAway !== null && hoursAway >= 2 ? "Back" : "Today",
      title: quietTitle,
      body: "",
      primary: { label: wired ? "Pipeline" : "Connect", action: wired ? "pipeline" : "connect" },
      secondary: wired ? { label: "Labs", href: "/labs" } : { label: "Settings", href: "/settings" },
    },
  };
}
