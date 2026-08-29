# LOOP — Implementation Plan

| Field | Value |
|---|---|
| Status | Binding plan for this build |
| Spec | `docs/PRD.md` v1.1 (verified 2026-08-29) |
| Region | `us-central1` (Requirement P-1) |
| Default model | `gemini-3.5-flash` (Requirement P-6a) |
| ADK pin | `google-adk>=2.8.0` (Requirement M-6) |
| GCP project | `mystical-timing-442601-q8` |

This plan is the architecture the code implements. MUST requirements in the PRD remain binding, especially Section 14 (safety) and Section 18 (limits). Where a platform primitive is expensive, Preview-only, or requires human entitlements, this plan names a **real local/control-plane implementation** plus an **exact operator path** — it does not fake the primitive.

---

## 1. Scope of this build

One complete, auditable loop on synthetic SaaS data:

```
signal → investigation → evidence → root-cause (≥3 independent sources)
  → risk tier → human approval → action → measured verification → lesson
```

All 19 agents exist as real ADK `LlmAgent`s with typed tool interfaces. The **investigation core** is a deterministic, resumable workflow so the seeded Safari conversion regression is detected unprompted in CI without a live Gemini call. When Vertex credentials are present, the same tools are available to the ADK agents.

### 1.1 What “done” means

| Gate | How we prove it |
|---|---|
| Seeded regression detected unprompted | Signal Agent scans warehouse; Safari/iOS purchase drop opens an investigation without a human hint |
| Three-source independence gate | Root Cause Agent refuses a hypothesis unless analytics + logs + deploy timeline are distinct independence groups |
| Tool-output injection caught | `after_tool_callback` plugin blocks the poisoned GitHub issue / injected tool payload; verdict is logged |
| HIGH-tier approval survives restart | Payment-surface action stays `PENDING`; process restart; one approval resumes exactly once (idempotency key) |
| Remotion renders | `npm run render` produces an mp4 of the real loop, no lorem |
| One-command boot | `./scripts/boot.sh` from a clean clone |
| Cheap GCP applied | BigQuery, Pub/Sub, Cloud Run, service account, Model Armor templates, budget alert |
| Gated GCP plan-only | Agent Gateway, SGP, telephony — `terraform plan` + exact apply commands for the owner |

---

## 2. Architecture

### 2.1 Planes (PRD §7)

```
SIGNAL          synthetic warehouse (local Parquet/JSON + optional BigQuery)
                  │  Pub/Sub topic loop.signals (or in-process bus)
AGENT           7 ADK Apps / trust boundaries, plugins on App
GOVERNANCE      identity matrix + deterministic tool gates + Model Armor
                  + tool-output plugin (M-10) + failOpen=false Terraform (M-5a)
TOOL            warehouse, logs, deploys, GitHub fixture, flags, memory, media-bridge
MEMORY          SQLite control plane + Memory Bank adapter + local SKILL.md playbooks
CONSOLE         Next.js trust product
```

ADK decides *what*. Deterministic tool code decides *whether*. The UI makes the chain legible.

### 2.2 Trust boundaries (PRD §7.2)

| TB | Deployment | Agents | Envelope (enforced in tool code + IAM docs) |
|---|---|---|---|
| TB-1 | `loop-orchestration` | Orchestrator, Evidence, Root Cause, Feedback, Risk, Decision | No external tools |
| TB-2 | `loop-analysis` | Signal, Analytics, Logs, Deployment, Database | Read-only warehouse/logs/deploys. No PII columns |
| TB-3 | `loop-customer` | Consent, Customer Voice | Media-bridge + SDP redaction. No code, no analytics write |
| TB-4 | `loop-code` | Code, Test | Sandbox + GitHub write fixtures. Denied customer data |
| TB-5 | `loop-product` | Product, Coordination | Issues + templated comms. No merge, no prod |
| TB-6 | `loop-experiment` | Experiment | Flag control + metric read. No code write |
| TB-7 | `loop-learning` | Learning | Memory write + warehouse read |

