import { canonicalAgentId } from "./names";

const BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8080");

const ADMIN_TOKEN_ENV = process.env.NEXT_PUBLIC_LOOP_ADMIN_TOKEN ?? "";
const ADMIN_STORAGE_KEY = "loop_admin_token";
const ADMIN_REMEMBER_KEY = "loop_admin_token_remember";

function readStoredAdminToken(): string {
  if (typeof window === "undefined") return "";
  const session = window.sessionStorage.getItem(ADMIN_STORAGE_KEY);
  if (session) return session;
  if (window.localStorage.getItem(ADMIN_REMEMBER_KEY) === "1") {
    return window.localStorage.getItem(ADMIN_STORAGE_KEY) || "";
  }
  return "";
}

export function adminRememberEnabled(): boolean {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(ADMIN_REMEMBER_KEY) === "1";
}

function adminToken(): string {
  const stored = readStoredAdminToken();
  if (stored) return stored;
  return ADMIN_TOKEN_ENV;
}

export function hasAdminToken(): boolean {
  return Boolean(adminToken());
}

function adminHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = adminToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

export function setAdminToken(token: string, remember = false) {
  if (typeof window === "undefined") return;
  const trimmed = token.trim();
  window.sessionStorage.setItem(ADMIN_STORAGE_KEY, trimmed);
  if (remember) {
    window.localStorage.setItem(ADMIN_STORAGE_KEY, trimmed);
    window.localStorage.setItem(ADMIN_REMEMBER_KEY, "1");
  } else {
    window.localStorage.removeItem(ADMIN_STORAGE_KEY);
    window.localStorage.removeItem(ADMIN_REMEMBER_KEY);
  }
}

export function clearAdminToken() {
  if (typeof window === "undefined") return;
  window.sessionStorage.removeItem(ADMIN_STORAGE_KEY);
  window.localStorage.removeItem(ADMIN_STORAGE_KEY);
  window.localStorage.removeItem(ADMIN_REMEMBER_KEY);
}

