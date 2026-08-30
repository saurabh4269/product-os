# Product OS (LOOP)

An autonomous product team that observes the product, understands users, identifies **problems or opportunities**, coordinates the right agents and people, ships with gated approval, measures impact, writes the lesson, and repeats.

> I observed the product, investigated, talked to customers, coordinated agents, changed the software, got the right approval, and verified the outcome.

**Safari / 3DS / payments are scenario fixtures — not the product.** The home experience is rooms + heterogeneous live signals. The same pipeline runs Type A (something broke → fix) and Type B (something could be better → improve). After root cause the graph forks: **BUG** (code + test + PR) vs **FEATURE** (proposal + impact + human approval).

**New agent?** Start on **`main`**. Read [`AGENTS.md`](AGENTS.md), then [`docs/PLAN_NEXT.md`](docs/PLAN_NEXT.md). Pitfalls: [`docs/LEARNINGS.md`](docs/LEARNINGS.md) · [`docs/RESEARCH_LEARNINGS.md`](docs/RESEARCH_LEARNINGS.md). Tenant product (separate repo): [`docs/TENANT.md`](docs/TENANT.md).

Spec: [`docs/PRD.md`](docs/PRD.md). Architecture: [`docs/architecture.mmd`](docs/architecture.mmd) · [`docs/architecture.svg`](docs/architecture.svg).

## One command

```bash
./scripts/boot.sh
```

API `:8080`, console `:3000`. On boot the warehouse is generated and `seed_world` opens six fixtures into rooms.

**Hosted:** https://loop-5uy6fkd7bq-uc.a.run.app · Product Y: https://northstar-5uy6fkd7bq-uc.a.run.app

```bash
./scripts/verify.sh
unset NEXT_PUBLIC_API_URL && ./scripts/package-host.sh && ./scripts/deploy-gcp.sh
```

Do not bake `NEXT_PUBLIC_API_URL=http://127.0.0.1:8080` into the Cloud Run bundle.

## What a reviewer should see

1. Multi-room chat: incidents, opportunities, reviews, research, ops. Pixel agents working in each room.
2. Heterogeneous signals (conversion, activation, feature requests, policy) — not a single Safari happy path.
3. Type A loops complete (Safari 3DS **and** Android SDK **and** onboarding activation).
4. Type B loops complete (Apple Pay proposal, shipping-date experiment).
5. Risk Agent / Gateway blocks “dump production customer records” via **identity**, not a prompt.
6. Memory Bank recalls a prior SDK-callback lesson when the Android signal arrives.
7. Architecture diagram matches the running five-plane system.

## Scenario pack (fixtures / evals)

Same generic pipeline for all of these:

| ID | Loop | Path | Room |
|---|---|---|---|
| `safari_3ds` | A | BUG | Incident — warehouse-detected Safari conversion break |
| `android_sdk` | A | BUG | Incident — Android −18% after pay-sdk 3.8 + Calendar/Gmail draft |
| `onboarding_activation` | A | BUG | Incident — **non-checkout** activation drop after copy |
| `apple_pay` | B | FEATURE | Opportunity — 37 customers, PRD, PM gate, GitHub issue |
| `shipping_ux` | B | FEATURE | Opportunity — 12% return-to-shipping, 5% experiment |
| `security_exfil` | A | SECURITY | Reviews — production customer-record dump **DENIED** |

Customer Voice always receives context (user, attempt, device, failure, history) and emits structured JSON (`reason`, `severity`, `purchase_intent`, `friction`, `competitor_mentioned`, `feature_request`, `willing_to_retry`, `confidence`).

In-repo fixture files the Code Agent patches today: [`apps/northstar-shop`](apps/northstar-shop). The tenant product is a separate repo and deployment — not hosted on this origin.

## Five planes

1. **Signal** — Ads, GA4, PostHog, Firebase, logs, CRM → BigQuery **facts** (e.g. “conversion was 81.7%”).
2. **Agent** — ADK 2 specialists, A2A, Type A / Type B fork. Incident Commander discovers the Registry; it does not own every capability.
3. **Security** — distinct identity per agent, Gateway allow/deny, Model Armor, SDP, Secret Manager.
4. **Tool** — GitHub, BigQuery, Calendar, Gmail draft, flags, voice media-bridge. Workspace MCP inherits user permissions when present.
5. **Memory / control** — Runtime, sessions, Memory Bank (customer / product / engineering / organizational), Registry, OpenTelemetry-shaped traces.

Analytics Agent: ALLOW GA4/BigQuery/PostHog read, DENY Gmail send / GitHub write / prod deploy.

Engineering (`loop-code`): ALLOW GitHub r/w + CI, DENY Gmail send / prod deploy / **customer data**. That is the answer to “what stops engineering from reading customer data?”

## Honest Google-product mapping (2026)

| Named product | In this repo |
|---|---|
| ADK 2 `LlmAgent` / Apps / plugins | Real locally (`google-adk>=2.8.0`, 23 agents, 7 Apps). Hosted control plane is the deterministic engine so CI/Cloud Run do not need Gemini. |
| Gemini 3.5+ | `config/models.yaml` default `gemini-3.5-flash`. Sampling never set on 3.6 / 3.5-lite. |
| A2A | Structured `AgentCall` records + Registry discovery. Not a mega-prompt. |
| Agent Registry / Identity / Gateway | `loop/registry.py` + IAM-shaped allow/deny in tool code. Agent Gateway / SGP Terraform is **plan-only** (`infra/terraform/gated`). |
| Memory Bank | Firestore-shaped SQLite `memory` table, four kinds, lesson recall. |
| Model Armor | Cheap GCP templates applied; `ToolOutputArmorPlugin` on `after_tool_callback` (ADK does not screen tool output). `fail_open = false`. |
| Gemini Live / Telephony | Media-bridge + transcript screening. No PSTN. |
| Agent Observability | Local A2A traces; Cloud Trace when the project has it. |
| Antigravity SDK | Code Agent contract + GitHub PR artifacts. Fixture targets are in-repo; production targets a connected tenant repo. |

## Stack

| Layer | Implementation |
|---|---|
| UI | Next.js 15, IBM Plex, multi-room chat, CSS pixel agents |
| Engine | Deterministic Python, SQLite, resumable |
| Agents | Google ADK 2, structured A2A |
| Cheap GCP | BigQuery, Pub/Sub, Cloud Run, Model Armor, SA — `infra/terraform/cheap` |
| Gated GCP | Agent Gateway / SGP / telephony — **plan only** |
| Demo | Remotion `apps/demo` |

Project `mystical-timing-442601-q8`, region `us-central1`. Runtime secret `GCP_SA_KEY` is base64 SA JSON. Never echo or commit it.

```bash
./scripts/gcp-activate.sh
cd infra/terraform/cheap && terraform init && terraform apply
./scripts/load-bq.sh
```

## Tests that invert defaults

- Seeded Safari regression is detected **without a prompt**; Chrome does not fire
- Six fixtures seed through **one** pipeline; Type A vs Type B routing
- Non-checkout onboarding scenario exists
- Security exfil is **DENY** via Gateway identity
- Memory Bank recalls the SDK-callback lesson on the later Android signal
- Three restatements of one GA4 query cannot pass the root-cause gate
- HIGH-tier action stays blocked across process restart and executes **once**
- Tool-output injection is blocked and logged
- Terraform CI fails if Model Armor `failOpen` is true
