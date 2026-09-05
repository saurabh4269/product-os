# AGENTS.md — handoff for the next agent

You are continuing **Product OS (LOOP)**. Start from **`main`**.

**Read-first order:** [`AGENTS.md`](AGENTS.md) → [`docs/LEARNINGS.md`](docs/LEARNINGS.md) → [`docs/PLAN_NEXT.md`](docs/PLAN_NEXT.md) → [`docs/TENANT.md`](docs/TENANT.md) → [`docs/PRD.md`](docs/PRD.md) → [`docs/DESIGN_INTENT.md`](docs/DESIGN_INTENT.md). Then [`docs/STATUS.md`](docs/STATUS.md) for branch/PR/blocker snapshot.

Repo: `github.com/saurabh4269/product-os`  
**User-facing URL:** https://productos.heisenbug.in — never use `*.run.app` as the product URL in user-facing copy.  
GCP: `mystical-timing-442601-q8` · `us-central1` · Cloud Run service `loop`  
Demo tenant (Cove only): `github.com/saurabh4269/cove` · Cloud Run `cove` · https://cove-5uy6fkd7bq-uc.a.run.app

**Owner unpaused keep-going.** #30–#32 on main; live revision `loop-00129-ghd` (Actions ship 2026-09-04). `GCP_SA_KEY` is set — green `ci` on `main` auto-deploys.

## What this product is

A **generic autonomous product team**: observe → rooms → parallel specialists → Customer Voice diagnostic JSON → Type A/B → risk LOW/MED/HIGH → human HIGH → tenant flags + PR (never merge) → verify → four memories.

Judging bar: 40% operational utility / 30% architecture / 30% demo readiness.

It is **not** a Safari / 3DS / checkout app. Those scenarios are **fixtures** through one pipeline.

- **Type A** — something broke → fix (BUG path).
- **Type B** — something could be better → improve (FEATURE path).
- After root cause: BUG vs FEATURE. Do not special-case one demo in architecture or UI.

The UI is a **campus + multi-room chat** (Grok / OpenClaw energy): pixel agents, visible handoffs, per-bot chats. It is not a CRUD dashboard and not a dark “war room.”

## Live / hosted (2026-09-04 ~07:00 IST)