Cross-TB calls go through an in-process A2A bus that records the same audit fields a gateway hop would. Production Agent Gateway is Terraform **plan-only** (immutable `identity_type` + `agent_gateway_config` at creation — A-1).

### 2.3 Execution topology

1. **Signal Agent** (ambient, ≤10 min): detect, classify, suppress, persist Investigation, emit `invocation_id`, return. Never investigates (A-4).
2. **Investigation workflow** (resumable, checkpointed): Orchestrator fans out Analytics / Logs / Deployment (and optionally Database / Voice). Join at Evidence Agent → Root Cause (≥3 independence groups or no hypothesis) → BUG vs OPPORTUNITY → Code/Product path → Risk → HITL → action → verification window → Learning.
3. State lives in SQLite (and BigQuery ops tables when GCP is live). Never only in process memory (A-6).

### 2.4 Why a hybrid engine + ADK agents

ADK 2.8 `App(resumability_config=ResumabilityConfig(is_resumable=True))` is the production shape. CI and the one-command demo cannot depend on Gemini quota, Live API, or Agent Runtime. The **Loop Engine** is the same state machine the agents drive via tools:

- Tools are the source of truth (L-4, A-7).
- Agents are real `LlmAgent`s with those tools attached.
- Tests call the engine and the plugin surface directly.
- When `GOOGLE_CLOUD_PROJECT` + ADC exist, `adk` / Vertex can run the same agents.

---

## 3. File tree

```
.
├── README.md
├── docs/
│   ├── PRD.md
│   ├── PLAN.md
│   └── STATUS.md
├── .cursor/environment.json          # gcloud in install; SA activate in start
├── scripts/
│   ├── boot.sh                       # one command: seed + api + console
│   ├── gcp-activate.sh               # decode GCP_SA_KEY, never echo
│   ├── verify.sh                     # build, typecheck, lint, tests, remotion
│   └── render-demo.sh
├── config/
│   └── models.yaml                   # P-6: model IDs only here
├── data/
│   ├── generate.py                   # seeded SaaS warehouse
│   └── fixtures/
│       ├── prompt_injection_tool.json
│       ├── poisoned_github_issue.md
│       └── pii_transcript.json
├── services/loop/                    # Python control plane + ADK
│   ├── pyproject.toml
│   ├── loop/
│   │   ├── config.py
│   │   ├── models.py                 # PRD §23 entities
│   │   ├── store.py                  # SQLite + idempotency
│   │   ├── engine.py                 # resumable investigation
│   │   ├── warehouse.py
│   │   ├── memory.py
│   │   ├── a2a.py
│   │   ├── api.py                    # FastAPI for console
│   │   ├── plugins/
│   │   │   ├── tool_output_armor.py  # M-10 after_tool_callback
│   │   │   ├── risk_gate.py          # before_tool + L-4
│   │   │   └── taint.py              # M-13
│   │   ├── tools/                    # FunctionTools + hard limits
│   │   ├── agents/                   # 19 LlmAgents + 7 Apps
│   │   └── media_bridge/             # mock Live API + transcript screen
│   └── tests/
├── apps/console/                     # Next.js + shadcn + Tailwind
├── apps/demo/                        # Remotion
├── infra/terraform/
│   ├── cheap/                        # BQ, Pub/Sub, SA, Armor, budget, Run
│   └── gated/                        # Gateway / SGP / telephony plan-only
└── .github/workflows/ci.yml
```

---

## 4. Data model (PRD §23)

Persisted in SQLite (`var/loop.db`) and mirrored to BigQuery `loop_ops` when applied.

