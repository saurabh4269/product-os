# Product OS — Status

Last updated: 2026-08-29

## Hosted

**Console + API:** https://loop-5uy6fkd7bq-uc.a.run.app

`us-central1` Cloud Run service `loop` (bundle path, latest known revision `loop-00017-77b`). Public `python:3.12-slim` + GCS tarball. SQLite is ephemeral (re-seeds the **full world** on cold start).

Redeploy: `unset NEXT_PUBLIC_API_URL && ./scripts/package-host.sh && ./scripts/deploy-gcp.sh`

## What works

- Generic Type A / Type B pipeline. Six fixtures, one engine. Safari is a fixture.
- Campus home: painted island, clickable buildings, isometric floor, generated furniture, flipbook rooms. Mochi (cream) is the brand face; she and Bean sit on campus without a plate. Both show on phone. Memory on the watch, Approvals on the tram.
- Icon-rail sidebar (always on) + expand. Overlay on phone, in-flow on laptop.
- Rooms, per-bot chats (`/agents/:id`), visible handoffs. Pixel people unclipped on phone cards.
- Agent Registry (identity, permissions, version, risk). Gateway deny on production customer-record dump.
- Memory Bank: customer / product / engineering / organizational. Lesson recall on similar later signals.
- Customer Voice: contextual diagnostic + structured JSON. Media-bridge mock (no Live API / PSTN).
- Code Agent targets `apps/northstar-shop` (adapter, onboarding, checkout).
- ADK 2: 23 `LlmAgent`s / 7 Apps locally. Hosted path is the deterministic engine.
- Cheap GCP: BQ, Pub/Sub, Model Armor (`fail_open=false` on gated TF). Gateway plan-only.

## What is mocked / mapped

See README “Honest Google-product mapping”. Agent Gateway, Memory Bank, Live API, Antigravity are faithful local equivalents where the named 2026 product is not usable from this SA.

## Docs for the next agent

- [`AGENTS.md`](../AGENTS.md) — handoff, commands, UI contract
- [`docs/LEARNINGS.md`](LEARNINGS.md) — pitfalls and errors already hit
