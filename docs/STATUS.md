# Product OS — Status

Last updated: 2026-09-05 (UTC)

## Active

Keep-going unpaused by owner. Do not merge Cove. Local ship via `./scripts/local-ship.sh`. Cloud agent does **not** deploy — owner deploys from laptop or Actions after green `ci`.

## Hosted (known 2026-09-05)

| Field | Value |
|---|---|
| User URL | https://productos.heisenbug.in |
| GCP | `mystical-timing-442601-q8` · `us-central1` · service `loop` |
| Revision | `loop-00141-j22` (100% traffic) |
| SHA on main | `3faa7ba` (#35 lean host) |
| Memory / scale | **2Gi** · concurrency **8** · `LOOP_INLINE_WORKER=0` · `LOOP_AUTO_INVESTIGATE=0` |
| `LOOP_EVAL` | `0` (`eval_mode: false`) |
| Health | `/` and `/rooms` 200 when instance healthy · `/shop` 404 · OAuth connected when live |

**2Gi lean host (PR #35, shipped):** Explicit `--memory 2Gi` + `--concurrency 8`, batch room summaries, capped office, 30s/60s debounce + `document.hidden` pause, slim `/api/status`. **E2E PASS** on this profile (see Demo E2E below). Stay on 2Gi — no 4Gi without owner sign-off.

**State:** `LOOP_STATE_GCS_URI=gs://mystical-timing-442601-q8-loop-host/loop_state.db`. Persist live sqlite before package when the demo room GET is 200. Do not overwrite a good snapshot from a 503/OOM instance. Multi-instance drift (intermittent room/action 404 under concurrency 8) — mitigated with retries + persist; see LEARNINGS.

**Demo tenant (Cove):** https://github.com/saurabh4269/cove · Cloud Run `cove`. Demo only — never merge Cove PRs from here.

## What works (PR #35 + E2E)

- Generic autonomous product loop: observe → rooms → parallel specialists → Customer Voice JSON → Type A/B → LOW/MED/HIGH → human HIGH → tenant flags + PR (never merge) → verify → four memories.
- Campus + multi-room chat UI. Mochi rail logo only. No Demo chrome (`LOOP_EVAL=0`).
- Unauth `/` and `/rooms` show Connect CTA — not ErrorState on 401 when no admin token.
- Mail-first outreach: contact lookup + cohort cluster + Gmail glass-box cards.
- Customer Voice: OTP hang metrics classify `otp_verify_timeout` on new ingest / telephony finalize.
- Duplicate HIGH hidden in room bundle, `/api/approvals`, and status counts when flags PR already shipped.
- Approve API returns **409** when a duplicate HIGH action would re-open a tenant PR (`act_4754e1ae24f5` pattern).
- Verify: dead `code_fix` jobs swept; immediate verify when flags PR opens (`LOOP_VERIFY_DELAY_HOURS=0` on deploy).
- GitHub card DONE when PR open — `code_fix` failure does not surface as failed GitHub receipt when flags PR exists.
- `./scripts/verify.sh` green locally.
- **Lean 2Gi E2E PASS (2026-09-05):** full demo path from metric ingest through HIGH approval to Cove flags PR.

## Demo E2E (PASS 2026-09-05)

| Field | Value |
|---|---|
| Metric | `otp_verify_hang_demo_1788625174` |
| Room | `room_65a4654bec` |
| Path | Type A HIGH |
| Voice | `otp_verify_timeout` |
| Action | `act_4d9bccc41f92` — approved |
| Cove PR | [#18](https://github.com/saurabh4269/cove/pull/18) — OPEN, never merge (`flags.json` only) |

**Fresh demo room:** ingest a **unique metric** (e.g. `otp_verify_hang_demo_<timestamp>`).

## Recording tip

Live revision `loop-00141-j22` · **2Gi** · concurrency **8**.

1. After Connect, deep-link **`/rooms/room_65a4654bec`** — the demo PASS room (Cove [#18](https://github.com/saurabh4269/cove/pull/18)).
2. Do **not** open stale `room_f627763ea9` or leftover HIGH `act_4754e1ae24f5`.
3. Prefer **in-room A2A** over Campus office — campus desks lag on older rooms.

## Older demo hang (stale GCS may still list)

| Field | Value |
|---|---|
| Room | `room_f627763ea9` |
| Investigation | `inv_450569ba5e7e` |
| Metric | `otp_verify_hang_0904` |
| Cove PR | [#17](https://github.com/saurabh4269/cove/pull/17) — OPEN, never merge |
| Blocked action | `act_4754e1ae24f5` — do not approve (duplicates #17) |

## Blockers resolved (2026-09-05)

| Issue | Resolution |
|---|---|
| `LOOP_GITHUB_TOKEN` invalid (390-char value → GitHub 401) | Replaced with working 40-char PAT. Do not print tokens. |
| `gcloud run deploy --env-vars-file` with one key | Wipes all other env vars. Use `--update-env-vars` instead. |

## Branches / PRs

### product-os

- `main` tip `3faa7ba` (#35 lean host — shipped).
- `GCP_SA_KEY` set; Actions `deploy-gcp` after green `ci`.

### Never merge

- **Cove:** PRs #1–#4, #7, #17, #18
- **LOOP:** #11–#16, #17 (Cove-related leftovers)

## Redeploy (when owner says go)

```bash
./scripts/local-ship.sh
# or:
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh   # --memory 2Gi --concurrency 8
```

Never `gcloud run deploy --source`. Never `gcloud run deploy --env-vars-file` with a single key — use `--update-env-vars`. See [`DEPLOY.md`](DEPLOY.md).

## Docs for the next agent

Read order: [`AGENTS.md`](../AGENTS.md) → [`LEARNINGS.md`](LEARNINGS.md) → [`PLAN_NEXT.md`](PLAN_NEXT.md) → [`TENANT.md`](TENANT.md) → [`PRD.md`](PRD.md) → [`DESIGN_INTENT.md`](DESIGN_INTENT.md). Full index: [`README.md`](README.md).
