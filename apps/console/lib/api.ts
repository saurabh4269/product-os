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
  scenario_id?: string | null;
  room_id?: string | null;
  title?: string | null;
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
  gate?: string;
  gate_mode?: string;
  tenant_repo?: string;
};

export type Tenant = {
  id: string;
  name: string;
  product: string;
  repo: string;
  deploy_url: string;
  connected: boolean;
  has_token: boolean;
  last_pr_url?: string;
  last_ingest_at?: string;
  last_connector?: string;
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

export type Room = {
  id: string;
  kind: string;
  title: string;
  topic: string;
  status: string;
  created_at: string;
  members: string[];
  investigation_id?: string | null;
  scenario_id?: string | null;
  loop_type?: string | null;
  path?: string | null;
  message_count?: number;
  preview?: string;
};

export type RoomMessage = {
  id: string;
  room_id: string;
  author: string;
  author_kind: string;
  kind: string;
  text: string;
  artifact_type?: string | null;
  artifact: Record<string, unknown>;
  created_at: string;
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

export type RoomDetail = {
  room: Room;
  messages: RoomMessage[];
  bundle: Bundle | null;
  members: string[];
};

export type OfficeDesk = {
  id: string;
  display_name: string;
  role: string;
  identity: string;
  status: "working" | "handing_off" | "idle" | string;
  doing: string;
  room_id?: string | null;
  room_title?: string | null;
  district: string;
  last_at?: string | null;
  handed_from?: string | null;
  handed_to?: string | null;
  message_count: number;
  handoff_count: number;
};

export type Handoff = {
  id: string;
  from_agent: string;
  to_agent: string;
  summary: string;
  started_at: string;
  room_id?: string | null;
  room_title?: string | null;
};

export type OfficeSnapshot = {
  desks: OfficeDesk[];
  handoffs: Handoff[];
  working: number;
  idle: number;
};

export type RegistryAgent = {
  id: string;
  display_name: string;
  owner: string;
  capabilities: string[];
  permissions_allow: string[];
  permissions_deny: string[];
  version: string;
  environment: string;
  risk_level: string;
  status: string;
  identity: string;
  room: string;
  role: string;
  trust_boundary: string;
};

export type AgentDetail = {
  agent: RegistryAgent;
  desk: OfficeDesk | null;
  rooms: Array<{ id: string; title: string; kind: string; topic: string }>;
  messages: Array<RoomMessage & { room_title?: string }>;
  handoffs: Handoff[];
};

export const api = {
  health: () => get<{ ok: boolean }>("/api/health"),
  run: () => post<Bundle>("/api/loop/run"),
  seedWorld: () => post<{ rooms: string[]; scenarios: Array<Record<string, unknown>> }>("/api/world/seed"),
  rooms: () => get<{ rooms: Room[] }>("/api/rooms"),
  room: (id: string) => get<RoomDetail>(`/api/rooms/${id}`),
  postRoom: (id: string, text: string) => post<RoomDetail>(`/api/rooms/${id}/messages`, { author: "you", text }),
  registry: () => get<{ agents: RegistryAgent[] }>("/api/registry"),
  memory: () =>
    get<{
      memory: Record<string, Array<Record<string, unknown>>>;
      lessons: Array<Record<string, unknown>>;
    }>("/api/memory"),
  traces: () =>
    get<{ traces: Array<Record<string, unknown>>; verdicts: Array<Record<string, unknown>> }>("/api/traces"),
  scenarios: () => get<{ scenarios: Array<Record<string, unknown>> }>("/api/scenarios"),
  investigations: () =>
    get<{
      investigations: Array<
        Investigation & { hypothesis?: string; confidence?: number; risk_tier?: string; action_status?: string }
      >;
    }>("/api/investigations"),
  investigation: (id: string) => get<Bundle>(`/api/investigations/${id}`),
  signals: () => get<{ signals: Array<Record<string, unknown>> }>("/api/signals"),
  approvals: () =>
    get<{
      pending: Action[];
      history: Array<Record<string, unknown>>;
      gate?: { mode: string; tenant_repo: string; label: string };
    }>("/api/approvals"),
  approve: (actionId: string, decision: "approve" | "deny") =>
    post(`/api/approvals/${actionId}`, {
      decision,
      approver: "you@product-os",
      rationale:
        decision === "approve"
          ? "Evidence pack and risk gate reviewed in-room."
          : "Need more evidence before this change ships.",
    }),
  outcomes: () => get<{ outcomes: Array<Record<string, unknown>> }>("/api/outcomes"),
  governance: () =>
    get<{
      identities: Array<{ id: string; envelope: string }>;
      verdicts: Array<Record<string, unknown>>;
      failOpen: boolean;
    }>("/api/governance"),
  tenants: () => get<{ tenants: Tenant[]; gate?: { mode: string; tenant_repo: string; label: string } }>("/api/tenants"),
  tenant: (id: string) => get<{ tenant: Tenant; flags: Record<string, string> }>(`/api/tenants/${id}`),
  upsertTenant: (body: {
    id: string;
    name: string;
    product: string;
    repo: string;
    deploy_url: string;
    token?: string;
  }) => post<{ tenant: Tenant }>("/api/tenants", body),
  rotateToken: (id: string, token: string) =>
    post<{ rotated: boolean; tenant: Tenant }>(`/api/tenants/${id}/token`, { token }),
  opportunities: () => get<{ opportunities: Array<Record<string, unknown>> }>("/api/opportunities"),
  office: () => get<OfficeSnapshot>("/api/office"),
  agents: () =>
    get<{
      agents: Array<{
        id: string;
        room: string;
        role: string;
        tb: string;
        status: string;
        owner?: string;
        identity?: string;
        risk_level?: string;
      }>;
    }>("/api/agents"),
  agent: (id: string) => get<AgentDetail>(`/api/agents/${id}`),
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
