# Product OS — Status

Last updated: 2026-08-30

## Hosted

**Product OS (console + API):** https://loop-5uy6fkd7bq-uc.a.run.app

`us-central1` Cloud Run service `loop` (bundle path, revision `loop-00034-tm9`). Public `python:3.12-slim` + GCS tarball. `--min-instances 1` so SQLite and the UI stay warm. Vendor wheels are built **inside** `python:3.12-slim` so they match the image (local Kali is 3.13). `/shop` and `/company` 404. Workspace OAuth consent is on Connect.

**Product Y (Cove):** https://cove-5uy6fkd7bq-uc.a.run.app

Cloud Run service `cove` (revision `cove-00001-s5b`). Repo: https://github.com/saurabh4269/cove  
Real Next.js storefront (Epic Design Labs ecommerce starter + LOOP flags/signals/voice). Northstar is retired as Product Y.

Redeploy OS: `unset NEXT_PUBLIC_API_URL && ./scripts/package-host.sh && ./scripts/deploy-gcp.sh`  
(needs `LOOP_TENANT_REPO=saurabh4269/cove`, `LOOP_TENANT_DEPLOY_URL`, `LOOP_TENANT_BOOTSTRAP_TOKEN`, `LOOP_GITHUB_TOKEN` in the environment)

Redeploy Y: `LOOP_TENANT_TOKEN=… ./scripts/deploy.sh` in the cove repo.

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
- Live rooms: WebSocket hub, agent_callback, presence handoff rail, Work/Transcript + flip artifacts (kind tones), typed A2A, skip-if-done approve, **live fleet graph** (parallel fan-out, review/critique `output_key`, funnel_stage bus), `POST /api/signals`, `POST /api/memory`, `GET /api/status` + campus StatusStrip + scenario chips, gateway deny artifacts. Contract: [`packages/contracts/api.md`](../packages/contracts/api.md).
- End-to-end path: Cove checkout with SDK 4.3 hangs → signal into OS → HIGH approve → flags off + PR on `saurabh4269/cove` → checkout shows 4.2.1. (Earlier proof used Northstar PR #2; Cove is the live tenant now.)
- ADK 2: 23 `LlmAgent`s / 7 Apps locally + Workflow soft-attach (JoinNode fan-out, critique). Hosted path is the deterministic engine.
- Cheap GCP: BQ, Pub/Sub, Model Armor (`fail_open=false` on gated TF). Gateway plan-only.

## Next

Create the Google Auth Platform Web client, paste it on Connect, then open `/api/oauth/google/start`. Optional Live. Agent Gateway still plan-only. See [`docs/TENANT.md`](TENANT.md).

## PRs

All numbered PRs through [#8](https://github.com/saurabh4269/product-os/pull/8) are on `main`. #6 shop files are **not** at tip.

## What is mocked / mapped

See README “Honest Google-product mapping”. Agent Gateway, Memory Bank, Live API, Antigravity are faithful local equivalents where the named 2026 product is not usable from this SA.

## Docs for the next agent

- [`AGENTS.md`](../AGENTS.md) — handoff, commands, UI contract, named references
- [`docs/PLAN_NEXT.md`](PLAN_NEXT.md) — later work (OAuth, Live, Gateway)
- [`docs/TENANT.md`](TENANT.md) — Cove vs OS; secret **names**
- [`docs/LEARNINGS.md`](LEARNINGS.md) — pitfalls already hit
- [`docs/RESEARCH_LEARNINGS.md`](RESEARCH_LEARNINGS.md) — PRD research traps
