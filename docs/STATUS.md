# LOOP — Status

Last updated: 2026-08-29

## What works

- Unprompted Safari conversion-regression detection on a seeded GA4-shaped warehouse (35 days, ~39k events). Chrome does not fire.
- Investigation engine: evidence from analytics + logs + deploy timeline; three-source independence gate; HIGH-tier payment action.
- Durable SQLite HITL: approval survives process restart; side effect executes once (idempotency key).
- Learning writes a measured outcome + lesson (`RESOLVED` after flag rollback).
- `ToolOutputArmorPlugin.after_tool_callback` blocks injected GitHub issue / tool-output prompts and logs a `PolicyVerdict`.
- PII transcript redaction; media-bridge mock (no Live API / PSTN).
- 19 ADK `LlmAgent`s across 7 Apps with `ResumabilityConfig(is_resumable=True)` and plugins.
- Next.js console: Pulse, investigation (graph + timeline), approval queue, outcomes, governance, opportunities.
- Remotion `LoopDemo` renders from real exported investigation JSON (no lorem).
- CI assertions: `fail_open = false` on Model Armor CONTENT_AUTHZ; default model `gemini-3.5-flash`; no sampling on 3.6-flash / 3.5-flash-lite.
- `./scripts/boot.sh` and `./scripts/verify.sh`.
- Tests: 17 passed (engine, safety, ads join, media-bridge, ADK apps, infra).
- Console verified against the live API: Pulse shows the Safari drop and HIGH investigation; evidence graph has analytics + logs + deploy plus a dashed untrusted GitHub node; approval queue executes once; outcome ledger shows Safari `9.3% → 17.0%` RESOLVED; governance shows `failOpen=false` and the BLOCK on `read_github_issue`.

## What is mocked

- Gemini Live API / Twilio / PSTN — media-bridge interface + transcript screening only.
- Agent Runtime (`reasoningEngines`), Agent Identity, Agent Gateway, SGP — Terraform **plan-only** in `infra/terraform/gated`.
- Workspace MCP OAuth mailbox — draft-only `send_gmail` hard-deny.
- Cloud Memory Bank / Skill Registry — local SQLite + filesystem playbook.
- Model Armor API calls in CI — deterministic plugin fallback (templates exist in GCP).

## GCP applied (2026-08-29, `us-central1`)

Applied with the Cloud Agent SA (credentials never echoed or committed):

| Kind | Names |
|---|---|
| APIs | BigQuery, Pub/Sub, Cloud Run, Model Armor, Logging, Monitoring, IAM, Service Usage |
| Datasets | `loop_raw`, `loop_metrics`, `loop_ops` |
| Topics | `loop.signals`, `loop.verification` |
| Model Armor templates | `loop-prompt`, `loop-response` (`MEDIUM_AND_ABOVE`, injection filter) |

Cheap Terraform re-apply is clean (`No changes`).

Warehouse loaded into BigQuery (2026-08-29): `loop_raw.events` 39,350 rows, `loop_raw.logs` 663 rows, `loop_raw.deploys` 2 rows. Cloud Run source deploy blocked — this SA cannot enable `cloudbuild.googleapis.com`.

Console E2E (this run): investigation `inv_ef8c3da145f3`, action `act_6b0f361a652f` approved once → `RESOLVED`. Queue empty after. Interactive Cloud Agent browser was usage-capped; pages were driven via the API and captured with headless Chrome.

## What needs you (IAM / entitlements)

This SA **cannot**:

- `iam.serviceAccounts.create` — new `loop-runtime` SA
- `resourcemanager.projects.setIamPolicy` — project IAM bindings
- `artifactregistry.repositories.get` / Cloud Build — image push + Cloud Run source deploy
- Enable `artifactregistry.googleapis.com` / `cloudbuild.googleapis.com`

Exact owner commands: [`docs/DEPLOY.md`](DEPLOY.md).

After those grants:

```bash
export TF_VAR_create_runtime_sa=true
export TF_VAR_grant_project_iam=true
# optional $8 budget: export TF_VAR_billing_account=XXXX
./scripts/load-bq.sh
./scripts/deploy-gcp.sh
```

Gated stack (Agent Gateway / SGP / telephony): `cd infra/terraform/gated && terraform plan` — **do not apply** unless you accept Preview cost. Confirm `fail_open = false`.

## Cost estimate

- Local demo + CI: $0.
- Cheap GCP now live (empty BQ + two topics + Armor templates): typically pennies/day until you load data or serve traffic.
- Budget alert at $8 is ready when you pass `TF_VAR_billing_account`.
- Do **not** apply gated Terraform or Agent Runtime `min_instances` without reviewing spend.

## Next (owner)

1. Grant Cloud Run / Artifact Registry / Cloud Build / IAM bindings listed in `docs/DEPLOY.md`.
2. `./scripts/load-bq.sh` then `./scripts/deploy-gcp.sh`.
3. Apply cheap Terraform with `TF_VAR_create_runtime_sa=true` and `TF_VAR_grant_project_iam=true` if you want a dedicated runtime SA.
4. Review `infra/terraform/gated` plan only.
5. Workspace consent for a real Coordination-Agent mailbox (not required for the synthetic loop).
