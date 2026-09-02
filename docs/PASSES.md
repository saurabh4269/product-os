# Production passes — living log

Each pass is a focused PR against `main`. Only record what was verified in code or on hosted LOOP (`LOOP_EVAL=0`).

---

## Pass 0 — production E2E wiring (this PR)

**Branch:** `cursor/pass0-production-e2e-d138`  
**Hosted:** https://productos.heisenbug.in · Tenant Cove: https://cove-5uy6fkd7bq-uc.a.run.app · tenant `acme`

### Production walk facts (2026-09-02, verified on hosted)

| # | Fact |
|---|---|
| 1 | `POST /api/t/acme/signals` (tenant bearer) **200**, **joins** existing open room, does **not** run investigation pipeline; `auto_investigated` stays 0. Worker tick `detected:0`. `tasks_disabled=true`, `inline=true`. Main e2e break vs `test_ingest_runs_investigation_pipeline`. |
| 2 | `GET /ws` and `GET /ws/rooms/:id` return **HTTP 200 HTML** (SPA catch-all), not 101. Browser Live work shows Offline when upgrade path is confused. `wss://` upgrade works from Python client on current deploy — plain GET must not serve SPA HTML. |
| 3 | Firestore: API **403 SERVICE_DISABLED**; `GET /api/memory` **200** from SQLite. Status must not advertise `enabled:true` when mirror is skipped. |
| 4 | `POST /api/signals` **200 with no auth** and runs live fleet graph — must **401** when `LOOP_EVAL=0`. |
| 5 | Duplicate tenants `acme` and `cove` (same Cove repo/deploy) with diverged flags (`acme` `pay_sdk_4_3=on`, `cove` off). Execute must use **bound** `inv.tenant_id` only. |
| 6 | Live graph stalls at **three-source gate** (`tokens_consumed` 0). Warehouse/connectors not producing independent evidence in prod. |
| 7 | Invalid approval decision `"maybe"` was coerced to **deny** (422 expected). A pending HIGH was denied during the walk — **do not re-approve**. |
| 8 | `NEXT_PUBLIC_LOOP_ADMIN_TOKEN` must never be inlined in the console bundle. |

### Changes in this pass

1. **Tenant ingest** — only join when investigation is `AWAITING_APPROVAL`; close stale open rooms and run `run_investigation` for checkout hang (GATHERING/terminal/stuck).
2. **WebSocket on LOOP** — explicit `GET /ws` + `/ws/rooms/:id` return **405** (not SPA HTML); WS handlers stay on FastAPI; SPA catch-all skips `ws` paths.
3. **Incident panel** — `incident_lifecycle` WS events + polling fallback.
4. **Inline worker** — detect → auto-investigate → job drain + heartbeat.
5. **Memory** — `mirror.configured` vs `mirror.enabled` (operational only); Memory page banner on skip.
6. **`POST /api/signals`** — admin bearer required when `LOOP_EVAL=0`.
7. **Approvals** — `decision` must be `approve` \| `deny` (422 otherwise).
8. **Execute** — prefer `inv.tenant_id` for flag/PR when tenant-bound.
9. **Console** — admin token sessionStorage only (no `NEXT_PUBLIC_LOOP_ADMIN_TOKEN`).

### Still open in Pass 0 (deploy required)

- Deploy this PR to hosted before re-walking Cove checkout hang.
- Cloud Firestore API enablement (optional).
- Cove → LOOP ingest freshness (`last_ingest_at`) depends on Cove posting with valid tenant token.

### Tests run locally

- `python3 -m pytest -q` (226+ passed; `test_lifecycle_awaiting_approval` pre-existing fail on `main`)
- `apps/console` `tsc --noEmit` green

---

## Pass A1 — security & evidence (queued, not this PR)

**Goal:** Close production holes found in the walk without widening Pass 0.

### Verified issues to address

| Item | Detail |
|---|---|
| Three-source gate stall | Warehouse/BQ/connectors not producing ≥3 independent evidence groups in prod (`tokens_consumed` 0). |
| Duplicate tenants | Consolidate or hide `cove` vs `acme` on Connect; single canonical tenant for Cove wire. |
| `POST /api/signals` surface | Confirm no other unauthenticated pipeline entrypoints in eval-off mode. |
| Approval UX | Surface 422 clearly in console; never coerce invalid decisions to deny. |
| Scheduler tick | Verify Cloud Scheduler OIDC auth to `/api/internal/worker/tick` (inline worker is fallback). |
| Firestore | Enable API or set `LOOP_FIRESTORE_MEMORY=0` on deploy for honest config. |

### Changes

- _(stub)_

### Still open

- _(stub)_

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
