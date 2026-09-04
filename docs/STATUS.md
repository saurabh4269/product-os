# Product OS — Status

Last updated: 2026-09-04 (IST)

## Active (2026-09-04 ~07:00 IST)

Keep-going unpaused by owner. Do not merge Cove. Local ship via `./scripts/local-ship.sh`.

## Hosted

| Field | Value |
|---|---|
| User URL | https://productos.heisenbug.in |
| GCP | `mystical-timing-442601-q8` · `us-central1` · service `loop` |
| Revision | `loop-00129-ghd` (100% traffic) |
| SHA deployed | `8588d32` on main (#32) via Actions `deploy-gcp` |
| Memory / scale | 4Gi · min 1 · max 2 |
| `LOOP_EVAL` | `0` (`eval_mode: false`) |
| Health | `/` 200 · `/rooms` 200 · `/shop` 404 · persist POST 200 · OAuth connected |
| Deploy finished | ~07:15 IST 2026-09-04 (Actions run 33826458867) |

**State:** `LOOP_STATE_GCS_URI=gs://mystical-timing-442601-q8-loop-host/loop_state.db`. Persist live sqlite before package when the hang room GET is 200. Do not overwrite a good snapshot from a 503/OOM instance. Post-deploy persist confirmed 200 after this ship (pre-deploy `/api/config` curl timed out once — hang GET was still 200).

**Demo tenant (Cove):** https://github.com/saurabh4269/cove · Cloud Run `cove`. Demo only — never merge Cove PRs from here.

## What works

- Generic autonomous product loop: observe → rooms → parallel specialists → Customer Voice JSON → Type A/B → LOW/MED/HIGH → human HIGH → tenant flags + PR (never merge) → verify → four memories.
- Campus + multi-room chat UI. Mochi rail logo only. No Demo chrome (`LOOP_EVAL=0`).
- Unauth `/rooms` stays on index with Connect CTA (PR #23). No ErrorState on 401.
- Campus stampede poll removed (PR #24). Was 4s office+rooms poll → OOM on 2Gi → GFE 429.
- Lean container boot: no apt-get curl/git/node on start. `urlretrieve(url, "/tmp/loop.tgz")` via gcloud `^|^` args (one-arg urlretrieve writes a random temp file — that killed `loop-00124-rc2`). `code_fix` extra skips; `github_pr` is the ship.
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
| State | Survived Actions deploy to `loop-00129-ghd`. ACTING · `pending_actions` empty · leftover `act_4754e1ae24f5` still in history (`awaiting_approval`) but not in pending UI. Do not approve. |

## Branches / PRs

### product-os (`main` tip `8588d32`)

Recent merged: #23–#32. Live on Actions-shipped revision (see Hosted table). `GCP_SA_KEY` is set; Actions `deploy-gcp` green.

### Never merge

- **Cove:** PRs #1–#4, #7
- **LOOP:** #11–#16, #17 (Cove-related leftovers)

## Blockers

1. **Overnight keep-going** — unpaused by owner 2026-09-03.
2. ~~**GitHub Actions deploy**~~ — `GCP_SA_KEY` set 2026-09-04 (SA `loop-cloud-agent`). Manual `workflow_dispatch` run succeeded: https://github.com/saurabh4269/product-os/actions/runs/33826458867. Auto-deploy on green `ci` → `main` should work now.

## Redeploy (when owner says go)

```bash
./scripts/local-ship.sh
# or:
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh
```

Never `gcloud run deploy --source`. See [`DEPLOY.md`](DEPLOY.md).

## Docs for the next agent

Read order: [`AGENTS.md`](../AGENTS.md) → [`LEARNINGS.md`](LEARNINGS.md) → [`PLAN_NEXT.md`](PLAN_NEXT.md) → [`TENANT.md`](TENANT.md) → [`PRD.md`](PRD.md) → [`DESIGN_INTENT.md`](DESIGN_INTENT.md). Full index: [`README.md`](README.md).
