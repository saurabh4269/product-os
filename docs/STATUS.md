# Product OS — Status

Last updated: 2026-09-03 (IST)

## Pause

**Owner paused deploy 2026-09-03 13:35 IST.** Do not deploy until they say go. Overnight keep-going routine is paused.

## Hosted

| Field | Value |
|---|---|
| User URL | https://productos.heisenbug.in |
| GCP | `mystical-timing-442601-q8` · `us-central1` · service `loop` |
| Revision | `loop-00122-drb` |
| SHA deployed | `10c9ad1` (PR #25 — 4Gi memory + lean boot) |
| Memory / scale | 4Gi · min 1 · max 2 |
| `LOOP_EVAL` | `0` |
| Health | `/` 200 · `/rooms` 200 · `/shop` 404 |

**Main tip (not deployed):** `54b4b97` — PR #26 (demo lesson scope) + PR #27 (room UI GitHub card truth) on `main`, not live yet.

**State:** `LOOP_STATE_GCS_URI=gs://mystical-timing-442601-q8-loop-host/loop_state.db`. Persist live sqlite before package when the hang room GET is 200. Do not overwrite a good snapshot from a 503/OOM instance.

**Demo tenant (Cove):** https://github.com/saurabh4269/cove · Cloud Run `cove`. Demo only — never merge Cove PRs from here.

## What works

- Generic autonomous product loop: observe → rooms → parallel specialists → Customer Voice JSON → Type A/B → LOW/MED/HIGH → human HIGH → tenant flags + PR (never merge) → verify → four memories.
- Campus + multi-room chat UI. Mochi rail logo only. No Demo chrome (`LOOP_EVAL=0`).
- Unauth `/rooms` stays on index with Connect CTA (PR #23). No ErrorState on 401.
- Campus stampede poll removed (PR #24). Was 4s office+rooms poll → OOM on 2Gi → GFE 429.
- Lean container boot (PR #25): apt no longer installs nodejs/npm/pip.
- GCS-backed SQLite persistence. Rooms survive restarts unless stale snapshot restored.
- Tenant wire: Connect, token-gated ingest, GitHub PR on HIGH approve. Cove PR #17 (`flags.json`) is the live ship path for the hang demo.
- `./scripts/verify.sh` green on `main`.

## Demo hang (live)

| Field | Value |
|---|---|
| Room | `room_f627763ea9` |
| Investigation | `inv_450569ba5e7e` |
| Metric | `otp_verify_hang_0904` |
| Path | Type A HIGH |
| Voice | `payment_timeout` |
| Cove PR | [#17](https://github.com/saurabh4269/cove/pull/17) — OPEN, `flags.json` only, never merge |
| Blocked action | `act_4754e1ae24f5` — do not approve (duplicates #17) |
| `code_fix` | Failed (no node in worker); `github_pr` is the ship path |
| UI gap | FAILED+DONE on hosted until #26+#27 deploy (merged on `main` as `54b4b97`) |

## Branches / PRs

### product-os (`main` has #9–#27, tip `54b4b97`)

**Open PRs:** none on product-os except this docs handoff ([#28](https://github.com/saurabh4269/product-os/pull/28)).

Recent merged: #23 (unauth rooms Connect CTA), #24 (remove 4s campus poll), #25 (4Gi + lean boot), #26 (demo lesson scope), #27 (room UI GitHub card truth, `54b4b97`).

### Never merge

- **Cove:** PRs #1–#4, #7
- **LOOP:** #11–#16, #17 (Cove-related leftovers)

## Blockers

1. **#26+#27 not deployed** — hosted UI still mislabels `code_fix` failure vs `github_pr` success until next deploy.
2. **Owner pause** — no deploy without explicit go.
3. **Remotion hang video** — off-repo only; `export-demo` cannot target hosted rooms.
4. **Workspace OAuth** — Web client still created manually in Google Auth Platform; flow wired on Connect.

## Redeploy (when owner says go)

```bash
# 1. Persist live sqlite if hang room is healthy (GET 200)
# 2. Package and deploy
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh
```

Never `gcloud run deploy --source`. See [`DEPLOY.md`](DEPLOY.md).

## Docs for the next agent

Read order: [`AGENTS.md`](../AGENTS.md) → [`LEARNINGS.md`](LEARNINGS.md) → [`PLAN_NEXT.md`](PLAN_NEXT.md) → [`TENANT.md`](TENANT.md) → [`PRD.md`](PRD.md) → [`DESIGN_INTENT.md`](DESIGN_INTENT.md). Full index: [`README.md`](README.md).
