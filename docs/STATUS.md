# LOOP — Status

Last updated: 2026-08-29 (plan committed; implementation in progress)

## What works

- `docs/PRD.md` is the verified spec.
- `docs/PLAN.md` is the binding architecture for this repo.
- Google ADK skills installed globally from `google/adk-docs` (`.agents/skills`).
- Source-of-truth clones used for ADK 2.8.0 (`App`, `ResumabilityConfig`, `ModelArmorPlugin`, `after_tool_callback`).

## What is mocked

- Not yet implemented — see plan.

## What needs you

- Agent Gateway / SGP / telephony: Terraform plan-only + commands (after infra lands).
- Workspace OAuth consent for a real mailbox (not required for the synthetic loop).

## Cost estimate

- Local demo: $0.
- Cheap GCP (BQ + Pub/Sub + Armor templates + budget + optional Cloud Run): target well under a few dollars if applied.

## Next

Implement warehouse, engine, ADK agents, console, Remotion, Terraform, verify, draft PR.
