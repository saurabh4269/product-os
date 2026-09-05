import data from "../fixtures/demo-room_65a4654bec.json";
import type { ScriptBeatKind } from "./script";

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

export function loopChip(payload: DemoBundle = bundle): string {
  if (payload.loop_chip) return payload.loop_chip;
  const raw = String(
    payload.investigation?.loop_type || payload.meta?.loop_type || "type_a",
  ).toLowerCase();
  if (raw.includes("type_b") || raw === "b" || raw === "feature") return "Type B · improve";
  return "Type A · fix";
}

export function signalMetric(payload: DemoBundle = bundle): string {
  const sig = payload.signals?.[0];
  if (sig?.metric) return sig.metric;
  return "otp_verify_hang_demo_1788625174";
}

export function signalDetail(payload: DemoBundle = bundle): string {
  const sig = payload.signals?.[0];
  if (sig?.metric != null) {
    return `${sig.metric} · ${((sig.magnitude ?? 0) * 100).toFixed(1)}% vs baseline`;
  }
  return "checkout abandon spike · tenant pipeline";
}

export function specialistLabels(payload: DemoBundle = bundle): string[] {
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
  const merged = [...new Set([...fromCalls, ...fromEvidence])];
  if (merged.length) return merged.slice(0, 5);
  return ["analytics", "logs", "code", "research", "customer voice"];
}

export function voiceDiagnostic(payload: DemoBundle = bundle): string {
  const tl = (payload.timeline ?? []).find((t) => /customer_voice|voice/i.test(t.actor ?? ""));
  if (tl?.detail && /otp|payment|timeout/i.test(tl.detail)) return tl.detail;
  const ev = (payload.evidence ?? []).find((e) => e.independence_group === "customer_voice");
  if (ev?.claim && /otp|payment|timeout/i.test(ev.claim)) return ev.claim;
  return "reason=otp_verify_timeout · severity=high · friction=technical";
}

export function rootCauseLine(payload: DemoBundle = bundle): string {
  const hyp = payload.hypotheses?.[0]?.statement;
  if (hyp && /otp|payment|sdk|verify/i.test(hyp)) {
    const short = hyp.length > 72 ? `${hyp.slice(0, 70)}…` : hyp;
    return short;
  }
  return "OTP verify hanging · pay-sdk path · logs agree";
}

export function tenantRepoLabel(payload: DemoBundle = bundle): string {
  const high = (payload.actions ?? []).find((a) => (a.risk_tier ?? "").toUpperCase() === "HIGH");
  const arts = (high?.artifacts ?? {}) as Record<string, unknown>;
  const gh = arts.github_pr as Record<string, unknown> | undefined;
  return (high?.tenant_repo as string) || (gh?.repo as string) || "demo-tenant/config";
}

export function verifyMetricLine(payload: DemoBundle = bundle): string {
  const outcome = payload.outcomes?.[0];
  const metric = signalMetric(payload);
  if (outcome?.verdict && outcome.verdict.toUpperCase() !== "NOT_RESOLVED") {
    return `${outcome.metric ?? metric}: ${Number(outcome.pre_value ?? 0).toPrecision(3)} → ${Number(outcome.post_value ?? 0).toPrecision(3)}`;
  }
  return `Watching ${metric} recovery post-ship`;
}

export function lessonLine(payload: DemoBundle = bundle): string {
  const lesson = payload.lessons?.[0]?.statement;
  if (lesson) return lesson.length > 80 ? `${lesson.slice(0, 78)}…` : lesson;
  return "OTP hang → mail-first, then call · remember for next incident";
}

export const LOOP_CHIP = loopChip();
export const INVESTIGATION_ID = bundle.investigation?.id ?? "investigation";
export const ROOM_ID = bundle.investigation?.room_id ?? bundle.meta?.room_id ?? "room";

/** Export-demo scene body by title (Signal, Evidence, Root cause, …) */
export function exportScene(title: string, payload: DemoBundle = bundle): string | undefined {
  return payload.scenes?.find((s) => s.title.toLowerCase() === title.toLowerCase())?.body;
}

export function githubPrNumber(payload: DemoBundle = bundle): number | null {
  const high = (payload.actions ?? []).find((a) => (a.risk_tier ?? "").toUpperCase() === "HIGH");
  const gh = (high?.artifacts as Record<string, unknown> | undefined)?.github_pr as
    | Record<string, unknown>
    | undefined;
  const n = gh?.number;
  return typeof n === "number" ? n : null;
}

/** Scene-aligned title shown inside the Mac window (not the VO caption) */
export function sceneTitle(kind: ScriptBeatKind): string {
  const titles: Record<ScriptBeatKind, string> = {
    cold_open: "Signal incoming",
    signal: "New room · tenant metric",
    room: "Parallel specialists",
    outreach: "Contact lookup · mail",
    root_cause: "Customer Voice · root cause",
    high_gate: "HIGH gate · flags PR",
    call_close: "Verify · Lexi call",
    end_card: "Product OS",
  };
  return titles[kind];
}
