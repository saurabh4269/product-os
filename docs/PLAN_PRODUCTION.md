# PLAN PRODUCTION — PRD vision → shippable phases

| Field | Value |
|---|---|
| Status | Active — production hardening track |
| Spec | [`PRD.md`](PRD.md) v1.1 (binding MUST) |
| Demo track | [`PLAN_NEXT.md`](PLAN_NEXT.md) Phases A–F (shipped) |
| Region | `us-central1` |

This document maps **PRD §24 build sequence** to what exists, what we are building now, and what stays plan-only until GEAP entitlements exist.

---

## Honest now vs PRD vision

| PRD phase | Vision | Today | This track |
|---|---|---|---|
| **0 Foundation** | BQ, GA4, warehouse | Synthetic warehouse + cheap TF applied | BQ read path when dataset configured |
| **1 Governance** | Agent Gateway + SGP + Model Armor enforce | Local `gateway.py` + registry; Model Armor TF `failOpen=false` | Admin auth, audit log, plugin screening stays |
| **2 Signal + analysis** | TB-2 ambient Pub/Sub | Deterministic detect + tenant ingest | Pub/Sub publish on ingest (best-effort) |
| **3 Investigation core** | Resumable, survives restart | Engine + SQLite; **hosted SQLite ephemeral** | **GCS full-state backup + jobs table** |
| **4 Memory** | Cloud Memory Bank | SQLite `memory` + playbooks | Memory adapter interface; cloud when entitled |
| **5 Risk + HITL** | Durable approval queue | Works per-instance; lost on cold start | **Persisted with state backup** |
| **6 Code path** | Sandbox + tests + PR gate | One-shot JSON / Safari hardcode | **Job queue + test-before-PR + git apply** |
| **7 Voice** | Live API + media bridge | Twilio trial + simulated fallback | Keep honest skip; Live when entitled |
| **8 Product + coordination** | Workspace MCP | OAuth wired; send denied | Calendar/Gmail draft when OAuth connected |
| **9 Experiment + learning** | Verify loop closes | Synthetic warehouse verify | Tenant metric hook (Cove flags + ingest) |
| **10 Evaluation** | CI eval gates | `verify.sh` + fixture tests | Job failure = no PR; adversarial suite grows |
| **11 Console** | Full trust UI | Campus + rooms + approvals (strong) | Job status on approvals + Connect |
| **12 Hardening** | Load + failure drills | min-instances=1 | Cloud SQL optional; worker tick endpoint |

**Plan-only (do not fake):** GEAP Agent Runtime, cloud Agent Gateway enforcement, SGP, Antigravity as sole path, outbound Google PSTN.

---

## P0 — shipped (this track)

1. **Durable control plane** — `state_persist.py`: hydrate/persist full SQLite to `LOOP_STATE_GCS_URI`; debounced upload after writes.
2. **Durable jobs** — `jobs` table: `queued → running → succeeded|failed|dead`; code-fix runs as a job via Cloud Tasks + inline fallback.
3. **Admin auth** — `LOOP_ADMIN_TOKEN` protects tenant admin, OAuth client, jobs, audit, worker tick/run. Approvals stay console-accessible until P1 (Google OAuth approver SSO).
4. **Code agent v2** — clone → generate → **apply in repo** → **run tests** → PR only if green; deterministic Safari path only when `brief.fixture_id=safari_3ds`.
5. **Audit log** — append-only `audit` table + `GET /api/audit` (admin).
6. **Model Armor layered screening** — `model_armor.py` on tool output (API + deterministic needles).
7. **Pub/Sub on ingest** — `publish_signal()` when tenant metrics land.
8. **Console job polling** — `/api/approvals/{id}/status` + Approvals UI.

Exit criteria: approve HIGH → job queued → survives deploy → PR opens only after vitest passes (or job records failure). **Met in code; verify on hosted after deploy.**

---

## P1 — customer pilot

6. PostgreSQL optional via `LOOP_DATABASE_URL` (Cloud SQL) — same Store schema.
7. Cloud Scheduler → `POST /api/internal/worker/tick` with admin token (replaces in-process poll for multi-instance).
8. GitHub App credentials (optional) alongside PAT.
9. Verify loop reads tenant signals post-flag-flip.
10. Model Armor on Gemini code-fix calls when entitled.

---

## P2 — PRD platform alignment (when entitled)

11. Managed ADK runtime deployment (TB-1…TB-7 split).
12. Agent Gateway + `failOpen=false` (gated TF already plan-only).
13. Cloud Memory Bank adapter replacing SQLite memory for production tenants.
14. Antigravity or ADK code sandbox as **editor inside job worker** (multi-turn), not one-shot JSON.

---

## Code map (production track)

```
services/loop/loop/
  state_persist.py   Full DB ↔ GCS
  jobs.py            Enqueue, claim, complete, Cloud Tasks dispatch
  tasks.py           Cloud Tasks HTTP enqueue; inline thread fallback
  model_armor.py     Layered Model Armor + deterministic screening
  connectors/warehouse.py  Pub/Sub publish on signals
  auth.py            Admin bearer + audit helper
  audit.py           Audit event writers
  code_worker.py     Apply patches, run tests, collect files
  code_fix.py        Enqueue job; worker entrypoint
  store.py           jobs + audit tables
  api.py             Admin deps, /api/jobs, /api/internal/worker/tick|run, approval status
docs/PLAN_PRODUCTION.md  This file
docs/ENTERPRISE_TRACK.md Judge-facing ADK 2 / GEAP honest map
```

---

## Environment variables

| Variable | Purpose |
|---|---|
| `LOOP_STATE_GCS_URI` | `gs://…/loop_state.db` full SQLite backup |
| `LOOP_ADMIN_TOKEN` | Bearer for admin + worker endpoints |
| `LOOP_DATABASE_URL` | Optional Postgres (P1) |
| `LOOP_CODE_TEST_CMD` | Override test command (default: auto-detect vitest/npm test) |
| `LOOP_CODE_REQUIRE_TESTS` | `1` = fail job if tests fail (default on hosted) |
| `LOOP_PUBSUB_TOPIC` | Pub/Sub topic for tenant ingest signals (default `loop.signals`) |
| `LOOP_TASKS_QUEUE` | Cloud Tasks queue name (default `loop-jobs`) |
| `LOOP_TASKS_DISABLE` | `1` = inline worker threads only |
| `LOOP_MODEL_ARMOR_DISABLE` | `1` = skip Model Armor API (deterministic needles still run) |

Existing: `LOOP_FLAGS_GCS_URI`, `LOOP_OAUTH_GCS_URI`, `LOOP_GITHUB_TOKEN`, `GOOGLE_API_KEY`, `LOOP_CODE_BACKEND`.
