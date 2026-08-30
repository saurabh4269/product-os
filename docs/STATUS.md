# Product OS — Status

Last updated: 2026-08-30

## Hosted

**Product OS (console + API):** https://loop-5uy6fkd7bq-uc.a.run.app

`us-central1` Cloud Run service `loop` (bundle path, revision `loop-00032-q4p`). Public `python:3.12-slim` + GCS tarball. `--min-instances 1` so SQLite and the UI stay warm. Vendor wheels are built **inside** `python:3.12-slim` so they match the image (local Kali is 3.13). `/shop` and `/company` 404.

**Product Y (Northstar):** https://northstar-5uy6fkd7bq-uc.a.run.app

Cloud Run service `northstar` (revision `northstar-00008-xj7`). Repo: https://github.com/saurabh4269/northstar

Redeploy OS: `unset NEXT_PUBLIC_API_URL && ./scripts/package-host.sh && ./scripts/deploy-gcp.sh`  
(needs `LOOP_TENANT_REPO`, `LOOP_TENANT_DEPLOY_URL`, `LOOP_TENANT_BOOTSTRAP_TOKEN`, `LOOP_GITHUB_TOKEN` in the environment)

Redeploy Y: `LOOP_TENANT_TOKEN=… ./scripts/deploy.sh` in the northstar repo.

## What works

- Generic Type A / Type B pipeline. Six fixtures, one engine. Safari is a fixture.
- Campus home: painted island, clickable buildings, isometric floor, generated furniture, flipbook rooms. Mochi (cream / Bubu) is the rail logo only — the sitting pair is off the campus. Memory on the watch, Approvals on the tram. No Shop pin.
- Icon-rail sidebar (always on) + expand in place on every width (no second flyout). Traces is on the rail. Connect, not Shop.
- Rooms, per-bot chats (`/agents/:id`), visible handoffs. Pixel people unclipped on phone cards.
- Agent Registry (identity, permissions, version, risk). Gateway deny on production customer-record dump.
- Memory Bank: customer / product / engineering / organizational. Lesson recall on similar later signals.
- Customer Voice: contextual diagnostic + structured JSON. Media-bridge mock (no Live API / PSTN). Tenant feedback POSTs `/api/t/{id}/voice` and opens a research room.
- Code Agent fixture targets stay in `apps/northstar-shop` (JS adapters only). Product OS does **not** host a tenant shop.
- Tenant wire: `/connect` form (repo, deploy URL, rotate token — never echoed). Token-gated `/api/t/{id}/flags|signals|voice`. Ingest opens or joins rooms. Approve HIGH flips `pay_sdk_4_3` and opens a real PR on the tenant repo. `merged` stays false. Mail/calendar skip without OAuth.
- End-to-end proven: Northstar checkout showed SDK 4.3 → HIGH approve in OS → flags off + [PR #2](https://github.com/saurabh4269/northstar/pull/2) (open, not merged) → checkout shows 4.2.1 from live flags. Place-order then succeeds.
- ADK 2: 23 `LlmAgent`s / 7 Apps locally. Hosted path is the deterministic engine.
- Cheap GCP: BQ, Pub/Sub, Model Armor (`fail_open=false` on gated TF). Gateway plan-only.

## Next

Workspace OAuth for Gmail draft / Calendar. Optional Live. Agent Gateway still plan-only. See [`docs/TENANT.md`](TENANT.md).

## PRs

All numbered PRs through [#8](https://github.com/saurabh4269/product-os/pull/8) are on `main`. #6 shop files are **not** at tip.

## What is mocked / mapped

See README “Honest Google-product mapping”. Agent Gateway, Memory Bank, Live API, Antigravity are faithful local equivalents where the named 2026 product is not usable from this SA.

## Docs for the next agent

- [`AGENTS.md`](../AGENTS.md) — handoff, commands, UI contract, named references
- [`docs/PLAN_NEXT.md`](PLAN_NEXT.md) — later work (OAuth, Live, Gateway)
- [`docs/TENANT.md`](TENANT.md) — Northstar vs OS; secret **names**
- [`docs/LEARNINGS.md`](LEARNINGS.md) — pitfalls already hit
- [`docs/RESEARCH_LEARNINGS.md`](RESEARCH_LEARNINGS.md) — PRD research traps
