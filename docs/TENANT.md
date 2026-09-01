# Tenant product — not this repo

Product OS is a production control plane. It does **not** host the customer’s product.

| Piece | What it is | Where it lives |
|---|---|---|
| Product OS | Campus, rooms, agents, approvals, memory | `github.com/saurabh4269/product-os` · Cloud Run `loop` · https://loop-5uy6fkd7bq-uc.a.run.app |
| Tenant app | Cove (Product Y) | `github.com/saurabh4269/cove` · Cloud Run `cove` · https://cove-5uy6fkd7bq-uc.a.run.app |
| Connection | Flags, signals, customer voice, PRs | Tenant id `acme`. Connect desk at `/connect` |

Do not put a storefront back on `loop` (`/shop`, `/company`, `public/shop`).

`apps/northstar-shop` in this repo is **fixture JS only** (engine Code Agent targets). It is not the demo app. Cove is a real Next.js storefront (Epic Design Labs ecommerce starter fork) with catalog, cart, checkout, and admin UI — plus the LOOP wire.

## What is wired

1. **Connect** — repo, deploy URL, hashed token (never echoed). Rotate via `POST /api/tenants/{id}/token`.
2. **Flags** — `GET /api/t/acme/flags` with `Authorization: Bearer`. Approve HIGH flips `pay_sdk_4_3` off. Cove checkout reads that live via `/api/loop/flags`.
3. **Signals / voice** — `POST /api/t/acme/signals` and `/voice` open or join rooms (generic, not Safari-special). Cove checkout hang + `/feedback` post through `/api/loop/ingest`.
4. **GitHub** — HIGH approve opens a PR on `saurabh4269/cove` that writes `config/flags.json`. OS never merges. OS never prod-deploys Cove.
5. **Google Workspace OAuth** — Connect → Google Auth Platform Web client → `/api/oauth/google/start` (offline consent). Refresh token stored under `LOOP_DATA_DIR`. Gmail draft + Calendar hold call the product APIs. `send_gmail` stays denied. Agent Identity / GEAP token injection is not used (plan-only).
6. **Investigation / research / improve / coordinate / product-intel** — generic APIs live on hosted `loop` (simulated Calendar/phone until OAuth/Twilio are set).

Hosted SQLite hydrates from GCS (`LOOP_STATE_GCS_URI`) on cold start when configured. Tenant flags persist via `LOOP_FLAGS_GCS_URI`. Firestore mirrors Memory Bank lessons when `LOOP_FIRESTORE_MEMORY=1`. Re-authorize Workspace after a cold wipe if the refresh token lived only on disk.

Wire/onboard requires `LOOP_ADMIN_TOKEN` on hosted (`LOOP_EVAL=0`). Paste the token once on Connect — it stays in browser sessionStorage, not in the static bundle.

## Secrets (names only)

On Cloud Run `loop`: `LOOP_GITHUB_TOKEN`, `LOOP_TENANT_BOOTSTRAP_TOKEN`, `LOOP_TENANT_REPO=saurabh4269/cove`, `LOOP_TENANT_DEPLOY_URL=https://cove-5uy6fkd7bq-uc.a.run.app`, `LOOP_PUBLIC_URL`. Optional: `LOOP_GOOGLE_OAUTH_CLIENT_ID`, `LOOP_GOOGLE_OAUTH_CLIENT_SECRET` (or paste once on Connect), `TWILIO_*`, `GOOGLE_API_KEY`.

On Cloud Run `cove`: `LOOP_TENANT_TOKEN` (same raw value as the bootstrap token), `LOOP_OS_URL`, `LOOP_TENANT_ID`.

## Still needs your browser / accounts

| Item | Why I cannot finish it from here |
|---|---|
| Google OAuth Web client + consent click | Auth Platform UI + your Google login as test user |
| Twilio trial SID/token/number | Your Twilio account; destination must be verified on trial |
| `GOOGLE_API_KEY` on Cloud Run | Create in AI Studio and set on `loop` (Gemini flag is already true via GCP project; key improves call dialogue) |

See `config.template` for the full env list.
## Phone (Twilio free trial + Gemini credits)

Google does not give free outbound PSTN for ADK. Winners used ElevenLabs; we avoid that bill:

1. [Twilio free trial](https://www.twilio.com/try-twilio) (~$15 credit) → buy/verify a US number.
2. Set on Cloud Run `loop`: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`.
3. Set `GOOGLE_API_KEY` (AI Studio / GCP) for spoken replies. `LOOP_PUBLIC_URL` must be the public loop URL so Twilio can webhook.
4. In a room: **Place call**, or collect a number on Cove `/feedback`.

Without Twilio, `place_call` returns an honest **skipped** connector report.

Authorize in browser:

1. [Google Auth Platform overview](https://console.cloud.google.com/auth/overview?project=mystical-timing-442601-q8) — branding + External/Testing audience; add yourself as a test user.
2. [Create Web client](https://console.cloud.google.com/auth/clients/create?project=mystical-timing-442601-q8) — redirect URI `https://loop-5uy6fkd7bq-uc.a.run.app/api/oauth/google/callback`.
3. Paste client ID + secret on Connect, then open [Authorize](https://loop-5uy6fkd7bq-uc.a.run.app/api/oauth/google/start).

No PSTN. No second GCP project.

## Do not

- Serve tenant HTML from FastAPI or `apps/console/public`.
- Add a Shop rail item or campus Shop pin.
- Treat `apps/northstar-shop` as a company.
- Treat [#6](https://github.com/saurabh4269/product-os/pull/6) as product direction. The **tip of `main` deletes the shop**. Follow #7.
- Restore Northstar as Product Y — it was the dummy shop; Cove replaced it.
