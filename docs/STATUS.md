# Product OS — Status

Last updated: 2026-09-03 (IST)

## Pause

**Owner asked to deploy latest (done ~13:55 IST 2026-09-03).** Overnight keep-going routine is still paused.

## Hosted

| Field | Value |
|---|---|
| User URL | https://productos.heisenbug.in |
| GCP | `mystical-timing-442601-q8` · `us-central1` · service `loop` |
| Revision | `loop-00123-7rx` (100% traffic) |
| SHA deployed | `fc1611948b3fcec0e68dd6dbe62d9cf7cd8f86b5` (PRs #26, #27, #28) |
| Memory / scale | 4Gi · min 1 · max 2 |
| `LOOP_EVAL` | `0` |
| Health | `/` 200 · `/rooms` 200 · `/shop` 404 |
| Deploy finished | ~13:55 IST 2026-09-03 |

**State:** `LOOP_STATE_GCS_URI=gs://mystical-timing-442601-q8-loop-host/loop_state.db`. Persist live sqlite before package when the hang room GET is 200. Do not overwrite a good snapshot from a 503/OOM instance.

**Demo tenant (Cove):** https://github.com/saurabh4269/cove · Cloud Run `cove`. Demo only — never merge Cove PRs from here.

## What works

- Generic autonomous product loop: observe → rooms → parallel specialists → Customer Voice JSON → Type A/B → LOW/MED/HIGH → human HIGH → tenant flags + PR (never merge) → verify → four memories.
- Campus + multi-room chat UI. Mochi rail logo only. No Demo chrome (`LOOP_EVAL=0`).
- Unauth `/rooms` stays on index with Connect CTA (PR #23). No ErrorState on 401.
- Campus stampede poll removed (PR #24). Was 4s office+rooms poll → OOM on 2Gi → GFE 429.
- Lean container boot: no apt-get curl/git/node on start (Python `urlretrieve` fetches the tarball). `code_fix` extra skips; `github_pr` is the ship.
- GCS-backed SQLite persistence. Ingest and HIGH approve flush sqlite immediately. `deploy-gcp.sh` POSTs `/api/internal/state/persist` when live `/api/config` is 200.
- Tenant wire: Connect, token-gated ingest, GitHub PR on HIGH approve. Cove PR #17 (`flags.json`) is the live ship path for the hang demo. Same-metric ingest joins an open AWAITING_APPROVAL room (including after leftover HIGH is hidden).
- `export-demo --room` targets hosted GET `/api/rooms/{id}` with admin bearer. Refuses to overwrite the generic Remotion fixture.
- `./scripts/verify.sh` green on `main`.

## Demo hang (live)

| Field | Value |
|---|---|
| Room | `room_f627763ea9` |
| Investigation | `inv_450569ba5e7e` |
| Metric | `otp_verify_hang_0904` |
| Path | Type A HIGH |
| Voice | Live still `payment_timeout`; new OTP diagnostics classify `otp_verify_timeout` |
| Cove PR | [#17](https://github.com/saurabh4269/cove/pull/17) — OPEN, `flags.json` only, never merge |
| Blocked action | `act_4754e1ae24f5` — do not approve (duplicates #17) |
| `code_fix` | Lean worker skips (no git/node); `github_pr` is the ship path |
| State | Survived deploy (`room_f627763ea9` still live) |

## Branches / PRs

### product-os (`main` tip `fc16119`, deployed)

Recent merged: #23–#28 (through docs handoff). Live on `loop-00123-7rx` at `fc16119`.

### Never merge

- **Cove:** PRs #1–#4, #7
- **LOOP:** #11–#16, #17 (Cove-related leftovers)

## Blockers

1. **Overnight keep-going paused** — autonomous overnight routine still off.
2. **Workspace OAuth** — Web client still created manually in Google Auth Platform; flow wired on Connect.
3. **Hosted revision** — this branch is not live until persist + `package-host.sh` + `deploy-gcp.sh`. Do not redeploy for docs-only.

## Redeploy (when owner says go)

```bash
# persist runs inside deploy-gcp.sh when live /api/config is 200
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh
```

Never `gcloud run deploy --source`. See [`DEPLOY.md`](DEPLOY.md).

## Docs for the next agent

Read order: [`AGENTS.md`](../AGENTS.md) → [`LEARNINGS.md`](LEARNINGS.md) → [`PLAN_NEXT.md`](PLAN_NEXT.md) → [`TENANT.md`](TENANT.md) → [`PRD.md`](PRD.md) → [`DESIGN_INTENT.md`](DESIGN_INTENT.md). Full index: [`README.md`](README.md).
