# AGENTS.md — handoff for the next agent

You are continuing **Product OS (LOOP)**. Start from **`main`**. Read this file first, then [`docs/LEARNINGS.md`](docs/LEARNINGS.md), [`docs/RESEARCH_LEARNINGS.md`](docs/RESEARCH_LEARNINGS.md), [`docs/TENANT.md`](docs/TENANT.md), and [`docs/PLAN_NEXT.md`](docs/PLAN_NEXT.md) before you change deploy, the campus map, the console API URL, or anything that looks like a shop.

Repo: `github.com/saurabh4269/product-os`  
Live: https://loop-5uy6fkd7bq-uc.a.run.app  
GCP: `mystical-timing-442601-q8` · `us-central1` · Cloud Run service `loop`  
Product Y: `github.com/saurabh4269/northstar` · Cloud Run `northstar` · https://northstar-5uy6fkd7bq-uc.a.run.app

## What this product is

A **generic Product OS**: observe the product, open work into rooms, coordinate agents, gate risky changes, measure, remember.

It is **not** a Safari / 3DS / payments app. Those six scenarios are **fixtures** that all go through one pipeline.

- **Type A** — something broke → fix (BUG path).
- **Type B** — something could be better → improve (FEATURE path).
- After root cause: BUG vs FEATURE. Do not special-case one demo in architecture or UI.

The UI is a **campus + multi-room chat** (Grok / OpenClaw energy): pixel agents, visible handoffs, per-bot chats. It is not a CRUD dashboard and not a dark “war room.”

## References the user pointed at

These are the named products, looks, and decisions from this chat. Open them before you change campus, mascots, or the rail. Do not copy licensed art.

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
| **Google Doc as “the office”** | Tried; unreadable (auth). Office is in-product. | `office-floor.tsx` + iso floor |
| **Safari / 3DS** | One **fixture**, not the product. Do not bias UI or architecture around it. | `safari_3ds` in the fixture table |

**Mascot now:** Mochi is the 32px rail mark (waves on home-link hover). PNG only — iPad Safari drops WebP alpha. No sitting pair on campus, phone or desktop. Do not restore Pip.

**Live / GitHub**

