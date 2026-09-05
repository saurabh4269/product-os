# Enterprise track — ADK 2.0 + GEAP alignment (honest)

| Field | Value |
|---|---|
| Status | Reference for judges / pilot buyers |
| Production plan | [`PLAN_PRODUCTION.md`](PLAN_PRODUCTION.md) |
| Live | https://loop-5uy6fkd7bq-uc.a.run.app |

This document states what LOOP ships **today** on cheap GCP vs what requires GEAP entitlements (Agent Gateway, SGP, managed Agent Runtime, cloud Memory Bank).

---

## What is production-real now

| Capability | Implementation | Honest limit |
|---|---|---|
| **Durable state** | Full SQLite ↔ `LOOP_STATE_GCS_URI` | Not Cloud SQL yet (P1) |
| **Background jobs** | `jobs` table + Cloud Tasks (`loop-jobs`) with inline thread fallback | Single-region; no multi-worker autoscale |
| **Code fix v2** | Clone → patch → vitest → PR; fail-closed on red tests | Deterministic Safari path; Gemini when `GOOGLE_API_KEY` set |
| **HITL approvals** | Persisted with state; console polls `/api/approvals/{id}/status` | Approver SSO is P1 |
| **Audit log** | Append-only `audit` table; admin `GET /api/audit` | No SIEM export yet |
| **Admin auth** | `LOOP_ADMIN_TOKEN` on tenant admin, jobs, worker | Console approvals stay open (demo) |
| **Model Armor** | Layered: GCP API best-effort + deterministic needles (`model_armor.py`) | Not GEAP Agent Gateway enforcement |
| **Pub/Sub signals** | `publish_signal()` on tenant ingest → `loop.signals` | BQ warehouse read path when dataset configured |
| **Gateway identity** | Local `gateway.py` + `registry.py`; exfil DENY by identity | `failOpen=false` in TF; cloud gateway plan-only |
| **Twilio voice** | Trial + simulated fallback | No outbound Google PSTN |
| **Workspace OAuth** | Gmail draft / Calendar hold; send denied | Not full MCP surface |

---

## ADK 2.0 artifacts (local / eval, not hosted runtime)

The repo contains a full **ADK 2.0-shaped fleet** for tests and local dev:

- **23 LlmAgents**, **7 Apps**, Workflows + JoinNode in `services/loop/loop/agents/`
- `ToolOutputArmorPlugin` on `after_tool_callback` (M-10 gap in stock ModelArmorPlugin)
- `run_live_graph()` for scenario eval (`POST /api/scenarios/{slug}/run`)

**Hosted Cloud Run** runs the deterministic `LoopEngine` path. It does **not** import `google-adk` in `requirements-host.txt` — by design for cold-start cost and hackathon reliability.

When GEAP Agent Runtime is entitled, the same agent configs deploy to managed runtime; the console and store schema stay unchanged.

**Cost posture (2026-09-05):** Hosted `loop` is thin glue — observe → investigate (ADK worker when `LOOP_ADK_WORKER_URL` set) → connectors → risk gate → receipts. Homemade `LoopEngine`, `gateway.py`, and SQLite/Firestore memory are **stand-ins** for GEAP Agent Runtime, Agent Gateway, and Memory Bank. Do not expand them without entitlements; prefer `loop-adk` scale-to-zero and a single brain path. Product UI, HITL approvals, and tenant PR workflow stay regardless of GEAP migration.

---

## Security model (judge narrative)

1. **Identity before prompt** — production customer exfil is DENY via Gateway/registry identity, not a model instruction.
2. **Tool-output armor** — untrusted GitHub/issue text screened before it reaches analysis (`screen_tool_output` → Model Armor + needles).
3. **Fail closed** — empty tool output blocks; `LOOP_CODE_REQUIRE_TESTS=1` blocks PR on red tests; admin APIs require bearer on hosted.
4. **No merge** — Product OS opens PRs on tenant repos; humans merge.

---

## Plan-only until GEAP

- GEAP **Agent Gateway** + SGP as enforcement plane (Terraform in `infra/terraform/gated/`)
- **Cloud Memory Bank** full consolidation (Firestore mirror + optional GEAP adapter today)
- **Antigravity** as sole code path (jobs worker uses clone + apply + test today)
- Outbound **Google PSTN** / Live API media bridge at scale

