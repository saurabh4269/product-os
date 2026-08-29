const BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8080");

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store", credentials: "same-origin" });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
  });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

export type Investigation = {
  id: string;
  state: string;
  opened_at: string;
  closed_at?: string | null;
  invocation_id: string;
  assigned_agents: string[];
  recalled_lessons: string[];
  verification_result?: string | null;
};

export type Evidence = {
  id: string;
  source_type: string;
  source_reference: string;
  claim: string;
  confidence: number;
  trust_level: string;
  collected_by: string;
  independence_group: string;
};

export type Hypothesis = {
  id: string;
  statement: string;
  classification: string;
  confidence: number;
  supporting_evidence_ids: string[];
  independence_groups: string[];
};

export type Action = {
  id: string;
  investigation_id: string;
  type: string;
  risk_tier: string;
  tier_rationale: string;
  status: string;
  consequence: string;
  artifacts: Record<string, unknown>;
};

export type Timeline = {
  id: string;
  at: string;
  actor: string;
  kind: string;
  title: string;
  detail: string;
  denial: boolean;
};

export type Bundle = {
  investigation: Investigation;
  signals: Array<Record<string, unknown>>;
  evidence: Evidence[];
  hypotheses: Hypothesis[];
  actions: Action[];
  timeline: Timeline[];
  agent_calls: Array<Record<string, unknown>>;
  outcomes: Array<Record<string, unknown>>;
  lessons: Array<Record<string, unknown>>;
  verdicts: Array<Record<string, unknown>>;
};

export const api = {
  health: () => get<{ ok: boolean }>("/api/health"),
  run: () => post<Bundle>("/api/loop/run"),
  investigations: () =>
    get<{ investigations: Array<Investigation & { hypothesis?: string; confidence?: number; risk_tier?: string; action_status?: string }> }>(
      "/api/investigations"
    ),
  investigation: (id: string) => get<Bundle>(`/api/investigations/${id}`),
  signals: () => get<{ signals: Array<Record<string, unknown>> }>("/api/signals"),
  approvals: () => get<{ pending: Action[]; history: Array<Record<string, unknown>> }>("/api/approvals"),
  approve: (actionId: string, decision: "approve" | "deny") =>
    post(`/api/approvals/${actionId}`, {
      decision,
      approver: "oncall@northstar",
      rationale:
        decision === "approve"
          ? "Evidence graph is consistent across analytics, logs, and deploy timeline."
          : "Need more evidence before touching payment.",
    }),
  outcomes: () => get<{ outcomes: Array<Record<string, unknown>> }>("/api/outcomes"),
  governance: () =>
    get<{
      identities: Array<{ id: string; envelope: string }>;
      verdicts: Array<Record<string, unknown>>;
      failOpen: boolean;
    }>("/api/governance"),
  opportunities: () =>
    get<{ opportunities: Array<Record<string, unknown>> }>("/api/opportunities"),
  agents: () =>
    get<{ agents: Array<{ id: string; room: string; role: string; tb: string; status: string }> }>(
      "/api/agents"
    ),
  metrics: () =>
    get<{
      idea_to_impact_hours_mean: number | null;
      idea_to_impact_target_hours: number;
      baseline_manual_hours: number;
      investigations: number;
      resolved: number;
      failOpen: boolean;
    }>("/api/metrics"),
};
