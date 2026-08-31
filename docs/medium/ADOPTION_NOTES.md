# Adoption notes — external patterns and production gaps

| Field | Value |
|---|---|
| Purpose | What we borrowed from common ADK multi-agent patterns, and gaps to close before publish |
| Our mapping | [`HACKATHON_STORY.md`](../HACKATHON_STORY.md) · [`GOOGLE_OPEN_SOURCE_LEARNINGS.md`](../GOOGLE_OPEN_SOURCE_LEARNINGS.md) |
| Draft posts | [`ARCHITECTURE_POST.md`](ARCHITECTURE_POST.md) · [`TUTORIAL_POST.md`](TUTORIAL_POST.md) |

Common ADK hackathon and tutorial patterns — real-time dashboards, parallel fan-out, OAuth toolsets, BigQuery analytics — map cleanly onto Product OS. We integrated the useful parts and diverged where production safety and ADK 2.8 require it.

---

## Patterns we adopted (and where they landed)

| Common pattern | Our take | Production gap to close |
|---|---|---|
| **Real-time command center** — WebSocket dashboard, live agent status | Campus + multi-room chat, `FunnelChips`, `/ws/rooms/:id`, `GET /api/status` | Publish a **60s demo video** and status-strip screenshots |
| **Parallel fan-out → merge** — multiple investigators in parallel | ADK 2 `Workflow` + `JoinNode` in `investigation_fanout`; deterministic engine on Cloud Run | Surface **`GET /api/workflows`** in the console |
| **Sequential QA loop** — draft → critique | FEATURE path: product draft → feedback critique loop | Generic across fixtures, not one demo scenario |
| **BigQuery as shared memory** | GA4 → `analytics_*`, `loop_raw`, `loop_metrics`, tenant `warehouse_mode: auto` | Real tenant analytics wired via Connect |
| **Pub/Sub between services** | `loop.signals` on tenant ingest | Document push + pull hybrid (Product Y signals + BQ warehouse) |
| **Human-in-the-loop** | HIGH approvals, idempotent replay, no auto-merge | Persisted gate survives restart |
| **One-command deploy** | `./scripts/boot.sh`, `deploy-gcp.sh` | Add a **Colab / notebook** path for OAuth + warehouse |

---

## OAuth and Workspace patterns (and our twist)

| Common pattern | Our take | Production gap to close |
|---|---|---|
| **Beginner OAuth walkthrough** | Connect desk + `/api/oauth/google/*` for Gmail draft / Calendar hold | Publish step-by-step: Web client, redirect URI, hosted callback |
| **`adk_request_credential` handshake** | Hosted OAuth (`/api/oauth/ga4/start`, GCS `ga4_adc.json`) | Contribute upstream ADK sample: production redirect URI pattern |
| **Service account + domain-wide delegation** | **Deliberately not shipped** — `send_gmail` denied; user refresh token only | Document **why** (PRD safety); optional SA appendix for enterprise |
| **GmailToolset / CalendarToolset** | Custom connectors in `loop/connectors/` with apply / skip / denied | ADK 2 sample: Connect + tenant + `ToolOutputArmorPlugin` |
| **Single OAuth client for everything** | GA4 needs **`analytics.edit`**, separate from Workspace OAuth | Second OAuth flow; Analytics Admin `v1alpha` for BigQuery links |

---

## Where Product OS goes further than typical ADK demos

1. **Trust boundaries** — seven ADK `App`s (TB-1…TB-7); exfil DENY by Gateway identity, not prompt.
2. **Evidence bar** — root cause requires ≥3 independent source groups (analytics, logs, deploy, …).
3. **ADK 2.8** — `Workflow`, `JoinNode`, `ModelArmorPlugin` + mandatory **`ToolOutputArmorPlugin`** on tool output (M-10 gap in stock Model Armor).
4. **Hybrid engine** — hosted Cloud Run runs deterministic loop without Gemini quota; ADK fleet for eval/worker.
5. **Tenant split** — Cove is Product Y on its own origin; OS is control plane only (not a demo shop on `loop`).
6. **Real warehouse path** — GA4 property, streaming export, tenant Connect fields.

---

## Production gaps to close (prioritized)

| Priority | Idea | Why |
|---|---|---|
| P0 | **Hosted OAuth cookbook** (Workspace + GA4) | Scattered docs + localhost redirects are the main onboarding pain — publish [`TUTORIAL_POST.md`](TUTORIAL_POST.md) |
| P0 | **Demo video + architecture diagram** | Show the orchestra, not just the repo |
| P1 | **“Connect in 10 minutes” notebook** | Colab-style path for tenant + BQ + GA4 |
| P1 | **Workflow visibility in UI** | Make ADK 2 graphs legible in the console |
| P2 | **Open-source ADK contributions** | [`GOOGLE_OPEN_SOURCE_LEARNINGS.md`](../GOOGLE_OPEN_SOURCE_LEARNINGS.md) — migration guide, tool-output armor sample |
| P2 | **Optional Twilio voice chapter** | Simulate-first + Twilio trial path for diagnostic calls |

---

## Deliberate divergences from typical hackathon stacks

| Typical demo stack | Product OS |
|---|---|
| Domain-specific automation (sales, support, …) | **Generic** product loop; any tenant, any fixture |
| Many Cloud Run microservices | One control plane + optional ADK worker; deterministic hosted path |
| Gmail send via service account | **Draft only**; `send_gmail` denied until explicit product decision |
| ADK 1.x `SequentialAgent` / `ParallelAgent` / `LoopAgent` | **ADK 2.8 Workflow** + trust-boundary `App`s |
| CRUD dashboard | **Campus + rooms + approvals tram** — chat-native |
| Third-party voice for outbound | Simulate-first; optional Twilio; no Google outbound PSTN |

---

## Pattern mapping (code locations)

See [`HACKATHON_STORY.md`](../HACKATHON_STORY.md) for the full table. Highlights:

| Pattern | Product OS location |
|---|---|
| Agent callback → UI fan-out | `/api/agent_callback` → Hub |
| Skip-if-done HITL | Approve reuse + `callbacks.py` |
| Parallel fan-out / merger | `investigation_fanout` Workflow + JoinNode |
| Funnel status chips | Room `FunnelChips` + `funnel_stage` WS events |
| BigQuery analytics | `loop/connectors/bigquery.py` + tenant warehouse fields |
| Gmail / Calendar | `loop/connectors/mail.py`, `calendar.py` + Workspace OAuth |

We did **not** ship: domain-wide Gmail send via service account, unsandboxed outbound voice, many separate agent services, or a tenant storefront on the OS origin.
