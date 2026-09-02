# Production passes — living log

Each pass is a focused PR against `main`. Only record what was verified in code or on hosted LOOP (`LOOP_EVAL=0`).

---

## Pass 0 — production E2E wiring (this PR)

**Branch:** `cursor/pass0-production-e2e-d138`  
**Hosted:** https://productos.heisenbug.in · Tenant Cove: https://cove-5uy6fkd7bq-uc.a.run.app · tenant `acme`

### Verified before changes

| Check | Result |
|---|---|
| `GET /api/status` on hosted | `inline=true`, `tasks_disabled=true`, `last_signal_tick` recent, `auto_investigated=0`, `last_tick_detected=0` |
| WebSocket `wss://productos.heisenbug.in/ws` (Python client) | Connects; receives `initial_state` |
| `GET /ws` without upgrade | SPA returned HTML (confusing for probes; WS upgrade path works) |
| Firestore mirror | `LOOP_FIRESTORE_MEMORY=1` but `403 SERVICE_DISABLED` on Firestore API — not operational |
| `GET /api/tenants/acme/incident-lifecycle` | Present on tip; requires admin or tenant bearer |
| Tenant ingest path | `ingest_tenant_signal` runs `run_investigation` async when room is new; joined existing open room even when prior investigation was terminal |

### Changes in this pass

1. **Incident panel WS + polling fallback** — `publish_incident_lifecycle` on ingest, approve, arm; console handles `incident_lifecycle` WS events; slower poll when WS live.
2. **Inline ambient worker** — `LOOP_INLINE_WORKER=1` loop runs detect → auto-investigate (open signals) → job drain and records heartbeat (not only Cloud Scheduler tick).
3. **Tenant re-repro** — ingest skips join when open room’s investigation is terminal; opens a fresh pipeline.
4. **Live work status** — show Connecting/Reconnecting instead of labeling initial WS as Offline; transient WS errors reconnect.
5. **SPA** — do not serve `index.html` for `/ws` GET probes.
6. **Memory honest skip** — `/api/memory` includes `mirror` + `source`; Memory page banner when Firestore configured but not operational.

### Still open (not fixed in Pass 0)

- Enable Cloud Firestore API on GCP (optional; SQLite remains source of truth).
- Cloud Scheduler OIDC tick auth — inline worker covers detect/investigate when scheduler misses.
- Cove → LOOP ingest freshness (`last_ingest_at`) depends on Cove posting with valid tenant token.
- Deploy this PR to hosted (PR does not deploy).

### Tests run locally

- `cd services/loop && python -m pytest -q`
- `cd apps/console && ./node_modules/.bin/tsc --noEmit`
- `./scripts/verify-deploy.sh` (CI gate)

---

## Pass 1 — stub

**Goal:** _(fill on next walk)_

### Verified

- 

### Changes

- 

### Still open

- 

---

## Pass 2 — stub

**Goal:** _(fill on next walk)_

### Verified

- 

### Changes

- 

### Still open

- 
