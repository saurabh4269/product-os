# Product OS — Status

Last updated: 2026-08-30

## Hosted

**Console + API:** https://loop-5uy6fkd7bq-uc.a.run.app

`us-central1` Cloud Run service `loop` (bundle path, latest known revision `loop-00025-pp5`). Public `python:3.12-slim` + GCS tarball. SQLite is ephemeral (re-seeds the **full world** on cold start).

Redeploy: `unset NEXT_PUBLIC_API_URL && ./scripts/package-host.sh && ./scripts/deploy-gcp.sh`

## What works

- Generic Type A / Type B pipeline. Six fixtures, one engine. Safari is a fixture.
- Campus home: painted island, clickable buildings, isometric floor, generated furniture, flipbook rooms. Mochi (cream / Bubu) is the rail logo only — the sitting pair is off the campus. Memory on the watch, Approvals on the tram.
- Icon-rail sidebar (always on) + expand in place on every width (no second flyout). Traces is on the rail.
- Rooms, per-bot chats (`/agents/:id`), visible handoffs. Pixel people unclipped on phone cards.
- Agent Registry (identity, permissions, version, risk). Gateway deny on production customer-record dump.
- Memory Bank: customer / product / engineering / organizational. Lesson recall on similar later signals.
- Customer Voice: contextual diagnostic + structured JSON. Media-bridge mock (no Live API / PSTN).
- Code Agent fixture targets stay in `apps/northstar-shop` (JS adapters only). Product OS does **not** host a tenant shop.
- ADK 2: 23 `LlmAgent`s / 7 Apps locally. Hosted path is the deterministic engine.
- Cheap GCP: BQ, Pub/Sub, Model Armor (`fail_open=false` on gated TF). Gateway plan-only.

## Next (blocked on the user)

Tenant app is **not** in this repo. Waiting on a tenant git repo, a second deploy, a shared token secret, and both repos on the Cloud Agent environment. See [`docs/TENANT.md`](TENANT.md).

## PRs

| PR | Action |
|---|---|
| [#7](https://github.com/saurabh4269/product-os/pull/7) | Merge — OS is the control plane; sitters off campus; no `/shop` |
| [#5](https://github.com/saurabh4269/product-os/pull/5) | Close — contained in #7 |
| [#6](https://github.com/saurabh4269/product-os/pull/6) | Close — hosted the shop on this origin |

## What is mocked / mapped

See README “Honest Google-product mapping”. Agent Gateway, Memory Bank, Live API, Antigravity are faithful local equivalents where the named 2026 product is not usable from this SA.

## Docs for the next agent

- [`AGENTS.md`](../AGENTS.md) — handoff, commands, UI contract, named references
- [`docs/TENANT.md`](TENANT.md) — tenant vs OS; what we still need from the user
- [`docs/LEARNINGS.md`](LEARNINGS.md) — pitfalls already hit
