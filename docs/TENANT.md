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
5. **Mail / calendar** — skip until Workspace OAuth. `send_gmail` stays denied.

Hosted SQLite is ephemeral. Cold start re-seeds the tenant from `LOOP_TENANT_REPO`, `LOOP_TENANT_DEPLOY_URL`, and `LOOP_TENANT_BOOTSTRAP_TOKEN`.

## Secrets (names only)

On Cloud Run `loop`: `LOOP_GITHUB_TOKEN`, `LOOP_TENANT_BOOTSTRAP_TOKEN`, `LOOP_TENANT_REPO`, `LOOP_TENANT_DEPLOY_URL`.

On Cloud Run `northstar`: `LOOP_TENANT_TOKEN` (same raw value as the bootstrap token), `LOOP_OS_URL`, `LOOP_TENANT_ID`.

Still needs the user: Gmail/Calendar OAuth (`LOOP_GMAIL_ACCESS_TOKEN`, `LOOP_CALENDAR_ACCESS_TOKEN`). No PSTN. No second GCP project.

## Do not

- Serve tenant HTML from FastAPI or `apps/console/public`.
- Add a Shop rail item or campus Shop pin.
- Treat `apps/northstar-shop` as a company.
- Treat [#6](https://github.com/saurabh4269/product-os/pull/6) as product direction. The **tip of `main` deletes the shop**. Follow #7.
