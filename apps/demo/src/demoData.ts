import data from "../public/loop.json";

export type MacSceneKind =
  | "signal"
  | "room"
  | "outreach"
  | "root_cause"
  | "flags_pr"
  | "approve"
  | "verify_call";

export type MacScene = {
  kind: MacSceneKind;
  title: string;
  body: string;
  chip?: string;
  /** Cursor hotspot in window coords (0–1) */
  hotspot: { x: number; y: number };
  /** Frame within scene when cursor "clicks" */
  clickAt: number;
};

export type DemoBundle = {
  meta?: {
    pipeline?: string;
    exported_at?: string;
    loop_type?: string;
    room_id?: string;
    source?: string;
  };
  loop_chip?: string;
  scenes?: Array<{ title: string; body: string }>;
  investigation?: {
    id?: string;
    state?: string;
    title?: string;
    loop_type?: string;
    assigned_agents?: string[];
    room_id?: string;
    tenant_id?: string | null;
  };
  signals?: Array<{ metric?: string; magnitude?: number; baseline?: number }>;
  evidence?: Array<{ independence_group?: string; trust_level?: string; claim?: string }>;
  hypotheses?: Array<{ statement?: string }>;
  actions?: Array<{
    risk_tier?: string;
    consequence?: string;
    tier_rationale?: string;
    gate_mode?: string;
    tenant_repo?: string;
    status?: string;
    artifacts?: Record<string, unknown>;
  }>;
  outcomes?: Array<{ verdict?: string; metric?: string; pre_value?: number; post_value?: number }>;
  lessons?: Array<{ statement?: string }>;
  agent_calls?: Array<{ to_agent?: string; summary?: string }>;
  timeline?: Array<{ kind?: string; title?: string; detail?: string; actor?: string }>;
  recalled_lessons?: string[];
};

export const bundle = data as DemoBundle;

const WAITING = {
  signal: "Signal stage is waiting — no metric from the pipeline yet.",
  room: "Room stage is waiting — specialists have not joined yet.",
  outreach: "Outreach stage is waiting — contact lookup not run yet.",
  root_cause: "Root cause stage is waiting — hypothesis not locked yet.",
  flags_pr: "Flags PR stage is waiting — no HIGH tenant change drafted yet.",
  approve: "Approval stage is waiting — no HIGH consequence drafted yet.",
  verify_call: "Verify stage is waiting — outcome and call not recorded yet.",
} as const;

function loopChip(payload: DemoBundle): string {
  if (payload.loop_chip) return payload.loop_chip;
  const raw = String(
    payload.investigation?.loop_type || payload.meta?.loop_type || "type_a",
  ).toLowerCase();
  if (raw.includes("type_b") || raw === "b" || raw === "feature") return "Type B · improve";
  return "Type A · fix";
}

function signalMetric(payload: DemoBundle): string {
  const sig = payload.signals?.[0];
  return sig?.metric ?? "";
}

function specialistLabels(payload: DemoBundle): string[] {
  const fromCalls = [
    ...new Set(
      (payload.agent_calls ?? [])
        .map((c) => c.to_agent?.replace(/_agent$/, "").replace(/_/g, " "))
        .filter(Boolean) as string[],
    ),
  ];
  const fromEvidence = [
    ...new Set(
      (payload.evidence ?? [])
        .filter((e) => (e.trust_level ?? "trusted") !== "untrusted")
        .map((e) => e.independence_group?.replace(/_/g, " "))
        .filter(Boolean) as string[],
    ),
  ];
  const merged = [...new Set([...fromCalls, ...fromEvidence])].slice(0, 6);
  if (merged.length) return merged;
  const assigned = (payload.investigation?.assigned_agents ?? [])
    .map((a) => a.replace(/_agent$/, "").replace(/_/g, " "))
    .filter((a) => a !== "orchestrator" && a !== "investigator");
  return assigned.length ? assigned.slice(0, 6) : ["analytics", "logs", "code", "research", "customer voice"];
}

function outreachBody(payload: DemoBundle): string {
  const tl = (payload.timeline ?? []).find(
    (t) =>
      /contact|mail|outreach/i.test(t.kind ?? "") ||
      /contact|mail|outreach/i.test(t.title ?? ""),
  );
  if (tl?.detail) return tl.detail;
  const lesson = (payload.recalled_lessons ?? [])[0] ?? (payload.lessons ?? [])[0]?.statement;
  if (lesson && /checkout|abandon|mail|email/i.test(lesson)) {
    return `Contact lookup → email abandon cohort. ${lesson.split(".")[0]}.`;
  }
  const metric = signalMetric(payload);
  if (/otp|checkout|payment|hang/i.test(metric)) {
    return "Contact lookup matched abandon cohort · mail-first outreach before any call.";
  }
  return "Contact lookup → mail-first outreach to affected users. No spam calls.";
}