- Console + API: https://loop-5uy6fkd7bq-uc.a.run.app (also `https://loop-632958340118.us-central1.run.app`)
- This agent run: https://cursor.com/agents/bc-8c53e2be-2abe-4034-a712-16e9ff15e32b
- Hosted revision: `loop-00033-6mz` (Connect + tenant APIs + GitHub PR on approve; `/shop` 404; min-instances 1)
- PRs [#1](https://github.com/saurabh4269/product-os/pull/1)–[#8](https://github.com/saurabh4269/product-os/pull/8) are on `main`. #6’s shop commits are in history but **deleted at tip**. Do not restore `/shop`.

**Product Y:** https://github.com/saurabh4269/northstar · https://northstar-5uy6fkd7bq-uc.a.run.app (Cloud Run `northstar`)

## Next work

Workspace OAuth (Gmail draft / Calendar). Optional Live. Agent Gateway still plan-only. Tenant **connectors** are in this repo; Product Y is the other repo. Do **not** rebuild a storefront here.

## Binding rules

| Rule | Detail |
|---|---|
| Safety | `fail_open = false`. Tool-output armor on. Exfil of production customer records is **DENY** via Gateway **identity**, not a prompt. |
| Models | IDs only in [`config/models.yaml`](config/models.yaml). Default `gemini-3.5-flash`. Never set sampling on 3.6 / 3.5-lite. |
| Cost | Cheap GCP only (BQ, Pub/Sub, Cloud Run, Model Armor). Agent Gateway / SGP / telephony stay **plan-only**. |
| Hosted SQLite | Ephemeral. Cold start re-seeds the world. Room IDs change. Do not hard-code hosted room IDs. |
| Theme | Light Apple-like: `#f5f5f7` / campus `#eef2ee`, ink `#1d1d1f`, accent `#0071e3`, Inter. No Instrument Serif, no dark class, no status-color dots. **Mochi** (cream / “Bubu”) is the rail logo only. Do **not** put the sitting duo on the campus — they read as a sticker, not the product. |
| Art | Campus is `apps/console/public/city/campus.webp` (~75KB) + `campus.jpg`. **Do not re-add the 2MB PNG.** |
| Tenant product | Product OS is the control plane. **Do not host a customer shop, ads page, or demo storefront on this origin** (`/shop`, `/company`, `public/shop`). The tenant app lives in its own repo and deployment. |
| Git | Commits look human. No AI `Co-authored-by` / author overrides. |

## Repo map

```
apps/console/          Next 15 console (rooms, campus, office, agents)
apps/northstar-shop/   Fixture patch targets only. Not a storefront. Not hosted here.
apps/demo/             Remotion walkthrough
services/loop/         Python control plane (engine, store, API, office, world, registry)
config/models.yaml     Only place model IDs live
data/                  Warehouse generator
playbooks/             SKILL-shaped lessons
infra/terraform/cheap  Applied. gated/ is plan-only
scripts/               boot, verify, package-host, deploy-gcp
docs/PRD.md            Spec (binding MUST)
docs/PLAN.md           Architecture this code implements
docs/LEARNINGS.md          Pitfalls — read before you touch host/UI
docs/RESEARCH_LEARNINGS.md PRD research traps (failOpen, telephony, quotas)
docs/TENANT.md             Tenant app is a separate repo. What we still need.
docs/PLAN_NEXT.md          What to build next so Company X can actually connect Product Y.
```

### Console (what you will edit)

| File | Role |
|---|---|
| `components/shell.tsx` | One rail that grows in place on every width (no second flyout). `localStorage` key `loop-sidebar`. `[` toggles. |
| `components/mascot.tsx` | Mochi (cream) is the rail mark. Pair is two PNG sprites (not WebP — iPad Safari drops alpha). They watch / hop / wave. |
| `components/city-map.tsx` | Painted campus. Pins **and building ellipses** are % of the contained image box. |
| `components/iso-office.tsx` | 2:1 isometric floor (Claude City energy, no Phaser). |
| `components/work-flipbook.tsx` | Click-the-work pages. Do not wrap room cards in a naked `<Link>`. |
| `lib/furniture.ts` | Deterministic pixel furniture. |
| `components/pixel-office.tsx` | Pixel people. Do not put sprites in a short `overflow-hidden` + `overflow-x-auto` box. |
| `components/office-floor.tsx` | Desk grid + handoffs. 2 columns on a phone. |
| `lib/api.ts` | `NEXT_PUBLIC_API_URL` or `""` in production (same origin). |
| `app/connect/page.tsx` | Tenant wire. Not a shop. |
| `app/agents/[id]/layout.tsx` | `generateStaticParams` `{ id: "_" }` — required for static export. Same for rooms/investigations. |

### Control plane

| File | Role |
|---|---|
| `loop/engine.py` | Deterministic loop. Hosted path does **not** need Gemini. |
| `loop/world.py` | Six fixtures → rooms. |
| `loop/office.py` | `GET /api/office`, `GET /api/agents/{id}`. `canonical_agent()` aliases (`analytics` → `analytics_agent`). |
| `loop/registry.py` | Identity + allow/deny. |
| `loop/api.py` | FastAPI. CORS `*` on Cloud Run. SPA fallback includes `agents/`. Do **not** serve a tenant storefront from this app. |
| `loop/store.py` | SQLite. `list_all_agent_calls`, `list_all_messages`. |

`a2a()` is **not** posted as room messages. The room UI merges `bundle.agent_calls` as “handed off” rows.

## How to run locally

```bash
./scripts/boot.sh          # warehouse + seed + API :8080 + console :3000
./scripts/verify.sh        # ruff, pytest, console lint/typecheck/build, Remotion
```

Console against hosted API (CORS is `*` on Cloud Run):

```bash
cd apps/console
env -u LOOP_STATIC NEXT_PUBLIC_API_URL=https://loop-5uy6fkd7bq-uc.a.run.app \
  ./node_modules/.bin/next dev --hostname 127.0.0.1 --port 3010
```

Use the **local** `node_modules/.bin/next`. Do not `npx next` (it has pulled Next 16 and raced `npm ci`).

`LOOP_STATIC=1` is **only** for `package-host.sh`. Unset it for `next dev`.

Local API on `:8080` does **not** allow CORS from `:3010` unless `LOOP_CONSOLE_ORIGIN=*` or `K_SERVICE` is set. Point the console at the hosted URL, or same-origin via boot (`:3000` is on the allow-list).

## How to ship to Cloud Run

**Must unset `NEXT_PUBLIC_API_URL`.** If it is `http://127.0.0.1:8080`, the static JS bakes localhost and the hosted console dies.

```bash
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh
```

This uploads `dist/loop-host.tgz` to `gs://mystical-timing-442601-q8-loop-host` and runs public `python:3.12-slim`, which curl’s the tarball. **`gcloud run deploy --source` fails** (no Cloud Build on this SA).

After deploy: hard-refresh the hosted URL. Confirm `/city/campus.webp` is 200 and `/api/office` is 200.

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

1. **Rail always visible** (64px). Expand grows **the same aside** on every width (`w-16` ↔ `w-[min(16.25rem,calc(100vw-3.5rem))]`). No second flyout, no second Mochi. Phone still auto-collapses on navigate. Do not go back to hamburger-only or a squeezed always-on 248px column on a phone.
2. **Campus pins** are measured against the **drawn image box** (`object-contain` + `ResizeObserver`). Memory = pocket watch. Approvals = tram.
3. **People** in room cards and the office must show full sprites. No `h-[80px]` + `overflow-hidden` people strip. `overflow-x-auto` also clips Y — pad inside the scrollport.
4. **Rooms are one column on a phone** (`lg:grid-cols-2`).
5. Campus hero is **not** `h-screen` on a phone (that letterboxed the island and floated pins into white).
6. Keep the painted `campus.webp`. Do not replace it with Phaser / Three / `react-isometric-grid`. Interactivity is hotspots + iso floor + flipbook.

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

## If you are stuck

1. Read [`docs/LEARNINGS.md`](docs/LEARNINGS.md) — every sharp edge we already hit.
2. Hosted 404 on `/rooms/:id` or `/agents/:id` → SPA placeholder `_` + `api.py` `_spa_file`.
3. Hosted API empty / new room IDs → cold start, SQLite reset. Hit `/` or wait for lifespan seed.
4. Console “Failed to fetch” from a dev port → CORS or baked localhost. Check `NEXT_PUBLIC_API_URL` and Network.
5. Deploy IAM → [`docs/DEPLOY.md`](docs/DEPLOY.md).