### GEAP Agent Runtime (wired, opt-in)

| Piece | Status | Notes |
|---|---|---|
| **Runtime client** | `services/loop/loop/geap_runtime.py` | `vertexai.Client` + `AdkApp` around LOOP orchestrator |
| **Deploy** | `scripts/deploy-geap-agent.sh` | Creates Reasoning Engine with `identity_type=AGENT_IDENTITY` |
| **Routing** | `LOOP_GEAP_ENABLED=1` + `LOOP_GEAP_AGENT_ENGINE_ID` | `POST /api/signals` → GEAP query → local LoopEngine persistence |
| **Memory Bank** | `services/loop/loop/geap_memory.py` | `VertexAiMemoryBankService` when engine id set; SQLite/Firestore fallback |
| **Status** | `GET /api/geap/status`, `/api/adk/status` | Honest skipped_reason when SDK or engine id missing |
| **Gateway** | Plan-only | Not required for first Runtime ship — Identity on create is enough |

Env checklist (GEAP):

```
LOOP_GEAP_ENABLED=1
LOOP_GEAP_AGENT_ENGINE_ID=projects/.../locations/.../reasoningEngines/<id>   # full resource name
LOOP_GEAP_STAGING_BUCKET=gs://mystical-timing-442601-q8-loop-host
GOOGLE_CLOUD_PROJECT=mystical-timing-442601-q8
GOOGLE_CLOUD_REGION=us-central1
```

Live probe (2026-09-05): use ``vertexai.Client(...).agent_engines`` for create/list — **not** ``agentplatform.Client`` (no ``agent_engines`` yet). Agent Engine create requires ``cloudpickle`` + ``pydantic`` in requirements. Model: ``config/models.yaml`` primary (``gemini-3.5-flash``), fallback ``gemini-2.5-flash`` on deploy failure.

IAM: deployer needs `roles/aiplatform.user` and write access to the staging bucket. Main `loop` host does **not** bundle `google-adk` — GEAP SDK is for deploy script / optional worker only; runtime queries use client API.

---

## Deploy (two services)

```bash
./scripts/package-host.sh && ./scripts/deploy-gcp.sh          # main loop + console
./scripts/package-adk-worker.sh && ./scripts/deploy-adk-worker.sh  # loop-adk (ADK + Antigravity)
# redeploy main to pick up LOOP_ADK_WORKER_URL automatically
./scripts/deploy-gcp.sh
```

Main `loop` forwards `POST /api/signals` through **GEAP Runtime** when `LOOP_GEAP_ENABLED=1` and `LOOP_GEAP_AGENT_ENGINE_ID` are set, else to `loop-adk` when `LOOP_ADK_WORKER_URL` is set. Code-fix jobs use `LOOP_CODE_BACKEND=auto`: Antigravity → Gemini → fixture fallback.

**Scale:** `loop` and `loop-adk` default **min-instances 0** in deploy scripts. Demo tenant Cove should also scale to zero when not demoing (separate repo/deploy).

---

## Demo script (60s)

1. Campus → Safari 3DS room → evidence → HIGH gate.
2. Approvals → Approve → job queued → vitest → Cove PR (multi-file).
3. Connect → tenant ingest → Pub/Sub publish (best-effort) + room opens.
4. Security exfil room → DENY artifact (no customer records tool).

---

## Env checklist (hosted)

```
LOOP_STATE_GCS_URI=gs://…/loop_state.db
LOOP_ADMIN_TOKEN=…
LOOP_GITHUB_TOKEN=…
GOOGLE_API_KEY=…          # AI Studio — not Gemini Pro Plus subscription
LOOP_CODE_REQUIRE_TESTS=1
LOOP_PUBSUB_TOPIC=loop.signals
LOOP_TASKS_QUEUE=loop-jobs
LOOP_PUBLIC_URL=https://loop-….run.app
```

Optional: `LOOP_TASKS_DISABLE=1` forces inline worker threads (used when Cloud Tasks API unavailable).