| Entity | Required fields (minimum) |
|---|---|
| Signal | id, family, direction, funnel_position, metric, magnitude, baseline, segments, window, confidence, source, status, suppression_reason |
| Investigation | id, signal_ids, state, opened/closed, invocation_id, agents, budget, hypothesis_ids, action_ids, verification |
| Evidence | id, investigation_id, source_type, source_ref, claim, confidence, trust (trusted/untrusted), agent, collected_at, weight, independence_group |
| Hypothesis | id, investigation_id, statement, classification, confidence, support_ids, contradict_ids, cited_memory, rank |
| CustomerContact | id, investigation_id, tokenized_user, consent, channel, attempted_at, connected, duration, structured_evidence, transcript_artifact, freq_cap |
| ProposedAction | id, investigation_id, type, risk_tier, rationale, approver_role, artifacts, idempotency_key |
| Approval | id, action_id, approver, decision, rationale, timestamp, tier |
| Experiment | id, hypothesis_id, primary_metric, mde, guardrails, cohort, rollout, stopping, status, result |
| Outcome | id, investigation_id, metric, pre, post, control, delta, verdict, measured_at |
| Lesson | id, investigation_id, statement, family, conditions, playbook, confidence, author, reviewer |
| PolicyVerdict | id, agent_identity, tool, args_digest, verdict, rationale, mode, tokens, timestamp |

**T-1.** Independence group is mandatory. Three restatements of one GA4 query do not pass the gate.

**T-2.** Customer keys are `tok_*` surrogates, never raw emails/phones.

Investigation states: `OPEN → GATHERING → HYPOTHESIS → ACTION_PROPOSED → AWAITING_APPROVAL → APPROVED → ACTING → VERIFYING → {RESOLVED, PARTIALLY_RESOLVED, NOT_RESOLVED, INCONCLUSIVE}`. HIGH-tier cannot skip `AWAITING_APPROVAL`. Terminal requires a Learning verdict (F-1).

---

## 5. Seeded world

Synthetic tenant: **Northstar Pay** — a B2B SaaS checkout.

| Stream | Shape | Seeded defect |
|---|---|---|
| GA4 `events_YYYYMMDD` | page_view, view_item, begin_checkout, add_payment_info, purchase | From 2026-08-20, Safari/iOS purchase CR drops ~25% vs 14-day baseline; aggregate drop ~3% |
| Ads | `ads_CampaignStats` views with `_DATA_DATE` on both join sides (J-9) | Spend stable — not the cause |
| Logs | 3DS timeout / `PaymentSDK` errors spike on Safari WebKit after deploy |
| Deploys | `pay-sdk@4.3.0` shipped 2026-08-20 09:14Z |
| Transcripts | Diagnostic call; one fixture contains PII (phone, email) |
| GitHub | Issue body contains a prompt-injection payload (untrusted DATA) |
| Tool fixture | `read_github_issue` returns injection text |

Detection is baseline-relative with day-of-week awareness (G-1) and **segment-mandatory** (G-3). The Signal Agent must fire a Safari signal, not only an aggregate one.

Adversarial fixtures are **untrusted DATA**, never instructions (M-13). They are tagged `trust=untrusted` at ingest and must not be interpolated into system prompts.

---

## 6. Safety (Section 14) — non-negotiable implementation

| ID | Implementation |
|---|---|
| **M-5a** | Terraform `google_network_services_lb_traffic_extension` / AuthzExtension sets `fail_open = false` (or `failOpen = false` in YAML). CI `test_failopen_false.py` greps cheap+gated Terraform and **fails if any `failOpen`/`fail_open` is true or missing** on Model Armor CONTENT_AUTHZ extensions |
| **M-10** | `ToolOutputArmorPlugin.after_tool_callback` screens tool results (injection patterns + optional Model Armor sanitize). First-party `ModelArmorPlugin` is also registered and does **not** replace this |
| **M-7** | `block_on_screening_failure=True` left at default |
| **L-4** | Numeric ceilings, HIGH-tier blocks, contact frequency caps, and “no send mail” live in tool Python, not the LLM judge |
| **A-7** | Every side-effecting tool takes `idempotency_key` derived from `(investigation_id, node_id, semantic_key)` |
| **P-6 / P-6a / P-6b** | Model IDs only in `config/models.yaml`. Default `gemini-3.5-flash`. CI asserts sampling params are unset for `gemini-3.6-flash` and `gemini-3.5-flash-lite` |
| Voice | Mock Live API. Media-bridge interface + transcript screening only (K-11). No real PSTN |

