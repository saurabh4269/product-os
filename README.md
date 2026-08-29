# LOOP

Autonomous product reliability and growth loop for **Northstar Pay**. Spec: [`docs/PRD.md`](docs/PRD.md). Plan: [`docs/PLAN.md`](docs/PLAN.md). Status: [`docs/STATUS.md`](docs/STATUS.md).

One complete loop on synthetic SaaS data:

```
signal → investigation → evidence → root-cause (≥3 sources)
  → HIGH approval → action → measured verification → lesson
```

## One command (clean clone)

```bash
./scripts/boot.sh
```

That generates the warehouse, runs unprompted detection, opens the Safari investigation through the HIGH-tier gate, starts the API on `:8080` and the console on `:3000`.

**Hosted (GCP `us-central1`):** [https://loop-5uy6fkd7bq-uc.a.run.app](https://loop-5uy6fkd7bq-uc.a.run.app) — API and console on one Cloud Run origin. Redeploy with `./scripts/package-host.sh && ./scripts/deploy-gcp.sh`.

```bash
./scripts/verify.sh   # lint, typecheck, tests, console build, Remotion render
```

## What you should see

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Pulse lists a **Safari** purchase-conversion drop (not only an aggregate). Open the investigation: evidence graph with analytics, logs, and deploy timeline; HIGH-tier rollback waiting on you. Approve once. Outcome ledger shows `RESOLVED` and a lesson about Safari 3DS after SDK upgrades.

Governance shows `failOpen=false`. Injected GitHub issue text is blocked by the `after_tool_callback` plugin and logged — it is **data**, not instructions.

## Stack

| Layer | Implementation |
|---|---|
| Agents | Google ADK ≥ 2.8.0, Python, 19 `LlmAgent`s, 7 Apps, `ResumabilityConfig(is_resumable=True)` |
| Default model | `gemini-3.5-flash` in `config/models.yaml` only (P-6 / P-6a) |
| Engine | Deterministic, resumable SQLite control plane — CI does not need Gemini |
| Safety | `ToolOutputArmorPlugin` on `after_tool_callback` (M-10); hard limits in tool code (L-4) |
| Console | Next.js + Tailwind, dark OLED |
| Demo | Remotion `apps/demo` |
| Cheap GCP | BigQuery, Pub/Sub, SA, Model Armor templates, budget — `infra/terraform/cheap` |
| Gated GCP | Agent Gateway / SGP / telephony — `infra/terraform/gated` **plan only** |

## GCP

Project `mystical-timing-442601-q8`, region `us-central1`.

Runtime secret `GCP_SA_KEY` is base64 SA JSON. `.cursor/environment.json` installs the Cloud SDK in `install` and activates the SA in `start` (never echoed or committed).

```bash
./scripts/gcp-activate.sh
cd infra/terraform/cheap && terraform init && terraform apply
./scripts/load-bq.sh          # synthetic warehouse → loop_raw (after ADC)
./scripts/deploy-gcp.sh       # Cloud Run API (needs owner IAM — see docs/DEPLOY.md)
```

Cheap resources already applied in this project: BigQuery datasets, Pub/Sub topics, Model Armor templates. Cloud Run source deploy is blocked until you grant Artifact Registry + Cloud Build + Cloud Run Admin to `loop-cloud-agent@…` — exact commands in [`docs/DEPLOY.md`](docs/DEPLOY.md).

Agent Gateway / SGP / telephony:

```bash
cd infra/terraform/gated && terraform init && terraform plan -out=gated.tfplan
# Review fail_open = false, then: terraform apply gated.tfplan
```

Exact apply notes: [`infra/terraform/gated/README.md`](infra/terraform/gated/README.md).

## Tests that invert defaults

- Seeded Safari regression is detected **without a prompt**
- Three restatements of one GA4 query **cannot** pass the root-cause gate
- HIGH-tier action stays blocked across process restart and executes **once**
- Tool-output injection is blocked and logged
- Terraform CI fails if Model Armor `failOpen` is true or missing
- Sampling params are not attached to `gemini-3.6-flash` / `gemini-3.5-flash-lite`