| Field | Value |
|---|---|
| User URL | https://productos.heisenbug.in |
| Revision | `loop-00129-ghd` (100% traffic) |
| SHA deployed | `8588d32` on main (#32) via Actions |
| Memory | **2Gi** · concurrency **8** · min 1 · max 2 |
| `LOOP_EVAL` | `0` (no Demo chrome) |
| Health | `/` and `/rooms` 200 · `/shop` 404 · persist POST 200 · Workspace OAuth connected |

**State:** SQLite persists via `LOOP_STATE_GCS_URI` (`gs://mystical-timing-442601-q8-loop-host/loop_state.db`). Rooms survive restarts unless a deploy hydrates an **old** GCS snapshot. **Persist live sqlite before `package-host.sh`** when the hang room GET is 200. If live is 503/OOM, do **not** overwrite a good snapshot.

**Demo hang (live):** `room_f627763ea9` (survived deploy) · `inv_450569ba5e7e` · metric `otp_verify_hang_0904` · Type A HIGH · Voice `payment_timeout`. Cove PR [#17](https://github.com/saurabh4269/cove/pull/17) (`flags.json` only) — OPEN, never merge. Do **not** approve leftover `act_4754e1ae24f5` (would duplicate #17). `code_fix` extra failed (no node in worker); `github_pr` is the ship path.

## References the user pointed at

Open these before you change campus, mascots, or the rail. Do not copy licensed art.

| What they said | What it means here | Look it up |
|---|---|---|
| **Bubu** (cream bear) | User name for the cream bear. In code she is **Mochi** — **rail logo only**, not a campus sticker. | `apps/console/public/city/mochi.png` · `BeanMark` in `shell.tsx` |
| **Bean / the duo on campus** | User asked them **off the homepage** — too prominent, off-vibe. Files can stay; do not re-mount `CampusSticker` on the map. | `bean-sit.png` is unused on campus now |
| **Bubu & Dudu / 黄油小熊** | Visual *register* only. Official pair is 黄小B’s **一二 (Yier)** cream panda + **布布 (Bubu)** brown bear. Fan name “Dudu” is unofficial. **Do not paste or trace their art.** Ours are original Mochi + Bean. | [Weibo 黄小B](https://weibo.com/u/2623471650) · [Yier & Bubu names](https://en.akkogear.com/bubu-dudu-or-yier-bubu-meet-the-real-creator-behind-the-internets-favorite-panda-and-bear/) · [FAQ](https://getbubududu.com/faq-all-about-bubu-and-dudu/) |
| **Pip** | Old otter mascot. **Do not restore.** `PipMark` / `PipSticker` are deprecated aliases. | `apps/console/components/mascot.tsx` |
| **Grok** | Multi-room chat, presence, not a dashboard. | [grok.com](https://grok.com) |
| **OpenClaw** | Same energy: rooms, agents, handoffs, a control surface that feels like chat. | [Control UI](https://docs.openclaw.ai/web/control-ui) · [repo](https://github.com/openclaw/openclaw) |
| **Claude City** | 2:1 isometric office floor, desks you can tap. No Phaser / Three / `react-isometric-grid`. | `components/iso-office.tsx` |
| **Apple / Stripe / “cloud”** | Light, welcoming. User **rejected** the dark ink + coral + Instrument Serif war-room. | Apple-like: bg `#f5f5f7`, campus `#eef2ee`, ink `#1d1d1f`, accent `#0071e3`, Inter. |
| **Linear / Notion rail** | 64px icon rail always on; expand grows the **same** aside. No second flyout, no hamburger-only. | `components/shell.tsx` |
| **Memory watch / Approvals tram** | Campus landmarks, % of the **contained image box**. | Watch `28, 72` · tram `50, 80` in `lib/campus.ts` |
| **Safari / 3DS** | One **fixture**, not the product. Do not bias UI or architecture around it. | `safari_3ds` in the fixture table |

**Mascot:** Mochi is the 32px rail mark (waves on home-link hover). PNG only — iPad Safari drops WebP alpha. No sitting pair on campus. Do not restore Pip.

## GitHub / PRs

**product-os:** `main` tip `8588d32` (#9–#32). `GCP_SA_KEY` set on the repo; Actions `deploy-gcp` works (`workflow_dispatch` green 2026-09-04). Laptop path: `./scripts/local-ship.sh`.

**Never merge:** Cove PRs #1–#4, #7; LOOP #11–#16, #17. Do not merge Cove.

## Binding rules

| Rule | Detail |
|---|---|
| Safety | `fail_open = false`. Tool-output armor on. Exfil of production customer records is **DENY** via Gateway **identity**, not a prompt. |
| Models | IDs only in [`config/models.yaml`](config/models.yaml). Default `gemini-3.5-flash`. Never set sampling on 3.6 / 3.5-lite. |
| Cost | Cheap GCP only (BQ, Pub/Sub, Cloud Run, Model Armor). Agent Gateway / SGP / telephony stay **plan-only**. |
| Hosted SQLite | Persists via `LOOP_STATE_GCS_URI` when configured. Rooms survive restarts. A deploy that hydrates an **old** GCS snapshot wipes rooms created after that snapshot — persist live DB before package when healthy. Do not hard-code hosted room IDs in commits. |
| Theme | Light Apple-like: `#f5f5f7` / campus `#eef2ee`, ink `#1d1d1f`, accent `#0071e3`, Inter. No Instrument Serif, no dark class, no status-color dots. **Mochi** (cream / “Bubu”) is the rail logo only. Do **not** put the sitting duo on the campus. |
| Art | Campus is `apps/console/public/city/campus.webp` (~75KB) + `campus.jpg`. **Do not re-add the 2MB PNG.** |
| Tenant product | Product OS is the control plane. **Do not host a customer shop, ads page, or demo storefront on this origin** (`/shop`, `/company`, `public/shop`). Cove is the demo tenant in its own repo/deploy. |
| Git | Commits look human. No AI `Co-authored-by` / author overrides. |
| Deploy | Only `package-host.sh` + `deploy-gcp.sh` with `NEXT_PUBLIC_API_URL` unset. Never `gcloud run deploy --source`. |
| Eval | Hosted `LOOP_EVAL=0`. No Demo chrome on production. |

## Repo map

```
apps/console/          Next 15 console (rooms, campus, office, agents)
apps/northstar-shop/   Fixture patch targets only. Not a storefront. Not hosted here.
apps/demo/             Remotion LoopDemo 1280×720 12s (local only; Cloud Run does not serve it)
services/loop/         Python control plane (engine, store, API, office, world, registry)
config/models.yaml     Only place model IDs live
data/                  Warehouse generator
playbooks/             SKILL-shaped lessons
infra/terraform/cheap  Applied. gated/ is plan-only
scripts/               boot, verify, package-host, deploy-gcp
docs/                  See docs/README.md for index
```

### Console (what you will edit)

| File | Role |
|---|---|
| `components/shell.tsx` | One rail that grows in place on every width (no second flyout). `localStorage` key `loop-sidebar`. `[` toggles. |
| `components/mascot.tsx` | Mochi (cream) is the rail mark. Pair is two PNG sprites (not WebP — iPad Safari drops alpha). They watch / hop / wave. |
| `components/city-map.tsx` | Painted campus. Pins **and building ellipses** are % of the contained image box. No 4s office+rooms poll (OOM risk — see LEARNINGS). |
| `components/iso-office.tsx` | 2:1 isometric floor (Claude City energy, no Phaser). |
| `components/work-flipbook.tsx` | Click-the-work pages. Do not wrap room cards in a naked `<Link>`. |
| `lib/furniture.ts` | Deterministic pixel furniture. |
| `components/pixel-office.tsx` | Pixel people. Do not put sprites in a short `overflow-hidden` + `overflow-x-auto` box. |
| `components/office-floor.tsx` | Desk grid + handoffs. 2 columns on a phone. |
| `lib/api.ts` | `NEXT_PUBLIC_API_URL` or `""` in production (same origin). |
| `app/connect/page.tsx` | Tenant wire. Not a shop. Unauth `/rooms` shows Connect CTA, not ErrorState. |
| `app/agents/[id]/layout.tsx` | `generateStaticParams` `{ id: "_" }` — required for static export. Same for rooms/investigations. |

### Control plane

| File | Role |
|---|---|
| `loop/engine.py` | Deterministic loop. Hosted path does **not** need Gemini. |
| `loop/world.py` | Six fixtures → rooms. |
| `loop/office.py` | `GET /api/office`, `GET /api/agents/{id}`. `canonical_agent()` aliases (`analytics` → `analytics_agent`). |
| `loop/registry.py` | Identity + allow/deny. |
| `loop/api.py` | FastAPI. CORS `*` on Cloud Run. SPA fallback includes `agents/`. Do **not** serve a tenant storefront from this app. |
| `loop/store.py` | SQLite + GCS hydrate/persist. `list_all_agent_calls`, `list_all_messages`. |
| `loop/demo_export.py` | `export-demo` / `build_demo_scenes`. `--room` fetches hosted GET `/api/rooms/{id}`. Lesson scenes use investigation `lessons[]`, not `recalled_lessons`. |

`a2a()` is **not** posted as room messages. The room UI merges `bundle.agent_calls` as “handed off” rows.

## How to run locally

```bash
./scripts/boot.sh          # warehouse + seed + API :8080 + console :3000
./scripts/verify.sh        # ruff, pytest, console lint/typecheck/build, Remotion
```

Console against hosted API (CORS is `*` on Cloud Run):

```bash
cd apps/console
env -u LOOP_STATIC NEXT_PUBLIC_API_URL=https://productos.heisenbug.in \
  ./node_modules/.bin/next dev --hostname 127.0.0.1 --port 3010
```

Use the **local** `node_modules/.bin/next`. Do not `npx next` (it has pulled Next 16 and raced `npm ci`).

`LOOP_STATIC=1` is **only** for `package-host.sh`. Unset it for `next dev`.

Local API on `:8080` does **not** allow CORS from `:3010` unless `LOOP_CONSOLE_ORIGIN=*` or `K_SERVICE` is set. Point the console at the hosted URL, or same-origin via boot (`:3000` is on the allow-list).

## How to ship to Cloud Run

**Must unset `NEXT_PUBLIC_API_URL`.** If it is `http://127.0.0.1:8080`, the static JS bakes localhost and the hosted console dies.

```bash
# When live hang room is healthy, persist sqlite to GCS first (see DEPLOY.md)
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh
```

This uploads `dist/loop-host.tgz` to `gs://mystical-timing-442601-q8-loop-host` and runs public `python:3.12-slim`, which fetches the tarball with Python `urlretrieve` (no boot `apt-get`). **`gcloud run deploy --source` fails** (no Cloud Build on this SA). Boot does not install curl/git/nodejs/npm/pip. `code_fix` extra skips on the lean worker; `github_pr` is the ship path.

After deploy: hard-refresh https://productos.heisenbug.in. Confirm `/city/campus.webp` is 200 and `/api/office` is 200.

## Remotion demo

`apps/demo` — LoopDemo 1280×720 12s from `export-demo` JSON. Cloud Run does **not** serve it.

- Hosted hang: `python3 -m loop.cli export-demo --room room_f627763ea9 -o apps/demo/out/hang.json` (needs `LOOP_ADMIN_TOKEN`). Refuses to overwrite `apps/demo/public/loop.json` unless `--force`. Copy to `public/loop.json` for render only, then `git checkout -- apps/demo/public/loop.json`.
- Lesson/verify scenes use this investigation’s `lessons[]` / `outcomes[]` and name **this metric** when still waiting.
- LoopDemo shows a Type A / Type B chip. No Safari/3DS/Northstar fallbacks.

## Fixtures (same pipeline)

| ID | Loop | Room kind |
|---|---|---|
| `safari_3ds` | A / BUG | Incident |
| `android_sdk` | A / BUG | Incident |
| `onboarding_activation` | A / BUG | Incident (not checkout) |
| `apple_pay` | B / FEATURE | Opportunity |
| `shipping_ux` | B / FEATURE | Opportunity |
| `security_exfil` | A / SECURITY | Reviews — **DENIED** |

## UI contract (do not regress)

1. **Rail always visible** (64px). Expand grows **the same aside** on every width (`w-16` ↔ `w-[min(16.25rem,calc(100vw-3.5rem))]`). No second flyout, no second Mochi. Phone still auto-collapses on navigate.
2. **Campus pins** are measured against the **drawn image box** (`object-contain` + `ResizeObserver`). Memory = pocket watch. Approvals = tram.
3. **People** in room cards and the office must show full sprites. No `h-[80px]` + `overflow-hidden` people strip. `overflow-x-auto` also clips Y — pad inside the scrollport.
4. **Rooms are one column on a phone** (`lg:grid-cols-2`).
5. Campus hero is **not** `h-screen` on a phone (that letterboxed the island and floated pins into white).
6. Keep the painted `campus.webp`. Do not replace it with Phaser / Three / `react-isometric-grid`. Interactivity is hotspots + iso floor + flipbook.
7. **Unauth `/rooms`** stays on index with Connect CTA (PR #23). No ErrorState on 401.

## Tests that matter

Prefer `./scripts/verify.sh`. At minimum:

```bash
cd services/loop && python -m pytest -q
cd apps/console && ./node_modules/.bin/tsc --noEmit
```

Inverts that must stay green: unprompted Safari detect, six fixtures one pipeline, exfil DENY, memory recall on Android, three restatements ≠ independence, HIGH gate survives restart, tool-output injection blocked, Terraform `failOpen` cannot be true.

## What not to do

- Do not restore `campus.png` / `pin.png` megabyte assets.
- Do not dark-theme the console.
- Do not host a tenant shop on this origin (`/shop`, `/company`, `public/shop`, Shop rail, Shop pin).
- Do not bias the product around Safari.
- Do not `gcloud run deploy --source`.
- Do not leave `NEXT_PUBLIC_API_URL` set while packaging.
- Do not run `npx next` in this repo.
- Do not credit Cursor/Copilot/Claude in commit trailers.
- Do not post to Slack / GitHub issues unless the user asked.
- Do not deploy until owner says go.
- Do not merge Cove PRs or leftover LOOP Cove PRs (#11–#17).
- Do not approve `act_4754e1ae24f5` (duplicates Cove #17).
- Do not overwrite a good GCS snapshot from a crash-looping instance.

## If you are stuck

1. Read [`docs/LEARNINGS.md`](docs/LEARNINGS.md) — every sharp edge we already hit.
2. Read [`docs/STATUS.md`](docs/STATUS.md) — current PRs and blockers.
3. Hosted 404 on `/rooms/:id` or `/agents/:id` → SPA placeholder `_` + `api.py` `_spa_file`.
4. Hosted rooms missing after deploy → stale GCS snapshot restored. Check persist timing.
5. Console “Failed to fetch” from a dev port → CORS or baked localhost. Check `NEXT_PUBLIC_API_URL` and Network.
6. GFE 429 “Rate exceeded” on campus → likely OOM on 2Gi, not an app rate limiter. See LEARNINGS 2026-09-03.
7. Deploy IAM → [`docs/DEPLOY.md`](docs/DEPLOY.md).
