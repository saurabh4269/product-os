# Product OS — Status

Last updated: 2026-09-03 (IST)

## Active (2026-09-03 ~23:50 IST)

Keep-going unpaused by owner. Do not merge Cove.

## Hosted

| Field | Value |
|---|---|
| User URL | https://productos.heisenbug.in |
| GCP | `mystical-timing-442601-q8` · `us-central1` · service `loop` |
| Revision | `loop-00127-7dc` (100% traffic) |
| SHA deployed | `996470e` (#31) + #32 console fixes deployed from branch |
| Memory / scale | 4Gi · min 1 · max 2 |
| `LOOP_EVAL` | `0` |
| Health | `/` 200 · `/rooms` 200 · `/shop` 404 · persist POST 200 · OAuth connected |
| Deploy finished | ~23:50 IST 2026-09-03 |

**State:** `LOOP_STATE_GCS_URI=gs://mystical-timing-442601-q8-loop-host/loop_state.db`. Persist live sqlite before package when the hang room GET is 200. Do not overwrite a good snapshot from a 503/OOM instance.

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
| State | Survived deploy to `loop-00127-7dc`. Browser verified: GitHub PR DONE; leftover HIGH gate hidden after pending_actions fix. |

## Branches / PRs

### product-os (`main` tip `996470e`)

Recent merged: #23–#31. Live on `loop-00127-7dc`. Open: [#32](https://github.com/saurabh4269/product-os/pull/32) (unauth room + pending_actions UI). GitHub Actions `deploy-gcp` needs `GCP_SA_KEY`.

### Never merge

- **Cove:** PRs #1–#4, #7
- **LOOP:** #11–#16, #17 (Cove-related leftovers)

## Blockers

1. **Overnight keep-going** — unpaused by owner 2026-09-03.
2. **GitHub Actions deploy** — add repo secret `GCP_SA_KEY` or keep shipping via `package-host.sh` + `deploy-gcp.sh`.

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
