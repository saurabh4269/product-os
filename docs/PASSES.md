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

## Pass 1 — production-grade control plane auth (this PR)

**Branch:** `cursor/pass1-control-plane-auth-7ec2`  
**Goal:** Close hosted auth holes verified before #9 deploy; keep tenant `/api/t/*` on tenant bearer.

### Verified (still true on `main` after #9)

| # | Issue |
|---|---|
| 1 | Unauthenticated GET of rooms, approvals, pipeline, traces, registry, office, signals, memory, oauth status leaked control-plane data |
| 2 | Mutations (tenants, memory, agent_callback, investigate, improve, research, coordinate, room messages) accepted unauth bodies |
| 3 | CORS `Access-Control-Allow-Origin: *` with `Authorization` on Cloud Run |
| 4 | Duplicate tenants `acme` + `cove` (same `saurabh4269/cove` repo) confused Connect |

### Changes

1. **`AdminUnlessEval` dependency** — `require_admin_unless_eval()` on all listed GET routes and mutation routes; runs before body validation via FastAPI `Depends`.
2. **Protected reads** — `GET /api/rooms`, `/api/rooms/:id`, `/api/approvals`, `/api/pipeline`, `/api/traces`, `/api/registry`, `/api/office`, `/api/signals`, `/api/memory`, `/api/oauth/google` return **401** when `LOOP_EVAL=0` without admin bearer.
3. **Protected writes** — `POST /api/tenants`, `/api/memory`, `/api/agent_callback`, `/api/investigate`, `/api/improve`, `/api/research`, `/api/coordinate`, `/api/rooms/:id/messages` return **401** before creating data.
4. **CORS allowlist** — `cors_allowlist()` never emits `*` on Cloud Run; uses `LOOP_PUBLIC_URL` / `LOOP_CONSOLE_ORIGIN` (`https://productos.heisenbug.in`) with `allow_credentials=True`. Deploy scripts updated (`deploy-gcp.sh`, `cloudrun-entry.sh`).
5. **Console** — `lib/api.ts` sends stored admin bearer on all fetches when present (sessionStorage/localStorage).
6. **Duplicate tenants** — `GET /api/tenants` hides non-canonical rows that share the same repo (keeps `LOOP_TENANT_ID` / `acme`); data not deleted.
7. **WebSocket** — Pass 0 already owns `/ws` HTTP probes (405); no change needed.

### Still open

- Deploy this PR to hosted before re-walking Cove checkout hang.
- OAuth `/start` and `/callback` stay browser redirects (Google); status endpoint is admin-gated.
- Full duplicate-tenant consolidation (merge SQLite rows) is out of scope — execution already prefers bound `inv.tenant_id`.

### Tests run locally

- `python -m pytest -q` — 256 passed
- `apps/console` `tsc --noEmit` + `verify-deploy.sh` green

---

## Pass — homepage glass office + design intent (this PR)

**Branch:** `cursor/homepage-glass-office-a9aa`  
**Spec:** [`docs/DESIGN_INTENT.md`](DESIGN_INTENT.md) committed as binding UI/architecture intent.

### What was wrong

Home stacked CityMap + ops dashboard (collapsed pipeline, activity log, demo strip). No visible A2A graph, no in-page tool embeds, `evalMode` defaulted `true` before config load. Rooms did not surface Type A/B, risk gate, or structured Customer Voice in chat.

### Changes

1. **`docs/DESIGN_INTENT.md`** — Grok/OpenClaw register, named specialists, Customer Voice JSON, four memories, gateway identity, honest skip.
2. **Home IA** — `HandoffGraph`, `HomeGlassBox`, `LiveRoomsRail`, `SevenStepLoop`; demo chrome removed; `evalMode` defaults `false`.
3. **Room glass box** — `RoomCaseBanner`, evidence graph, proof grid, `StructuredEvidenceCard` in chat.
4. **Tests** — `tests/test_design_intent.py` (8 tests, generic pipeline — not checkout-only).

### Verified locally

- `python3 -m pytest -q` — 264 passed
- `apps/console` `tsc --noEmit` + `npm run build` green

---

## Pass 1 — stub

**Goal:** _(superseded by section above)_

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
