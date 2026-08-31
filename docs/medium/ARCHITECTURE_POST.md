# Product OS (LOOP): Building an Autonomous Product Workforce with ADK 2, BigQuery, and Governed Multi-Agent Orchestration

| Field | Value |
|---|---|
| Format | Medium architecture story |
| Status | Draft — ready to paste into Medium |
| Live demo | https://loop-5uy6fkd7bq-uc.a.run.app |
| Repo | https://github.com/saurabh4269/product-os |

**Subtitle:** How we built a generic control plane that observes any product, investigates with evidence, gates risky changes, and remembers — powered by Google Cloud, Gemini, and ADK 2.8.

---

## The problem: product teams learn too slowly

Every SaaS team hits the same wall. Conversion drops on Safari. Checkout abandons spike. A payment SDK upgrade ships on Tuesday; support notices on Thursday; engineering finds the root cause next week. Dashboards show *that* something broke. They rarely show *why* — and nobody measures whether the fix actually worked.

Traditional incident response is a chain of handoffs: support → PM → on-call → ticket → PR → merge → “someone should check analytics.” Context dies at each step. Three weeks later, the org has a merged PR and a Slack thread, not verified impact.

We built **Product OS (LOOP)** to close that loop:

```
Observe → Investigate → Diagnose → Decide → Act → Approve → Ship → Verify → Learn
```

It is **not** a Safari app or a payments demo. Those are **fixtures** that exercise one pipeline — the same engine handles conversion regressions, crash spikes, feature opportunities, and security exfil attempts (DENIED).

---

## The solution: a campus, rooms, and a governed agent fleet

LOOP is a **control plane** with a human-legible surface:

- A **campus map** — landmarks for Memory, Approvals, Connect
- **Multi-room chat** — Grok / OpenClaw energy: pixel agents, visible handoffs, per-bot threads
- **Connect desk** — wire Product Y (our demo tenant **Cove**) with flags, ingest, GitHub PR on approve

Behind the UI: **23 ADK `LlmAgent`s** in **7 trust-boundary `App`s**, a resumable investigation workflow, and a deterministic engine on Cloud Run so cold starts never depend on Gemini quota.

---

## 100% Google Cloud native stack

| Layer | Google service | Role |
|---|---|---|
| Brain | **Gemini 3.5 Flash** (config in `models.yaml` only) | Agent reasoning when ADK worker runs |
| Framework | **ADK 2.8+** — `LlmAgent`, `App`, `Workflow`, `JoinNode` | Fleet + orchestration |
| Safety | **Model Armor** + custom **ToolOutputArmorPlugin** | Screen prompts, responses, *and* untrusted tool payloads |
| Compute | **Cloud Run** (`loop`, optional `loop-adk`, tenant `cove`) | Serverless, min-instances for demo reliability |
| Warehouse | **BigQuery** — `loop_raw`, `loop_metrics`, GA4 `analytics_*`, optional `loop_ads` | Detect, evidence, verification |
| Analytics | **GA4** → BQ export (daily + **streaming intraday**) | Real tenant signals, not just synthetic data |
| Messaging | **Pub/Sub** `loop.signals` | Push ingest from Product Y |
| Jobs | **Cloud Tasks** + SQLite ↔ GCS | Background code-fix, worker ticks |
| Workspace | **Gmail draft / Calendar hold** via OAuth | Human coordination, send intentionally denied |

---

## Nineteen agents, one pipeline, two signal types

**Type A — something broke (BUG):** Safari 3DS conversion regression, Android SDK crash spike, security exfil attempt (DENIED).

**Type B — something could be better (FEATURE):** Apple Pay opportunity, shipping UX friction.

Every signal runs the same graph:

```
Signal Agent (detect only — never investigates)
    → Investigation fan-out (Analytics · Logs · Deploy · DB · Voice · Code)
    → JoinNode → Evidence → Root Cause (≥3 independent sources)
    → BUG vs OPPORTUNITY → Risk tier → HITL approval → action → verify → learn
```

We use **ADK 2 `Workflow` graphs** — not the deprecated ADK 1.x sequential/parallel agent classes — with a deterministic hosted path for reliability.

---

## Technical implementation: ADK 2 multi-agent excellence

### Clean orchestration (Workflow, not deprecated agents)

```python
from google.adk import Workflow
from google.adk.workflow import START, JoinNode

# Fan-out investigators → barrier at Evidence Agent
# Workflow-as-Tool on LlmAgent requires explicit Pydantic input_schema
```

### ADK core concepts we use

- **Workflow + JoinNode** — parallel investigation with a deterministic merge point
- **App + resumability** — production shape for GEAP Agent Runtime when entitled
- **ModelArmorPlugin** — first-party prompt/response screening
- **ToolOutputArmorPlugin** — companion plugin; stock Model Armor does not screen tool output (Requirement M-10)
- **RequestInput** — human approval gates instead of ad-hoc pause hacks

