# Tenant product — not this repo

Product OS is a production control plane. It does **not** host the customer’s product.

| Piece | What it is | Where it lives |
|---|---|---|
| Product OS | Campus, rooms, agents, approvals, memory | `github.com/saurabh4269/product-os` · Cloud Run `loop` |
| Tenant app | The thing customers use (shop, SaaS, …) | **Separate git repo + separate deploy** |
| Connection | Flags, signals, customer voice, PRs | After onboard: OS talks to that repo and that URL |

A sales demo is the first tenant, on the same path a real customer would use. Do not put a storefront back on `loop` (`/shop`, `/company`, `public/shop`).

`apps/northstar-shop` in this repo is **fixture JS only** (engine Code Agent targets). It is not the demo app.

## Blocked on the user

The next agent cannot create a GitHub org or a second repo (`gh` is read-only). Wait for:

1. **Empty tenant repo** — e.g. `saurabh4269/northstar` or `org/northstar`. Write access for this agent (add the repo to the Cloud Agent environment, or a fine-grained PAT as a **secret**, not in chat).
   - Scopes: `contents:write`, `pull_requests:write`, `issues:write`, `metadata:read`.
2. **Second deploy** — new Cloud Run service (e.g. `northstar` in `mystical-timing-442601-q8`) **or** Vercel / other. Confirm if the same GCP project is OK.
3. **Shared service token** — Cloud Run secret on both services (name only in chat): shop reads flags / posts voice; OS verifies the token.
4. **Cursor environment** — both repos on the same Cloud Agent run.

Not needed yet: custom domain, real GA4/Ads/BQ, GitHub App review, second GCP project, SSO.

## After those land

1. Build the demo shop **in the tenant repo**.
2. Deploy it to the second service.
3. Onboard that org in Product OS (repo + deploy URL + token).
4. Flags and PRs point at **their** git. Approve in OS → PR on tenant repo → their deploy updates. OS never merges or deploys the tenant app.

## Do not

- Serve tenant HTML from FastAPI or `apps/console/public`.
- Add a Shop rail item or campus Shop pin.
- Treat `apps/northstar-shop` as a company.
- Treat [#6](https://github.com/saurabh4269/product-os/pull/6) as product direction. GitHub marked it merged because those commits sit in history; the **tip of `main` deletes the shop**. Follow #7.
