# Tenant product — not this repo

Product OS is a production control plane. It does **not** host the customer’s product.

| Piece | What it is | Where it lives |
|---|---|---|
| Product OS | Campus, rooms, agents, approvals, memory | `github.com/saurabh4269/product-os` · Cloud Run `loop` · https://loop-5uy6fkd7bq-uc.a.run.app |
| Tenant app | Northstar (Product Y) | `github.com/saurabh4269/northstar` · Cloud Run `northstar` · https://northstar-5uy6fkd7bq-uc.a.run.app |
| Connection | Flags, signals, customer voice, PRs | Tenant id `acme`. Connect desk at `/connect` |

Do not put a storefront back on `loop` (`/shop`, `/company`, `public/shop`).

`apps/northstar-shop` in this repo is **fixture JS only** (engine Code Agent targets). It is not the demo app.

## What is wired

1. **Connect** — repo, deploy URL, hashed token (never echoed). Rotate via `POST /api/tenants/{id}/token`.
2. **Flags** — `GET /api/t/acme/flags` with `Authorization: Bearer`. Approve HIGH flips `pay_sdk_4_3` off. Northstar checkout reads that live.
3. **Signals / voice** — `POST /api/t/acme/signals` and `/voice` open or join rooms (generic, not Safari-special).
4. **GitHub** — HIGH approve opens a PR on `saurabh4269/northstar` that writes `config/flags.json`. OS never merges. OS never prod-deploys Northstar.
5. **Google Workspace OAuth** — Connect → Google Auth Platform Web client → `/api/oauth/google/start` (offline consent). Refresh token stored under `LOOP_DATA_DIR`. Gmail draft + Calendar hold call the product APIs. `send_gmail` stays denied. Agent Identity / GEAP token injection is not used (plan-only).

Hosted SQLite is ephemeral. Cold start re-seeds the tenant from `LOOP_TENANT_REPO`, `LOOP_TENANT_DEPLOY_URL`, and `LOOP_TENANT_BOOTSTRAP_TOKEN`. Re-authorize Workspace after a cold wipe if the refresh token lived only on disk.

## Secrets (names only)

On Cloud Run `loop`: `LOOP_GITHUB_TOKEN`, `LOOP_TENANT_BOOTSTRAP_TOKEN`, `LOOP_TENANT_REPO`, `LOOP_TENANT_DEPLOY_URL`, `LOOP_PUBLIC_URL`. Optional: `LOOP_GOOGLE_OAUTH_CLIENT_ID`, `LOOP_GOOGLE_OAUTH_CLIENT_SECRET` (or paste once on Connect).

On Cloud Run `northstar`: `LOOP_TENANT_TOKEN` (same raw value as the bootstrap token), `LOOP_OS_URL`, `LOOP_TENANT_ID`.

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