### Hosted vs ADK worker (hybrid by design)

**Cloud Run `loop`** runs the **deterministic Loop Engine** — same state machine the agents drive via tools. CI and cold starts never need Gemini quota.

**Optional `loop-adk` worker** runs the full ADK fleet when `LOOP_ADK_WORKER_URL` is set. Same console, same store schema.

---

## Multi-agent patterns we productionized

Typical ADK demos show parallel research, sequential QA loops, agent callbacks to the UI, skip-if-done HITL, and BigQuery-backed analytics. We integrated those patterns into a **generic product loop** and added governance ADK tutorials rarely cover:

| Demo pattern | Product OS |
|---|---|
| Domain-specific automation | **Generic** loop; any tenant, any fixture |
| Many Cloud Run services | One control plane + optional ADK worker |
| Autonomous Gmail send | **Draft only**; `send_gmail` denied |
| ADK 1.x agent trees | **ADK 2.8 Workflow** + trust-boundary `App`s |
| CRUD dashboard | **Campus + rooms + approvals tram** |

---

## Production-grade choices hackathon demos skip

1. **`fail_open = false`** — we pin Model Armor Terraform against Google's own fail-open examples.
2. **Tool-output armor** — GitHub issues and ingested mail are injection vectors; stock `ModelArmorPlugin` does not screen `function_response` parts.
3. **Identity before prompt** — customer-record exfil is DENY via Gateway/registry identity.
4. **No merge, no tenant deploy** — LOOP opens PRs on Cove's repo; humans merge and CI deploys Product Y.
5. **Hybrid engine** — CI and hosted demo run without Vertex; same tools when credentials exist.
6. **Tenant split** — no `/shop` on the OS origin; Cove lives in its own repo and Cloud Run service.

---

## The Product OS multi-agent workflow

```
                    ┌─────────────────┐
  Product Y (Cove)  │  Signal ingest  │
        │           └────────┬────────┘
        │                    ▼
        │           ┌─────────────────┐
        └──────────►│  Product OS     │
                    │  (LOOP)         │
                    │  campus + rooms │
                    └────────┬────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   BigQuery warehouse   Gmail draft        GitHub PR
   GA4 + loop_raw       Calendar hold      (no merge)
```

Six fixtures, one pipeline. Safari is a recipe, not the architecture.

---

## Installation and testing

### Hosted project URL

- **Product OS:** https://loop-5uy6fkd7bq-uc.a.run.app
- **Demo tenant (Cove):** https://cove-5uy6fkd7bq-uc.a.run.app

**Try it:** Campus → Safari 3DS room → evidence chain → Approvals tram → Approve → GitHub PR on Cove (vitest-gated, no auto-merge).

### Public code repository

```bash
git clone https://github.com/saurabh4269/product-os
cd product-os
./scripts/boot.sh      # warehouse + seed + API :8080 + console :3000
./scripts/verify.sh    # ruff, pytest, console build
```

### Ship to Cloud Run

```bash
unset NEXT_PUBLIC_API_URL LOOP_STATIC
./scripts/package-host.sh
./scripts/deploy-gcp.sh
```

Requirements met:

- Functional as depicted — demo features work on hosted Cloud Run
- ADK 2.8 framework — full fleet in repo; deterministic path on hosted service
- Multi-agent focus — 23 agents, 7 trust boundaries, Workflow catalog
- Google Cloud integration — Cloud Run, BigQuery, GA4, Pub/Sub, Model Armor, Gemini
- English language support — full UI and documentation in English

---

## Open source contribution ready

We documented upstream gaps and suggested fixes for Google repos in [`docs/GOOGLE_OPEN_SOURCE_LEARNINGS.md`](https://github.com/saurabh4269/product-os/blob/main/docs/GOOGLE_OPEN_SOURCE_LEARNINGS.md):

- Tool-output Model Armor sample (M-10)
- ADK 1.x → 2.x migration guide (ParallelAgent → Workflow)
- GA4 Admin API version notes (`v1alpha` for BigQuery links)
- Hosted OAuth redirect pattern for production Cloud Run

---

## Conclusion

Multi-agent orchestration on Google Cloud can automate complex business workflows. Product OS applies that shape to **product reliability and growth**: observe any product, investigate with evidence, gate risky changes, verify outcomes, and remember lessons.

ADK 2 `Workflow` + BigQuery warehouse + a chat-native control plane is the architecture. The fixtures change; the pipeline does not.

The future of product ops is multi-agent, ADK-powered, and governable — available today on cheap GCP.

---

**Tags:** `#GoogleADK` `#ADK2` `#GoogleCloud` `#BigQuery` `#GA4` `#MultiAgent` `#ProductEngineering` `#CloudRun` `#ModelArmor` `#Gemini` `#AgentDevelopmentKit`

**Related:** [Hands-on tutorial draft](TUTORIAL_POST.md) · [Adoption notes](ADOPTION_NOTES.md)
