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

export type GoogleOAuth = {
  configured: boolean;
  connected: boolean;
  email: string;
  redirect_uri: string;
  scopes: string[];
  authorize_path: string;
  authorize_url: string;
  console: { overview: string; create_client: string; audience: string };
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
  presence?: Array<{ agentId: string; status: string; pixel?: Record<string, unknown> }>;
  funnel?: { steps: Array<{ id: string; label: string; on: boolean }>; current: string; kind: string };
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
  status: () =>
    get<{
      ok: boolean;
      rooms: { total: number; open: number; by_kind: Record<string, number> };
      approvals_pending: number;
      presence: { agents: number; by_status: Record<string, number> };
      funnel: { signal: number; approve: number; learn: number };
      workspace: { connected: boolean; email: string };
      patterns: string[];
    }>("/api/status"),
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
  postSignal: (body: {
    source?: string;
    polarity?: string;
    domain?: string;
    metric: string;
    delta?: number;
    title?: string;
    dimensions?: Record<string, unknown>;
    fork?: string;
    scenario?: string;
  }) =>
    post<{
      signalId: string;
      roomId: string;
      room_id: string;
      trace_id: string;
      fork: string;
      pipeline?: string[];
      steps?: number;
    }>("/api/signals", body),
  rememberMemory: (body: {
    type: string;
    title: string;
    body?: string;
    tags?: string[];
    room_id?: string;
  }) => post<Record<string, unknown>>("/api/memory", body),
  trace: (id: string) => get<Record<string, unknown>>(`/api/traces/${id}`),
  approvals: () =>
    get<{
      pending: Action[];
      history: Array<Record<string, unknown>>;
      gate?: { mode: string; tenant_repo: string; label: string };
    }>("/api/approvals"),
  approve: (actionId: string, decision: "approve" | "deny") =>
    post<{
      approval: unknown;
      outcome?: Record<string, unknown>;
      execution?: {
        flag?: string;
        value?: string;
        pr_url?: string;
        pr_opened?: boolean;
        merged?: boolean;
        job_id?: string;
        code_fix?: string | { status?: string; job_id?: string };
      };
      pr_url?: string;
    }>(`/api/approvals/${actionId}`, {
      decision,
      approver: "you@product-os",
      rationale:
        decision === "approve"
          ? "Evidence pack and risk gate reviewed in-room."
          : "Need more evidence before this change ships.",
    }),
  approvalStatus: (actionId: string) =>
    get<{
      action_id: string;
      status: string;
      execution: Record<string, unknown>;
      job: { id: string; status: string; result?: Record<string, unknown>; error?: string } | null;
      pr_url?: string;
    }>(`/api/approvals/${actionId}/status`),
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
  oauth: () => get<GoogleOAuth>("/api/oauth/google"),
  saveGoogleClient: (client_id: string, client_secret: string) =>
    post<GoogleOAuth>("/api/oauth/google/client", { client_id, client_secret }),
  telephony: () =>
    get<{
      twilio: boolean;
      gemini: boolean;
      google_inbound?: boolean;
      google_outbound?: boolean;
      mode: string;
      detail: string;
    }>("/api/telephony"),
  adkStatus: () =>
    get<{
      adk_installed: boolean;
      adk_inline: boolean;
      adk_worker_url: string | null;
      worker_reachable: boolean;
      fleet: Record<string, unknown> | null;
      antigravity: {
        installed: boolean;
        configured: boolean;
        backend_preference: string;
        preview: boolean;
        note: string;
      };
      code_backend: string;
      pitch: string;
    }>("/api/adk/status"),
  research: (body: {
    kind: string;
    user_id: string;
    title?: string;
    topic?: string;
    phone?: string;
    dimensions?: Record<string, unknown>;
    memory_conditions?: string[];
    place_real_call?: boolean;
    scenario_id?: string;
  }) => post<Record<string, unknown>>("/api/research", body),
  improve: (body: {
    kind: string;
    metric: string;
    magnitude?: number;
    baseline?: number;
    title?: string;
    polarity?: "negative" | "positive";
    loop_type?: string;
    dimensions?: Record<string, unknown>;
    memory_conditions?: string[];
    scenario_id?: string;
    simulate_outcome?: boolean;
  }) => post<Record<string, unknown>>("/api/improve", body),
  coordinate: (body: {
    kind?: string;
    title: string;
    subject?: string;
    surface?: string;
    risk_tier?: string;
    owners?: string[];
    duration_minutes?: number;
    prefer_meet?: boolean;
    notify_channels?: string[];
    room_id?: string;
    action_id?: string;
    pr_url?: string;
    dimensions?: Record<string, unknown>;
  }) => post<Record<string, unknown>>("/api/coordinate", body),
  signalsCatalog: () => get<Record<string, unknown>>("/api/signals/catalog"),
  investigate: (body: {
    kind: string;
    metric: string;
    title?: string;
    family?: string;
    magnitude?: number;
    baseline?: number;
    dimensions?: Record<string, unknown>;
    scenario_id?: string;
  }) => post<Record<string, unknown>>("/api/investigate", body),
  productIntel: (body: {
    mentions: Array<{ text: string; user_id?: string; channel?: string; revenue_hint_usd?: number }>;
    theme?: string;
    title?: string;
    scenario_id?: string;
    revenue_affected_usd?: number;
  }) => post<Record<string, unknown>>("/api/product-intel", body),
  calendar: () => get<{ oauth: boolean; mode: string; detail: string; tools: string[] }>("/api/calendar"),
  placeCall: (body: { to_number: string; reason?: string; room_id?: string; product?: string }) =>
    post<{ report: { status: string; connector: string; detail: string; url?: string | null } }>(
      "/api/calls",
      body,
    ),
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
  scenarioRun: (slug: string) =>
    post<{
      scenario: string;
      room_id: string;
      room: Room;
      funnel?: RoomDetail["funnel"];
      pipeline?: string[];
      trace_id?: string;
      steps?: number;
      presence?: RoomDetail["presence"];
    }>(`/api/scenarios/${slug}/run`),
  workflows: () =>
    get<{
      adk_version: string;
      preferred_2x?: string[];
      investigation_fanout?: string;
      proposal_critique?: string;
      note?: string;
      enterprise?: Record<string, string>;
    }>("/api/workflows"),
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

/** Same-origin or NEXT_PUBLIC_API_URL WebSocket for a room. */
export function roomSocket(roomId: string): WebSocket {
  const http = BASE || (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8080");
  const ws = http.replace(/^http/, "ws");
  return new WebSocket(`${ws}/ws/rooms/${roomId}`);
}
