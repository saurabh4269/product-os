# LOOP — Status

Last updated: 2026-08-29

## Hosted (live)

**Console + API (same origin):** https://loop-5uy6fkd7bq-uc.a.run.app

`us-central1` Cloud Run service `loop`. Cheap path: public `python:3.12-slim` + GCS bundle (`gs://mystical-timing-442601-q8-loop-host/loop-host.tgz`). No Cloud Build, no Artifact Registry.

On boot the warehouse is generated and the Safari loop opens unprompted (`AWAITING_APPROVAL`). SQLite is **ephemeral** (revision/instance local). That is correct for the demo; a new instance re-opens the same seeded investigation.

Redeploy: `./scripts/package-host.sh && ./scripts/deploy-gcp.sh`

## What works

- Unprompted Safari conversion-regression detection (~39k GA4-shaped events). Chrome does not fire.
- Evidence: analytics + logs + deploy timeline + consented customer-voice structured evidence (`reason=payment_timeout`).
- Three-source independence gate; HIGH-tier payment rollback; idempotent execute-once.
- Tool-output injection blocked on `after_tool_callback` and logged (`failOpen=false`).
- PII transcript redacted; media-bridge mock (no Live API / PSTN).
- 19 ADK `LlmAgent`s / 7 Apps locally; hosted control plane is the deterministic engine (no Gemini required).
- Console: Pulse (idea→impact), incident **room** (agent roster + chat + graph), approvals, outcomes, governance, opportunities (3DS retry, Apple Pay, shipping-earlier).
- Remotion demo from real investigation JSON.
- Tests: 17 passed.

## Research doc (Google Doc tabs)

Fetched https://docs.google.com/document/d/168EoiDg-PsdhUpaXX373X7malB9RZCYrTVZDvLyhn0Q (public export; Drive MCP needs desktop auth for remaining private tabs). The first tab is the original product brief this repo implements: ADK 2 agents, Safari 3DS loop, Sarah diagnostic → structured evidence, HIGH-tier HITL, organizational memory, Model Armor / Identity / Gateway, idea-to-impact, agent-room UI.

Remaining tabs were not readable from this SA (Docs API scope). Authenticate Google Drive in Cursor desktop if you want those ingested automatically.

## What is mocked

- Gemini Live API / Twilio / PSTN — media-bridge + transcript screening only.
- Agent Runtime / Identity / Gateway / SGP — Terraform **plan-only**.
- Workspace mailbox — `send_gmail` hard-deny.
- Cloud Memory Bank — local SQLite.
- Hosted persistence — ephemeral SQLite (re-seeds on cold start).

## GCP applied

| Kind | Names |
|---|---|
| Cloud Run | `loop` → https://loop-5uy6fkd7bq-uc.a.run.app |
| GCS | `gs://mystical-timing-442601-q8-loop-host/loop-host.tgz` (13 MB) |
| BigQuery | `loop_raw` (39,350 events / 663 logs / 2 deploys), `loop_metrics`, `loop_ops` |
| Pub/Sub | `loop.signals`, `loop.verification` |
| Model Armor | `loop-prompt`, `loop-response` |

Not applied (needs owner IAM): dedicated `loop-runtime` SA, project IAM, $8 budget, Artifact Registry, gated Gateway/SGP.

## Cost

- Hosted Cloud Run min_instances=0, 1Gi, max 2: typically pennies unless left under load.
- BQ + topics + Armor templates: pennies.
- Do not apply gated Terraform.

## Next (optional)

1. Authenticate Google Drive in Cursor desktop to ingest remaining research tabs.
2. `TF_VAR_billing_account` for the $8 alert.
3. Review `infra/terraform/gated` plan only (`fail_open = false`).
4. Cloud SQL / GCS sqlite if you want investigations to survive Cloud Run scale-to-zero.