SGP / Agent Gateway are **defense in depth**, Preview, and cost-bearing. They ship as gated Terraform (plan-only) plus documented `gcloud`/`terraform apply` commands. Hard limits still hold if they never apply (Q-4).

---

## 7. Real vs stubbed

| Component | This build |
|---|---|
| Signal detection + suppression | **Real** on synthetic warehouse |
| Investigation engine, evidence graph, 3-source gate | **Real** |
| Risk tier + durable HITL | **Real** |
| Idempotent actions (flag, PR record, memory write) | **Real** (local + optional GitHub dry-run) |
| Learning / outcome / lesson | **Real** (verification window compressed for demo) |
| ADK agents + FunctionTools | **Real** interfaces; LLM optional |
| Model Armor templates | **Real Terraform**; local plugin has deterministic fallback if API disabled |
| BigQuery / Pub/Sub / Cloud Run / budget | **Real cheap apply** when ADC works |
| Agent Identity + Gateway + SGP | **Terraform plan-only** + operator commands |
| Live API / Twilio / PSTN | **Mock** media-bridge; interface complete |
| Workspace MCP OAuth | **Interface + consent stub**; no live mailbox |
| Agent Runtime (`reasoningEngines`) | **Not applied** (min_instances cost). Source layout ready |
| Memory Bank / Skill Registry cloud | **Local adapters**; cloud wiring documented |

---

## 8. Console (PRD §22)

Dark-first OLED ops product (ui-ux-pro-max: Dark Mode OLED, Fira Sans + Fira Code, density 7). Surfaces:

1. **Investigation** — timeline, current action, confidence, next human move
2. **Evidence graph** — nodes + support/contradict edges, provenance on click
3. **Agent timeline** — who ran, A2A hops, denials visible (S-4)
4. **Approval queue** — full decision context; one-click approve/deny
5. **Outcome ledger** — verdicts, deltas, idea-to-impact
6. Signal feed, opportunity board, governance (inventory + verdicts + Armor findings)

All agent text is escaped (S-5). Empty / loading / error states are first-class. An on-call engineer can judge one investigation in seconds (S-6).

---

## 9. Demo

Remotion composition walks the **real** seeded investigation (API or exported JSON): signal fire → three evidence sources → gated hypothesis → HIGH approval → action → verification → lesson. No lorem ipsum.

---

## 10. GCP (cheap only)

Project `mystical-timing-442601-q8`, region `us-central1`.

**Apply:** enable cheap APIs; BigQuery datasets `loop_raw`, `loop_metrics`, `loop_ops`; Pub/Sub `loop.signals`, `loop.verification`; runtime SA; Model Armor input/output templates + floor settings; billing budget alert (few USD); optional Cloud Run for API+console if image build stays cheap.

**Plan-only + commands in README:** Agent Gateway, SGP policy engine, telephony, Agent Runtime deployments (`identity_type=AGENT_IDENTITY`, `agent_gateway_config` at create).

**Never:** echo/log/commit `GCP_SA_KEY` or decoded JSON. `.cursor/environment.json` installs gcloud idempotently; `start` decodes the secret and activates the SA (exported env does not survive Builds).

---

## 11. Milestones (mapped to PRD §24, shipped together)

| M | Deliverable |
|---|---|
| M0 | Plan, config, environment.json, boot script |
| M1 | Synthetic warehouse + fixtures + detection |
| M2 | Engine + store + idempotency + 3-source gate + HITL |
| M3 | ADK apps, plugins (M-10), 19 agents, media-bridge mock |
| M4 | FastAPI + Next.js console |
| M5 | Tests + CI failOpen/P-6b assertions |
| M6 | Remotion |
| M7 | Terraform cheap apply + gated plan + STATUS |

---

## 12. Verification commands

```bash
./scripts/boot.sh          # seed, API :8080, console :3000
./scripts/verify.sh        # lint, typecheck, unit, e2e loop, remotion
```

E2E assertions live in `services/loop/tests/test_e2e_loop.py` and `test_safety.py`.