function flagsPrBody(payload: DemoBundle): string {
  const high = (payload.actions ?? []).find((a) => (a.risk_tier ?? "").toUpperCase() === "HIGH");
  const arts = (high?.artifacts ?? {}) as Record<string, unknown>;
  const gh = arts.github_pr as Record<string, unknown> | undefined;
  const pr = arts.pr as Record<string, unknown> | undefined;
  const repo = high?.tenant_repo || (gh?.repo as string) || "tenant repo";
  const title = (gh?.title as string) || (pr?.title as string) || "flags.json";
  if (high?.gate_mode === "github_pr" || gh) {
    return `HIGH-gated ${title} on ${repo} — never auto-merge.`;
  }
  if (high?.consequence) {
    return `${high.consequence} Tenant flags PR opens on approve — never merge.`;
  }
  return WAITING.flags_pr;
}

function verifyCallBody(payload: DemoBundle): string {
  const outcome = payload.outcomes?.[0];
  const metric = signalMetric(payload);
  const high = (payload.actions ?? []).find((a) => (a.risk_tier ?? "").toUpperCase() === "HIGH");
  const voice = (high?.artifacts as Record<string, unknown> | undefined)?.voice_context as
    | Record<string, unknown>
    | undefined;
  const failure = (voice?.failure as string) || "checkout friction";
  const device = (voice?.device as string) || "mobile";

  let verify = "";
  if (outcome?.verdict && outcome.verdict.toUpperCase() !== "NOT_RESOLVED") {
    verify = `Verified ${outcome.metric ?? metric}: ${Number(outcome.pre_value ?? 0).toPrecision(3)} → ${Number(outcome.post_value ?? 0).toPrecision(3)}.`;
  } else if (metric) {
    verify = `Verify path running — watching ${metric} recovery.`;
  } else {
    verify = "Verify path armed after approve.";
  }

  const callLine = `Lexi calls about ${failure} on ${device} — phone notify after mail window.`;
  return `${verify} ${callLine}`;
}

export function buildMacScenes(payload: DemoBundle = bundle): MacScene[] {
  const sig = payload.signals?.[0];
  const jsonScenes = payload.scenes ?? [];
  const chip = loopChip(payload);

  const signalBody =
    jsonScenes[0]?.body ??
    (sig?.metric != null
      ? `${sig.metric} moved ${((sig.magnitude ?? 0) * 100).toFixed(1)}% vs baseline ${((sig.baseline ?? 0) * 100).toFixed(1)}% — lands in Product OS from the tenant pipeline.`
      : WAITING.signal);

  const specialists = specialistLabels(payload);
  const roomBody =
    jsonScenes[1]?.body ??
    (specialists.length
      ? `New room opens · parallel specialists: ${specialists.join(" · ")}. Customer Voice joins the thread.`
      : WAITING.room);

  const rootBody =
    jsonScenes[2]?.body ??
    payload.hypotheses?.[0]?.statement ??
    WAITING.root_cause;

  const highAction = (payload.actions ?? []).find((a) => (a.risk_tier ?? "").toUpperCase() === "HIGH");
  const approveBody =
    jsonScenes[3]?.body ??
    highAction?.consequence ??
    highAction?.tier_rationale ??
    WAITING.approve;

  return [
    {
      kind: "signal",
      title: jsonScenes[0]?.title ?? "Signal",
      body: signalBody,
      chip,
      hotspot: { x: 0.72, y: 0.28 },
      clickAt: 24,
    },
    {
      kind: "room",
      title: "Room",
      body: roomBody,
      chip,
      hotspot: { x: 0.38, y: 0.42 },
      clickAt: 28,
    },
    {
      kind: "outreach",
      title: "Outreach",
      body: outreachBody(payload),
      chip,
      hotspot: { x: 0.58, y: 0.52 },
      clickAt: 30,
    },
    {
      kind: "root_cause",
      title: jsonScenes[2]?.title ?? "Root cause",
      body: rootBody,
      chip,
      hotspot: { x: 0.44, y: 0.48 },
      clickAt: 26,
    },
    {
      kind: "flags_pr",
      title: "Flags PR",
      body: flagsPrBody(payload),
      chip,
      hotspot: { x: 0.62, y: 0.55 },
      clickAt: 32,
    },
    {
      kind: "approve",
      title: jsonScenes[3]?.title ?? "HIGH approval",
      body: approveBody,
      chip,
      hotspot: { x: 0.68, y: 0.62 },
      clickAt: 34,
    },
    {
      kind: "verify_call",
      title: "Verify + call",
      body: verifyCallBody(payload),
      chip,
      hotspot: { x: 0.52, y: 0.58 },
      clickAt: 36,
    },
  ];
}

export const MAC_SCENES = buildMacScenes(bundle);
export const LOOP_CHIP = loopChip(bundle);
export const INVESTIGATION_ID = bundle.investigation?.id ?? "investigation";
