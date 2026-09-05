# Product OS — Status

Last updated: 2026-09-05 (UTC)

## Active

Keep-going unpaused by owner. Do not merge Cove. Local ship via `./scripts/local-ship.sh`. Cloud agent does **not** deploy — owner deploys from laptop or Actions after green `ci`.

## Hosted (known 2026-09-05)

| Field | Value |
|---|---|
| User URL | https://productos.heisenbug.in |
| GCP | `mystical-timing-442601-q8` · `us-central1` · service `loop` |
| Revision | `loop-00134-8dw` (reported) |
| SHA on main (pre-ship) | `1add371` (#33 product film) · demo PR #35 in flight |
| Memory / scale | **2Gi** (hackathon pricing) · min 1 · max 2 |
| `LOOP_EVAL` | `0` (`eval_mode: false`) |
| Health | `/` and `/rooms` 200 when instance healthy · `/shop` 404 · OAuth connected when live |

**2Gi note:** GFE 429 on campus usually means OOM from request stampede, not an in-app rate limiter. This branch reduces load: no office+rooms hammer on every WS tick, slim room GET (`?slim=1`), SQL preview for `/api/rooms` list, 30s/60s debounced refetch.

**State:** `LOOP_STATE_GCS_URI=gs://mystical-timing-442601-q8-loop-host/loop_state.db`. Persist live sqlite before package when the hang room GET is 200. Do not overwrite a good snapshot from a 503/OOM instance.

**Demo tenant (Cove):** https://github.com/saurabh4269/cove · Cloud Run `cove`. Demo only — never merge Cove PRs from here.

## What works (PR #35)

- Generic autonomous product loop: observe → rooms → parallel specialists → Customer Voice JSON → Type A/B → LOW/MED/HIGH → human HIGH → tenant flags + PR (never merge) → verify → four memories.
- Campus + multi-room chat UI. Mochi rail logo only. No Demo chrome (`LOOP_EVAL=0`).
- Unauth `/` and `/rooms` show Connect CTA — not ErrorState on 401 when no admin token.
- Mail-first outreach: contact lookup + cohort cluster + Gmail glass-box cards.
- Customer Voice: OTP hang metrics classify `otp_verify_timeout` on new ingest / telephony finalize.
- Duplicate HIGH hidden in room bundle, `/api/approvals`, and status counts when flags PR already shipped.
- GitHub card DONE when PR open — `code_fix` failure does not surface as failed GitHub receipt when flags PR exists.
- `./scripts/verify.sh` green locally.

## Demo hang (live sqlite — may be stale)

| Field | Value |
|---|---|
| Room | `room_f627763ea9` |
| Investigation | `inv_450569ba5e7e` |
| Metric | `otp_verify_hang_0904` |
| Path | Type A HIGH |
| Voice | Stale GCS row may still show `payment_timeout` — new ingest uses `otp_verify_timeout` |
| Cove PR | [#17](https://github.com/saurabh4269/cove/pull/17) — OPEN, never merge |
| Blocked action | `act_4754e1ae24f5` — do not approve (duplicates #17) |
| Verify | Often inconclusive until tenant metric recovers — UI says so honestly |

**Fresh demo room:** ingest a **unique metric** (e.g. `otp_verify_hang_0905`).

## Branches / PRs

### product-os

- `main` tip `1add371`. **PR #35** — demo path on 2Gi (load reduction + workflow fixes).
- `GCP_SA_KEY` set; Actions `deploy-gcp` after green `ci`.

### Never merge

- **Cove:** PRs #1–#4, #7, #17
- **LOOP:** #11–#16, #17 (Cove-related leftovers)

## Redeploy (when owner says go)

```bash
./scripts/local-ship.sh
# or:
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh   # --memory 2Gi
```

Never `gcloud run deploy --source`. See [`DEPLOY.md`](DEPLOY.md).

## Docs for the next agent

Read order: [`AGENTS.md`](../AGENTS.md) → [`LEARNINGS.md`](LEARNINGS.md) → [`PLAN_NEXT.md`](PLAN_NEXT.md) → [`TENANT.md`](TENANT.md) → [`PRD.md`](PRD.md) → [`DESIGN_INTENT.md`](DESIGN_INTENT.md). Full index: [`README.md`](README.md).