export async function verifyAdminToken(token: string, remember = false): Promise<boolean> {
  const res = await fetch(`${BASE}/api/admin/verify`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token.trim()}`, "Content-Type": "application/json" },
    credentials: "same-origin",
  });
  if (!res.ok) return false;
  setAdminToken(token, remember);
  return true;
}

async function get<T>(path: string, opts?: { admin?: boolean }): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    cache: "no-store",
    credentials: "same-origin",
    headers: opts?.admin ? adminHeaders() : undefined,
  });
  if (!res.ok) throw new Error(`${path} ${res.status}`);
  return res.json();
}

async function recoverApproval(path: string): Promise<Record<string, unknown> | null> {
  const m = path.match(/^\/api\/approvals\/([^/]+)$/);
  if (!m) return null;
  const actionId = m[1];
  for (let i = 0; i < 40; i++) {
    await new Promise((r) => window.setTimeout(r, 500));
    try {
      const st = await get<{
        status: string;
        execution: Record<string, unknown>;
        pr_url?: string;
      }>(`/api/approvals/${actionId}/status`);
      if (st.status === "executed" || st.status === "denied" || st.status === "approved") {
        return {
          approval: st.status === "denied" ? "deny" : "approve",
          execution: st.execution,
          pr_url: st.pr_url,
          recovered: true,
        };
      }
    } catch {
      /* keep polling */
    }
  }
  return null;
}

async function post<T>(path: string, body?: unknown, opts?: { admin?: boolean }): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: opts?.admin ? adminHeaders() : { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : "{}",
    credentials: "same-origin",
  });
  if (!res.ok) {
    if (res.status === 401 && path.includes("/api/approvals/")) {
      throw new Error(
        "Admin token required — open Connect, paste LOOP_ADMIN_TOKEN, click Authorize, then try again."
      );
    }
    let detail = `${path} ${res.status}`;
    try {
      const j = await res.json();
      if (typeof j?.detail === "string") detail = j.detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  try {
    return (await res.json()) as T;
  } catch {
    const recovered = await recoverApproval(path);
    if (recovered) return recovered as T;
    throw new Error(
      "Connection dropped while approving. The change may still have applied — refresh the room or Approvals."
    );
  }
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
  flag_names?: string[];
  code_paths?: string[];
  flag_file_path?: string;
  stack?: string;
  test_command?: string;
  default_surface?: string;
  metric_catalog?: string[];
  bq_project?: string;
  bq_raw_dataset?: string;
  bq_metrics_dataset?: string;
  ga4_property_id?: string;
  ga4_dataset?: string;
  ads_dataset?: string;
  ads_customer_id?: string;
  warehouse_mode?: string;
  primary_metric?: string;
  funnel_events?: string[];
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
  tenant?: { id: string; name: string; product: string; repo?: string } | null;
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
  resources?: Array<Record<string, unknown>>;
};

export const api = {
  health: () => get<{ ok: boolean }>("/api/health"),
  status: () =>
    get<{
      ok: boolean;
      rooms: { total: number; open: number; by_kind: Record<string, number> };
      approvals_pending: number;
      engaged?: number;
      verified?: number;
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
    get<{
      traces: Array<Record<string, unknown>>;
      threads?: Array<{
        investigation_id: string;
        room_id?: string | null;
        title: string;
        kind?: string | null;
        members?: string[];
        events: Array<Record<string, unknown>>;
        latest_at?: string;
      }>;
      verdicts: Array<Record<string, unknown>>;
    }>("/api/traces"),
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
    }>(
      `/api/approvals/${actionId}`,
      {
        decision,
        approver: "you@product-os",
        rationale:
          decision === "approve"
            ? "Evidence pack and risk gate reviewed in-room."
            : "Need more evidence before this change ships.",
      },
      { admin: true }
    ),
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
  tenants: () => get<{ tenants: Tenant[]; gate?: { mode: string; tenant_repo: string; label: string } }>("/api/tenants", { admin: true }),
  tenant: (id: string) => get<{ tenant: Tenant; flags: Record<string, string> }>(`/api/tenants/${id}`, { admin: true }),
  onboardServices: (opts?: { project?: string; region?: string }) => {
    const q = new URLSearchParams();
    if (opts?.project) q.set("project", opts.project);
    if (opts?.region) q.set("region", opts.region);
    const qs = q.toString();
    return get<{
      status: string;
      detail?: string;
      project: string;
      region: string;
      services: Array<{ id: string; name: string; url: string; repo_hint?: string }>;
    }>(`/api/onboard/services${qs ? `?${qs}` : ""}`, { admin: true });
  },
  onboardTenant: (body: {
    cloud_run_service?: string;
    repo: string;
    region?: string;
    project?: string;
    tenant_id?: string;
    name?: string;
    product?: string;
    deploy_url?: string;
    wire?: boolean;
  }) =>
    post<{
      status: string;
      tenant_id: string;
      tenant: Tenant;
      token?: string;
      token_once?: boolean;
      os_url?: string | null;
      wire?: { status: string; detail?: string; url?: string; hint?: string; manual?: string };
      cloud_run?: Record<string, unknown>;
      next?: string[];
    }>("/api/tenants/onboard", body, { admin: true }),
  verifyTenant: (id: string) =>
    post<{
      status: string;
      tenant_id: string;
      checks: Array<{ id: string; ok: boolean; label: string; detail?: string; room_id?: string }>;
      ok: number;
      total: number;
      room_id?: string | null;
      ready?: boolean;
      ready_for_demo?: boolean;
    }>(`/api/tenants/${id}/verify`, {}, { admin: true }),
  incidentLifecycle: (id: string, metric = "checkout_conversion") =>
    get<{
      status: string;
      tenant_id: string;
      checkout_url?: string | null;
      deploy_url?: string | null;
      room_id?: string | null;
      investigation_id?: string | null;
      investigation_state?: string | null;
      pending_action_id?: string | null;
      execution?: { pr_url?: string; flag?: string } | null;
      steps: Array<{
        id: string;
        label: string;
        detail?: string;
        done: boolean;
        active?: boolean;
        href?: string | null;
        room_id?: string | null;
        action_id?: string | null;
      }>;
      progress: { done: number; total: number };
      ready_for_checkout?: boolean;
      pay_sdk_active?: string;
      regression_active?: boolean;
      phase?: string;
      headline?: string;
      subtitle?: string;
      product_status?: string;
      last_ingest_at?: string | null;
      flags?: Record<string, string>;
    }>(`/api/tenants/${id}/incident-lifecycle?metric=${encodeURIComponent(metric)}`, { admin: true }),
  armIncident: (id: string) =>
    post<{ status: string; tenant_id?: string; flag?: string; value?: string; lifecycle: Record<string, unknown> }>(
      `/api/tenants/${id}/incident-lifecycle/arm`,
      {},
      { admin: true }
    ),
  upsertTenant: (body: {
    id: string;
    name: string;
    product: string;
    repo: string;
    deploy_url: string;
    token?: string;
    flag_names?: string[];
    code_paths?: string[];
    flag_file_path?: string;
    stack?: string;
    test_command?: string;
    default_surface?: string;
    metric_catalog?: string[];
    bq_project?: string;
    bq_raw_dataset?: string;
    bq_metrics_dataset?: string;
    ga4_property_id?: string;
    ga4_dataset?: string;
    ads_dataset?: string;
    ads_customer_id?: string;
    warehouse_mode?: string;
    primary_metric?: string;
    funnel_events?: string[];
  }) => post<{ tenant: Tenant }>("/api/tenants", body, { admin: true }),
  rotateToken: (id: string, token: string) =>
    post<{ rotated: boolean; tenant: Tenant }>(`/api/tenants/${id}/token`, { token }, { admin: true }),
  oauth: () => get<GoogleOAuth>("/api/oauth/google"),
  ga4Status: () => get<{ ready: boolean }>("/api/oauth/ga4/status"),
  saveGoogleClient: (client_id: string, client_secret: string) =>
    post<GoogleOAuth>("/api/oauth/google/client", { client_id, client_secret }, { admin: true }),
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
    apply_calendar?: boolean;
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
  calendarSuggest: (body?: { duration_minutes?: number; limit?: number }) =>
    post<{
      status?: string;
      connector?: string;
      slots?: Array<{ start: string; end: string; duration_minutes?: number }>;
      detail?: string;
    }>("/api/calendar/suggest", body ?? { limit: 5 }),
  placeCall: (body: {
    to_number?: string;
    reason?: string;
    room_id?: string;
    product?: string;
    tokenized_user?: string;
    force?: boolean;
    purpose?: string;
  }) =>
    post<{
      report: { status: string; connector: string; detail: string; url?: string | null };
      resolved?: {
        phone?: string | null;
        email?: string | null;
        found: boolean;
        detail?: string;
        feedback?: string;
      } | null;
      to_number?: string | null;
      gate?: { allowed?: boolean; reason?: string; detail?: string };
      purpose?: string;
    }>("/api/calls", body),
  roomContact: (roomId: string) =>
    get<{
      phone?: string | null;
      email?: string | null;
      found: boolean;
      detail?: string;
      feedback?: string;
      source?: string;
      tokenized_user?: string | null;
    }>(`/api/rooms/${roomId}/contact`),
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
  agent: (id: string) => get<AgentDetail>(`/api/agents/${canonicalAgentId(id)}`),
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
      investigators_fanout?: string[];
      adopted_patterns?: string[];
      hitl?: Record<string, unknown>;
      note?: string;
      enterprise?: Record<string, string>;
    }>("/api/workflows"),
  workflowLinks: () =>
    get<{
      oauth: { connected: boolean; email: string; authorize_path: string };
      calendar: { oauth: boolean; mode: string; detail: string; tools: string[] };
      links: Array<{
        kind: string;
        label: string;
        url: string;
        room_id?: string | null;
        detail?: string;
        simulated?: boolean;
      }>;
      shortcuts: Array<{ kind: string; label: string; url: string }>;
      workflows_href: string;
    }>("/api/workflows/links"),
  metrics: () =>
    get<{
      idea_to_impact_hours_mean: number | null;
      idea_to_impact_target_hours: number;
      baseline_manual_hours: number;
      investigations: number;
      resolved: number;
      failOpen: boolean;
    }>("/api/metrics"),
  pipeline: () =>
    get<{
      columns: string[];
      column_labels?: Record<string, string>;
      cards: Array<{
        room_id: string;
        title: string;
        stage: string;
        kind: string;
        workflow?: {
          nodes?: string[];
          steps?: Array<{ id: string; label: string; short?: string; detail?: string; on?: boolean }>;
          current?: string;
          needs?: Record<string, boolean>;
          tags?: string[];
        };
        tenant_id?: string | null;
        tenant_product?: string | null;
        scenario_id?: string | null;
        investigation_id?: string | null;
        awaiting_approval?: boolean;
        pending_action_id?: string | null;
        pr_url?: string | null;
        evidence_snippet?: string | null;
        calendar_snippet?: string | null;
        calendar_url?: string | null;
        meet_url?: string | null;
        gmail_url?: string | null;
        voice_snippet?: string | null;
        contact_phone?: string | null;
        call_feedback?: string | null;
        warehouse_snippet?: string | null;
        code_snippet?: string | null;
        activity_line?: string | null;
        activity_author?: string | null;
        verified?: boolean;
        denied?: boolean;
        active_agents?: string[];
      }>;
      focus?: {
        steps: Array<{
          n: number;
          id: string;
          short: string;
          label: string;
          detail: string;
          stage: string;
          on?: boolean;
        }>;
        current?: string | null;
        kind?: string | null;
        needs?: Record<string, boolean>;
        tags?: string[];
        room_id?: string | null;
      };
    }>("/api/pipeline"),
  workflowFocus: () =>
    get<{
      mode?: "watching" | "active";
      watch_line?: string | null;
      signal_agent?: { status?: string; detail?: string };
      steps: Array<{
        n: number;
        id: string;
        short: string;
        label: string;
        detail: string;
        stage: string;
        on?: boolean;
        status?: string;
        agent?: string;
      }>;
      handoffs?: Array<{ from: string; to: string; why: string; from_node?: string; to_node?: string }>;
      current?: string | null;
      kind?: string | null;
      needs?: Record<string, boolean>;
      tags?: string[];
      room_id?: string | null;
    }>("/api/workflows/focus"),
  orchestrationHome: () =>
    get<{
      mode?: "watching" | "active";
      watch_line?: string | null;
      signal_agent?: { status?: string; detail?: string };
      steps?: Array<Record<string, unknown>>;
      handoffs?: Array<Record<string, unknown>>;
      room_id?: string | null;
    }>("/api/orchestration/home"),
  liveWork: () =>
    get<{
      columns: Array<{ id: string; label: string; count: number }>;
      cards: Array<{
        id: string;
        column: string;
        badge: string;
        text: string;
        agent: string;
        room_id: string;
        room_title?: string;
        tenant_product?: string | null;
        artifact_type?: string | null;
        phone?: string | null;
        metric?: string | null;
        source?: string | null;
        created_at?: string;
        pr_url?: string | null;
        gmail_url?: string | null;
        calendar_url?: string | null;
        meet_url?: string | null;
        bq_url?: string | null;
        action_id?: string;
        proof?: Record<string, unknown> | null;
      }>;
      stats: Record<string, number>;
    }>("/api/live-work"),
  proof: () =>
    get<{
      warehouse?: Record<string, unknown> | null;
      github?: Record<string, unknown> | null;
      ga4?: Record<string, unknown> | null;
      logs?: Record<string, unknown> | null;
      deploys?: Record<string, unknown> | null;
      ads?: Record<string, unknown> | null;
      contacts?: Record<string, unknown> | null;
      flags?: Record<string, unknown> | null;
      memory?: Record<string, unknown> | null;
      workspace?: Record<string, unknown> | null;
      gateway?: Record<string, unknown> | null;
      cards?: Array<Record<string, unknown>>;
      tenant_id?: string | null;
      tenant_product?: string | null;
    }>("/api/proof"),
  proofResources: (opts?: { agent?: string; signal?: string; arm?: string }) => {
    const q = new URLSearchParams();
    if (opts?.agent) q.set("agent", opts.agent);
    if (opts?.signal) q.set("signal", opts.signal);
    if (opts?.arm) q.set("arm", opts.arm);
    const qs = q.toString();
    return get<{ scope: string; id: string; cards: Array<Record<string, unknown>> }>(
      `/api/proof/resources${qs ? `?${qs}` : ""}`
    );
  },
  activity: () =>
    get<{
      events: Array<{
        ts?: string;
        agent_id?: string;
        message?: string;
        room_id?: string;
        stage?: string;
        tenant_id?: string;
      }>;
    }>("/api/activity"),
  demoRun: () =>
    post<{
      demo: boolean;
      tenant_id: string;
      room_id?: string;
      investigation_id?: string;
      joined?: boolean;
      async?: boolean;
    }>("/api/demo/run"),
  config: () =>
    get<{ eval_mode: boolean; hosted: boolean; fixture_scenarios?: string[] }>("/api/config"),
};

/** Same-origin or NEXT_PUBLIC_API_URL WebSocket for a room. */
export function roomSocket(roomId: string): WebSocket {
  const http = BASE || (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8080");
  const ws = http.replace(/^http/, "ws");
  return new WebSocket(`${ws}/ws/rooms/${roomId}`);
}

/** Campus-wide WebSocket — activity log + pipeline refresh. */
export function globalSocket(): WebSocket {
  const http = BASE || (typeof window !== "undefined" ? window.location.origin : "http://127.0.0.1:8080");
  const ws = http.replace(/^http/, "ws");
  return new WebSocket(`${ws}/ws`);
}
