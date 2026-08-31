# Google open-source learnings — contribution handoff

| Field | Value |
|---|---|
| Purpose | Hand to a Cursor agent to file issues/PRs on Google repos |
| Session | Product OS (LOOP) + Cove tenant — Aug 30–31, 2026 |
| Verified | **2026-08-31 pass 3** — see [`upstream/DRAFTS.md`](upstream/DRAFTS.md) verification table |
| Drafts | **Ready-to-paste issues/PRs:** [`upstream/DRAFTS.md`](upstream/DRAFTS.md) |
| Binding plans | [`PLAN.md`](PLAN.md) · [`PLAN_NEXT.md`](PLAN_NEXT.md) · [`PLAN_PRODUCTION.md`](PLAN_PRODUCTION.md) |
| Our workarounds | [`LEARNINGS.md`](LEARNINGS.md) · [`RESEARCH_LEARNINGS.md`](RESEARCH_LEARNINGS.md) · [`HACKATHON_STORY.md`](HACKATHON_STORY.md) |

This document summarizes what we built in the session, which Google open-source projects we relied on, concrete bugs/gaps we hit, and suggested upstream fixes. It is written for an agent that will open GitHub issues or PRs — not for end-user docs.

**Product OS upstream status:** [product-os PRs #1–#8](https://github.com/saurabh4269/product-os/pulls?q=is%3Apr) merged. **No Google upstream issues/PRs filed yet** from this work.

---

## 1. Session recap (what we shipped)

### Product OS control plane

- **Tenant split:** Cove (Product Y) on its own repo + Cloud Run; no `/shop` on `loop`.
- **Connect desk:** tenant record, flags, ingest, GitHub PR on HIGH approve (never merge/deploy Y).
- **Workspace OAuth:** Web client + hosted callback; Gmail draft / Calendar hold; `send_gmail` denied ([`services/loop/loop/connectors/google_oauth.py`](../services/loop/loop/connectors/google_oauth.py)).
- **GA4 OAuth (separate flow):** `/api/oauth/ga4/start` with `analytics.edit` scope; ADC saved to GCS as `ga4_adc.json`.
- **BigQuery warehouse:** `loop_raw`, `loop_metrics`, synthetic load + tenant `warehouse_mode: auto`.
- **GA4 → BQ:** property `552119204`, measurement `G-795LDMSV20`, dataset `analytics_552119204`, streaming export enabled.
- **Google Ads → BQ:** demo `loop_ads` only (user chose not to wire live Ads account); transfer needs browser OAuth.
- **ADK 2 fleet (local/worker):** 23 `LlmAgent`s, 7 `App`s, Workflow catalog, optional `loop-adk` Cloud Run worker ([`docs/ENTERPRISE_TRACK.md`](ENTERPRISE_TRACK.md)).

### Plan alignment

| Plan doc | What the session validated |
|---|---|
| [`PLAN.md`](PLAN.md) §2.4 | **Hybrid engine + ADK agents** — hosted `loop` stays deterministic; ADK runs on worker or local eval only. |
| [`PLAN.md`](PLAN.md) M-6, M-10 | Pin `google-adk>=2.8.0`; first-party `ModelArmorPlugin` **plus** custom `ToolOutputArmorPlugin` on `after_tool_callback`. |
| [`PLAN.md`](PLAN.md) §2.2 | Seven trust-boundary `App`s map cleanly to ADK `App(plugins=[...])`. |
| [`PLAN_NEXT.md`](PLAN_NEXT.md) Phases A–F | Shipped: tenant, flags, ingest, connectors, warehouse path, Connect UI. |
| [`PLAN_NEXT.md`](PLAN_NEXT.md) §4 | Workspace OAuth flow wired; user still creates Web client in Auth Platform once. |
| [`PLAN_PRODUCTION.md`](PLAN_PRODUCTION.md) P0 | GCS state, jobs, Cloud Scheduler worker tick, Model Armor layering — all landed. |

---

## 2. Google repos we used

| Repo | Role in session | Version / ref |
|---|---|---|
| [google/adk-python](https://github.com/google/adk-python) | ADK 2.x runtime: `LlmAgent`, `App`, `Workflow`, `JoinNode`, `ModelArmorPlugin`, OAuth samples | `google-adk>=2.8.0` (latest on PyPI: **2.8.0**, verified 2026-08-31) |
| [google/adk-samples](https://github.com/google/adk-samples) | Referenced in PRD M-6; **`ModelArmorSafetyFilterPlugin` superseded for input/output** — but sample still implements tool-output screening first-party lacks | Not pinned — do not copy sample as production guardrail |
| [google/adk-docs](https://github.com/google/adk-docs) | Published docs site — **separate repo** from adk-python; user-facing doc PRs go here | Model Armor guide **not live** on site yet (see §3.1) |
| Google Analytics Admin API | GA4 property, web stream, BigQuery link automation | `v1beta` (CRUD) + **`v1alpha` (BigQuery links only)** — confirmed via API discovery |
| BigQuery / `bq` CLI | Warehouse load, Google Ads Data Transfer setup | gcloud SDK on Kali |
| Workspace OAuth codelab pattern | User refresh token, not service account (ADK/GEAP docs) | No single canonical repo — pattern from Google codelabs |

---

## 2.1 Upstream contribution rules (verified on GitHub)

Read these before filing. All require the [Google CLA](https://cla.developers.google.com/about).

### `google/adk-python`

| Rule | Detail |
|---|---|
| Issue before PR | Non-trivial PRs need a linked issue **or** full problem/solution in PR body (issue-template shape). |
| Docs split | User-facing docs → PR in **`google/adk-docs`**, not only adk-python. In-repo guide lives under `docs/guides/`. |
| PR landing | Accepted PRs often land via **Copybara** — GitHub shows *closed* + `merged` label + comment with commit hash. Closed ≠ rejected. |
| Testing | `pytest`, `tox` across Python versions, testing plan in PR. |
| Templates | [bug_report](https://github.com/google/adk-python/blob/main/.github/ISSUE_TEMPLATE/bug_report.md) · [feature_request](https://github.com/google/adk-python/blob/main/.github/ISSUE_TEMPLATE/feature_request.md) · [PR template](https://github.com/google/adk-python/blob/main/.github/pull_request_template.md) |
| Labels | `good first issue`: **0 open** · `help wanted`: **1 open** (as of 2026-08-31) — most work is not pre-triaged. |
| Samples path | `contributing/samples/` — see `.agents/skills/` for AI-assisted contribution. |

### `google/adk-docs`

| Rule | Detail |
|---|---|
| Doc fixes / typos | **PR-first, no issue** ([CONTRIBUTING](https://github.com/google/adk-docs/blob/main/CONTRIBUTING.md)) |
| New guide / integration page | **Issue first** to discuss; then PR + `mkdocs.yml` nav |
| Integrations | `docs/integrations/<name>.md` with `catalog_*` frontmatter — see [integrations section](https://github.com/google/adk-docs/blob/main/CONTRIBUTING.md#integrations) |
| Local preview | `pip install -r requirements.txt` · `mkdocs serve` |
| Templates | [feature_request](https://github.com/google/adk-docs/blob/main/.github/ISSUE_TEMPLATE/feature_request.md) · [bug_report](https://github.com/google/adk-docs/blob/main/.github/ISSUE_TEMPLATE/bug_report.md) · **no** checked-in PR template |
| API reference | **Do not edit** `docs/api-reference/` — generated from upstream language repos |

### `google/adk-samples`

| Rule | Detail |
|---|---|
| New recipes | Send to **`contrib/`**, not directly under `python/agents/`. |
| Checklist | [recipe-checklist.md](https://github.com/google/adk-samples/blob/main/docs/recipe-checklist.md): manifest, README ≥100 words, `uv lock`, runnability tests, `uv run validate`. |
| Templates | `[BUG]:` bug_report · recipe_request |
| Review | Automated AI reviewers on PRs (advisory). |
| Legacy path | `python/agents/safety-plugins/` still live — no deprecation banner yet. |

---

## 2.2 Google CLA — what it is and when to sign

**CLA** = [Contributor License Agreement](https://cla.developers.google.com/about). Google requires it for **every** patch to `adk-python`, `adk-docs`, and `adk-samples` before a PR can merge.

| Question | Answer |
|---|---|
| What does it do? | You **keep copyright**. You grant Google a license to use, modify, and redistribute your contribution inside the project (and related Google open-source projects). |
| Is it copyright transfer? | **No** — you retain ownership; this is a contribution license, not an assignment. |
| Sign once or per PR? | Usually **once per person** (or once per company). If you or your employer already signed the Google CLA for any project, you typically **do not sign again**. |
| Where to sign | [https://cla.developers.google.com/](https://cla.developers.google.com/) — pick **individual** or **corporate**; use the **same GitHub username** as your PR author. |
| How you know it worked | On first PR, **`google-cla`** bot comments. If unsigned, the CLA check **fails** and the PR cannot merge until you sign (often one click from the check link). |
| Corporate contributors | If your employer owns the code you write on the job, the **company** may need the corporate CLA — check with legal before filing in a work context. |

**Order of operations:** fork → branch → sign CLA (if needed) → open PR → CLA check goes green → review.

---

## 2.3 Issue & PR templates — by repo

Use the **GitHub “New issue” / PR template** in each repo. Incomplete adk-python feature requests may be **deprioritized** (stated in template).

### `google/adk-python`

| Kind | Template | URL |
|---|---|---|
| Feature | `feature_request.md` | [New feature issue](https://github.com/google/adk-python/issues/new?template=feature_request.md) |
| Bug | `bug_report.md` | [New bug issue](https://github.com/google/adk-python/issues/new?template=bug_report.md) |
| PR | `pull_request_template.md` | Auto-filled on new PR |

**Feature issue — required fields (🔴):**

1. Problem — what you are trying to solve  
2. Solution — specific feature/API change  
3. Impact on your work — why it matters; timeline if critical  
4. **Willingness to contribute — Yes/No** (required for our #4 and #5)

**Recommended (🟡):** Alternatives, proposed API/pseudocode, additional context.

**Bug issue — required fields:** Describe bug · steps to reproduce · expected · observed · environment (ADK version, OS, Python) · LiteLLM yes/no · model.

**PR — required sections:**

1. **Link to Issue** — `Closes: #N` or Problem + Solution in body  
2. **Testing Plan** — unit tests (`pytest` summary) + manual E2E unless small doc fix  
3. **Checklist** — CONTRIBUTING read, self-review, tests pass, E2E done  

For **#2, #7** (small docs): Testing Plan can state “N/A — README/markdown only”; checklist still applies.

### `google/adk-docs`

| Kind | Template | URL |
|---|---|---|
| Feature / doc request | `feature_request.md` | [New feature issue](https://github.com/google/adk-docs/issues/new?template=feature_request.md) |
| Bug | `bug_report.md` | [New bug issue](https://github.com/google/adk-docs/issues/new?template=bug_report.md) |
| PR | *(none)* | Write clear title + body; use `Fixes #N` or `Closes #N` when applicable |

**Feature issue fields:** Problem · solution you'd like · alternatives · additional context.

**Doc PR body (no template — include):**

- What changed and why  
- `mkdocs serve` tested locally (for #1 integration page)  
- For integrations: frontmatter `catalog_title`, `catalog_description`, `catalog_icon`; working code blocks  
- Link issue: `Closes #N` when issue exists  

**Integration acceptance criteria** (from CONTRIBUTING): complete, testable examples · clear developer value · publishable (no ToS circumvention).

### `google/adk-samples`

| Kind | Template | URL |
|---|---|---|
| Bug in existing sample | `bug_report.md` | Title must start **`[BUG]:`** (template sets label `bug`) |
| New recipe | `recipe_request.md` | Title **`[RECIPE]`** — not used for our #3 |
| PR | *(none)* | Describe change; our #3 is README-only on legacy path |

**Bug template fields:** Name of sample affected · description · environment (OS, Python/Java) · repro steps · error log.

**#3 is not a recipe request** — it is a **docs PR** on existing `python/agents/safety-plugins/` (legacy layout). No issue template required; follow [CONTRIBUTING](https://github.com/google/adk-samples/blob/main/CONTRIBUTING.md) PR review process.

---

## 2.4 Existing GitHub issues — do not duplicate

Searched 2026-08-31. **No open issues found** for: first-party tool-output Model Armor, `google.adk.workflows` shim, GA4 `bigQueryLinks` v1alpha docs, `bq --transfer_location`.

| Issue | Repo | Status | Relevance |
|---|---|---|---|
| [#5872](https://github.com/google/adk-python/issues/5872) | adk-python | **Closed** | SequentialAgent deprecated; Workflow cannot be `sub_agent`. Maintainer answer (2.4.0+): **Workflow-as-Tool** is the official path — pass `Workflow` in `Agent(tools=[…])`, needs `description` + `input_schema`. Native sub-agent still unresolved. **Reference in migration issues; do not re-file.** |
| [#6224](https://github.com/google/adk-python/issues/6224) | adk-python | Open | Around-call plugin hooks for durable execution — **different** from Model Armor tool-output screening. |
| [#2179](https://github.com/google/adk-docs/issues/2179) | adk-docs | Open | v2.7.1→v2.8.0 doc sync bot issue — **does not mention Model Armor yet**. Comment or extend for publishing Model Armor guide. |
| — | adk-samples | — | No open issues on ModelArmor deprecation or safety-plugins redirect. |

---

## 3. Findings by repo (issues / PR opportunities)

Severity: **P0** = blocks automation or security gap · **P1** = sharp edge / doc bug · **P2** = improvement / DX

Verification column: **✅ confirmed** · **⚠️ partial** (upstream started, gap remains) · **🔍 nuance** (adjust filing ask)

---

### 3.1 `google/adk-python`

#### P0 — `ModelArmorPlugin` does not screen tool output ✅ confirmed, no duplicate issue

**What we hit:** PRD Requirement M-10 and ADK docs state tool output is **not** screened. Our main injection path is GitHub issues, ingested mail, web results — all arrive as `function_response` parts, not as user text the plugin reads.

**Evidence:**

- Plugin module docstring: screens only `before_model_callback` / `after_model_callback` ([`integrations/model_armor/_plugin.py`](https://github.com/google/adk-python/blob/main/src/google/adk/integrations/model_armor/_plugin.py)).
- In-repo guide **Limitations** section: *"Tool output is not screened."* ([`docs/guides/integrations/model_armor/index.md`](https://github.com/google/adk-python/blob/main/docs/guides/integrations/model_armor/index.md)).
- Published site URL `https://adk.dev/guides/integrations/model_armor/` → **404** (2026-08-31 `curl -sI`). adk-docs [`safety/index.md`](https://github.com/google/adk-docs/blob/main/docs/safety/index.md) has a **two-sentence** blurb only — not a substitute for the full guide.
- We ship [`services/loop/loop/plugins/tool_output_armor.py`](../services/loop/loop/plugins/tool_output_armor.py) as a mandatory companion plugin.

**🔍 Nuance — adk-samples sample:** `ModelArmorSafetyFilterPlugin` in adk-samples **does** implement `after_tool_callback` tool-output screening, but uses older callback shapes (`on_user_message_callback`, `before_run_callback`). PRD M-6 says use first-party for input/output; do **not** copy the sample as production guardrail. Upstream should **port tool-output screening into first-party**, not just delete the sample.

**Suggested upstream work:**

1. **Issue (highest value, no duplicate):** Request first-party tool-output screening — extend `ModelArmorPlugin` with optional `screen_tool_output=True` on `after_tool_callback`, or ship `ToolOutputModelArmorPlugin`. Set **Willingness to contribute: Yes** (sample PR).
2. **PR (samples):** Add `contributing/samples/integrations/model_armor_tool_output/` showing `after_tool_callback` + `SanitizeUserPromptRequest` on stringified tool results.
3. **Docs PR (adk-docs):** Add `docs/integrations/model-armor.md` (adapt adk-python guide; follow integrations frontmatter). Cross-link from `safety/index.md`. See §5.2 #1 — **do not** claim zero adk-docs coverage.

---

#### P1 — ADK 1.x → 2.x migration gap ⚠️ partial — samples exist, narrative guide missing

**What we hit:** Early ADK 1.x codebases use `SequentialAgent`, `ParallelAgent`, `LoopAgent`. ADK 2 marks these `@deprecated` in favor of `Workflow`, but deprecation text says:

> *"Workflow cannot yet be used as an LlmAgent sub-agent."*

That blocks drop-in replacement of nested sub-agent trees — exactly how many multi-service demos structured their agents.

**Evidence:**

- [`sequential_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/sequential_agent.py) deprecation message (verified on `main`).
- Maintainer resolution in [#5872](https://github.com/google/adk-python/issues/5872): **Workflow-as-Tool** (ADK ≥2.4) is the supported replacement for many sub-agent patterns — not `sub_agents=[workflow]`.
- Samples already exist: [`contributing/samples/legacy_workflows/`](https://github.com/google/adk-python/tree/main/contributing/samples/legacy_workflows) (3 dirs) and [`contributing/samples/workflows/`](https://github.com/google/adk-python/tree/main/contributing/samples/workflows) (20+ dirs including fan-out, loop, HITL).
- We rewrote fan-out as `Workflow + JoinNode` in [`services/loop/loop/agents/workflows.py`](../services/loop/loop/agents/workflows.py); hosted path still uses deterministic engine.

**Suggested upstream work:**

1. **Issue / docs PR:** Official **migration narrative** (not more samples): ParallelAgent → `Workflow` + `JoinNode`; LoopAgent → `RequestInput` + resume; nested sub-agent trees → Workflow-as-Tool per #5872. Link closed #5872; do not ask for Workflow-as-sub-agent without acknowledging open ask.
2. **PR:** Expand `legacy_workflows/` with side-by-side “before/after” for fan-out, critique loop, human gate.

---

#### P1 — `NodeTool` / Workflow-as-Tool requires explicit `input_schema` ⚠️ partial — sample documents it

**What we hit:** Wrapping a `Workflow` on `LlmAgent.tools` fails at runtime unless the workflow has a Pydantic `input_schema`. Error: *"Node '…' does not have an input_schema defined."*

**Evidence:**

- [`tools/_node_tool.py`](https://github.com/google/adk-python/blob/main/src/google/adk/tools/_node_tool.py) lines 69–74 (verified).
- Sample [`contributing/samples/workflows/node_as_tool/README.md`](https://github.com/google/adk-python/blob/main/contributing/samples/workflows/node_as_tool/README.md) already says: assign `input_schema` + `description`, pass into `tools=[…]`.
- We added `InvestigationIn` / `CritiqueIn` in [`workflows.py`](../services/loop/loop/agents/workflows.py).

**Suggested upstream work (lower priority — sample exists):**

1. **Docs PR:** Cross-link main Workflow guide → `node_as_tool` sample; lead with `input_schema` requirement.
2. **PR (nice):** Validate at `Workflow(...)` construction when used as tool, or auto-infer schema from first `FunctionNode` signature.

---

#### P1 — Misleading import path: `google.adk.workflows` (plural) does not exist ✅ confirmed

**What we hit:** Our fallback import tries `from google.adk.workflows import Workflow` — **always fails**. Correct paths:

```python
from google.adk import Workflow          # lazy export
from google.adk.workflow import START, JoinNode
```

**Evidence:** Repro on `google-adk==2.8.0` — `ModuleNotFoundError: No module named 'google.adk.workflows'`.

**Suggested upstream work:**

1. **Our repo fix:** Remove dead fallback in [`workflows.py`](../services/loop/loop/agents/workflows.py) (lines 41, 120) — listed in §4.
2. **PR (adk-python):** Optional compatibility shim `google.adk.workflows` re-exporting `Workflow` with `DeprecationWarning`.

---

#### P2 — Docs / CLI inconsistency on deprecated agents ✅ confirmed

**What we hit:** [`src/google/adk/cli/built_in_agents/README.md`](https://github.com/google/adk-python/blob/main/src/google/adk/cli/built_in_agents/README.md) still lists `SequentialAgent, ParallelAgent, LoopAgent` without deprecation notice, while agent classes emit `@deprecated`.

**Suggested upstream work:** **Small docs PR** — mark legacy agents deprecated; point to `contributing/samples/workflows/`. Good first contribution.

---

#### P2 — Model Armor docs site lag vs package (2.8.0) ✅ confirmed

**What we hit:** Plugin shipped in ADK 2.8.0 (~2026-08-25). In-repo guide is complete; **published adk-docs site does not have the page** (404). [#2179](https://github.com/google/adk-docs/issues/2179) tracks other v2.8.0 gaps but not Model Armor specifically.

**Suggested upstream work:** **PR to adk-docs** (or comment on #2179) — publish `docs/guides/integrations/model_armor/` from adk-python. Optionally request release checklist: docs site same day as PyPI for new integrations.

---

#### P2 — Hosted Cloud Run / OAuth samples gap ⚠️ partial

**What we hit:** ADK has OAuth samples (`auth_oauth`, `oauth_calendar_agent`, `oauth2_client_credentials` under `contributing/samples/integrations/`) but not our exact pattern:

- Registered redirect: `https://loop-…/api/oauth/google/callback`
- **Separate scope bundle** for GA4 (`analytics.edit`) vs Workspace (Gmail/Calendar)
- Persist refresh token to GCS (ephemeral container FS)

**Evidence:** [`google_oauth.py`](../services/loop/loop/connectors/google_oauth.py), [`setup-ga4-auth.sh`](../scripts/setup-ga4-auth.sh).

**Suggested upstream work:**

1. **Sample PR (adk-python):** `contributing/samples/integrations/oauth/hosted_web_client/` — Cloud Run callback, offline refresh, multi-scope split.
2. **Docs:** “Automation scripts cannot use `gcloud auth print-access-token` for Analytics Admin; need user consent with `analytics.edit`.”

---

#### P2 — `google-adk[gcp]` weight vs slim control plane

**What we hit:** [`PLAN.md`](PLAN.md) §2.4 — main hosted service **excludes** `google-adk` from `requirements-host.txt` for cold-start size; ADK runs on optional `loop-adk` worker ([`scripts/deploy-adk-worker.sh`](../scripts/deploy-adk-worker.sh)).

**Suggested upstream work:** **Issue** — document minimal install surface / optional extras matrix for “orchestrator-only” vs “full ADK worker” deployments.

---

### 3.2 `google/adk-samples`

#### P1 — Stale Model Armor sample still discoverable 🔍 nuance — banner, not removal

**What we hit:** PRD M-6 says do **not** use `ModelArmorSafetyFilterPlugin` as production guardrail; use first-party `ModelArmorPlugin` for input/output. Sample remains at `python/agents/safety-plugins/` and `core/python/safety-plugins/` with **no README banner** pointing to first-party plugin.

**Verified:** Sample README does not mention `google.adk.integrations.model_armor.ModelArmorPlugin`. Sample **does** screen tool output via `after_tool_callback` — reference pattern until first-party ships that capability.

**Suggested upstream work (do not delete sample until first-party has tool-output screening):**

1. **PR:** README banner on `safety-plugins/` → prefer `ModelArmorPlugin`; note sample's `after_tool_callback` is reference-only until first-party supports tool output.
2. **Optional:** Redirect note in sample `main.py` docstring.

---

### 3.3 Google Analytics Admin API (`analyticsadmin.googleapis.com`)

#### P0 — BigQuery link CRUD only on `v1alpha`, not `v1beta` ✅ confirmed via API discovery

**What we hit:** Automating GA4 → BQ in [`scripts/setup-ga4-cove.py`](../scripts/setup-ga4-cove.py):

- Property + data stream: **`v1beta`** — works.
- List/create `bigQueryLinks`: **`v1beta` → HTTP 404**; **`v1alpha` → works**.

**API discovery proof (2026-08-31):**

- `v1beta` property sub-resources: `conversionEvents`, `customDimensions`, `dataStreams`, `googleAdsLinks`, … — **no `bigQueryLinks`**
- `v1alpha` property sub-resources: includes **`bigQueryLinks`** with methods `create`, `patch`, `delete`, `get`, `list`

**Payload quirks we had to discover:**

```json
{
  "project": "projects/PROJECT_ID",
  "datasetLocation": "US",
  "dailyExportEnabled": true,
  "streamingExportEnabled": true,
  "freshDailyExportEnabled": true
}
```

**Suggested upstream work (no GitHub issue found):**

1. **Issue (googleapis feedback or GA4 docs):** Promote `bigQueryLinks` to `v1beta` **or** document v1alpha requirement on every BQ export guide page. Include discovery JSON in issue body.
2. **Docs PR:** GA4 BigQuery export — latency table (daily vs intraday vs streaming) and which flags to set at link creation.

---

#### P1 — `ACCESS_TOKEN_SCOPE_INSUFFICIENT` / wrong ADC for automation

**What we hit:**

- `gcloud auth print-access-token` and default ADC **do not** include `analytics.edit`.
- `setup-gcp-warehouse.sh` initially picked legacy ADC without Analytics scope → 403 on `accountSummaries`.
- Fix: dedicated GA4 OAuth + `ga4_adc.json` ([`setup-ga4-auth.sh`](../scripts/setup-ga4-auth.sh)).

**Suggested upstream work:**

1. **Docs PR:** “Automating GA4 Admin API” — scope list, separate consent, do not reuse Cloud SDK user token.
2. **Issue:** `gcloud auth application-default login` could document `--scopes` including `analytics.edit` for warehouse automation.

---

#### P1 — Streaming export not enabled by default

**What we hit:** After link creation, **`streamingExportEnabled` was false** — only daily export. User asked for faster path; we set `streamingExportEnabled: true` at create time in `setup-ga4-cove.py` (~15–60 min intraday tables vs ~24h daily).

**Suggested upstream work:**

1. **Docs PR:** Recommend enabling streaming at link creation for BQ-first pipelines.
2. **Issue (product):** Consider default `streamingExportEnabled: true` in console “Link to BigQuery” wizard.

---

### 3.4 BigQuery CLI / Data Transfer Service

#### P1 — Wrong flag name: `--transfer_location` vs `--location` ✅ confirmed

**What we hit:** `bq mk --transfer_config --transfer_location=us` fails (unknown flag). Correct: **`--location=REGION`** (we use `us-central1` to match datasets).

**Repro (2026-08-31):**

```text
FATAL Flags parsing error: Unknown command line flag 'transfer_location'.
Did you mean: transfer_config ?
```

**Evidence:** [`setup-gcp-warehouse.sh`](../scripts/setup-gcp-warehouse.sh).

**Suggested upstream work (no public google-cloud-sdk GitHub issue found via search):**

1. **Issue (cloud-sdk feedback):** Alias `--transfer_location` → `--location` with deprecation warning, or fix stale docs showing `transfer_location`.
2. **Docs PR:** Google Ads → BQ transfer — create target dataset in same region **before** transfer config.

---

#### P1 — Google Ads transfer cannot be fully automated from CI

**What we hit:** `bq mk --transfer_config --data_source=google_ads` opens **browser OAuth**; requires pasting `version_info` token back into terminal. No headless path for Cloud Build / Cloud Run job.

**Suggested upstream work:**

1. **Issue:** Document service-account / workforce identity path for Ads transfer, or officially mark as “interactive setup only.”
2. **Docs PR:** Clarify GCP credits cover BQ transfer **infrastructure**, not Ads **spend**.

---

#### P1 — Cross-region dataset copy fails silently in scripts

**What we hit:** `CREATE TABLE loop_ads.campaign_daily AS SELECT * FROM loop_raw.campaign_daily` failed when `loop_ads` was **`US`** and `loop_raw` was **`us-central1`**.

**Fix:** Recreate `loop_ads` in `us-central1` ([`setup-gcp-warehouse.sh`](../scripts/setup-gcp-warehouse.sh)).

**Suggested upstream work:** **Docs PR** — Data Transfer target dataset region must match analytics dataset region.

---

### 3.5 Workspace OAuth / Google Auth Platform (platform, not one repo)

#### P1 — `redirect_uri_mismatch` when codelabs use localhost

**What we hit:** Initial [`setup-ga4-auth.sh`](../scripts/setup-ga4-auth.sh) used `http://localhost:8765/`; production Web client only registered Cloud Run callback → **400 redirect_uri_mismatch**.

**Fix:** Route all consent through hosted Loop URLs (`/api/oauth/ga4/start`).

**Suggested upstream work:**

1. **Docs PR (ADK / Workspace codelabs):** Section “Production redirect URIs (Cloud Run)” — register exact callback, never assume localhost.
2. **Issue:** Auth Platform UI could show “common mistake: localhost mismatch” when error occurs.

---

#### P2 — No `gcloud` command to create Web OAuth clients

**What we hit:** [`LEARNINGS.md`](LEARNINGS.md) — must use Google Auth Platform console; `gcloud iam oauth-clients` is workforce, not the same.

**Suggested upstream work:** **Issue** — Auth Platform CLI for Web client CRUD (automation for hackathon setups).

---

### 3.6 ADK 1.x → 2.x pattern mapping (Product OS)

Real-world pre–ADK-2 multi-agent shapes and how we mapped them.

| Pattern | ADK 1.x typical shape | Our ADK 2 mapping |
|---|---|---|
| Fan-out investigators | `ParallelAgent` | `Workflow` + `JoinNode` ([`workflows.py`](../services/loop/loop/agents/workflows.py)) |
| Draft → critique loop | `LoopAgent` | `proposal_critique` Workflow |
| Skip-if-done HITL | `before_tool_callback` | `RequestInput` + our approve reuse ([`HACKATHON_STORY.md`](HACKATHON_STORY.md)) |
| Nested pipeline under orchestrator | `SequentialAgent` as `sub_agent` | Workflow-as-Tool on `LlmAgent.tools` (per [#5872](https://github.com/google/adk-python/issues/5872)) |
| Live UI | WebSocket + `agent_callback` | [`loop/live.py`](../services/loop/loop/live.py) Hub |
| Gmail send | Service account + DWD | **Rejected** — user OAuth draft only (Google codelab pattern) |
| Multi Cloud Run services | Many agent services | Single `loop` + optional `loop-adk` worker |

**Suggested upstream work (adk-python):** **Docs issue/PR** — official migration blog or guide referencing #5872 and existing workflow samples.

---

## 4. What we already patched locally (do not re-report as Google bugs)

These are **Product OS** fixes; listed so the contribution agent does not duplicate them as upstream issues.

| Area | Our fix | File(s) |
|---|---|---|
| GA4 OAuth hosted flow | `/api/oauth/ga4/*` + GCS `ga4_adc.json` | `google_oauth.py`, `api.py`, `setup-ga4-auth.sh` |
| GA4 BQ link API version | Use `v1alpha/bigQueryLinks` | `setup-ga4-cove.py` |
| GA4 ADC priority | Prefer `ga4_adc.json` over generic ADC | `setup-ga4-cove.py`, `setup-gcp-warehouse.sh` |
| Streaming export | `streamingExportEnabled: true` at link create | `setup-ga4-cove.py` |
| Tool-output screening | Custom `ToolOutputArmorPlugin` | `plugins/tool_output_armor.py` |
| ADK worker split | `loop-adk` Cloud Run service | `adk_runtime.py`, `deploy-adk-worker.sh` |
| BQ Ads demo region | `loop_ads` in `us-central1` | `setup-gcp-warehouse.sh` |
| Deploy env preservation | Re-read Cloud Run env before `--set-env-vars` | `deploy-gcp.sh` |
| Dead ADK import fallback | **TODO:** remove `google.adk.workflows` try/except | `agents/workflows.py` lines 41, 120 |

---

## 5. Upstream filing list — **these 7 only**

Maintainer-lens triage (2026-08-31). Everything else in §3 (GA4, bq, Auth Platform, OAuth sample, workflows shim) stays **local / product feedback** — do not file unless asked.

**Do not file any item until its §5.2 gate is `GO`.** Re-run checks on `main` if more than a week passes.

| # | Repo | What | Type | Issue first? | Ack before PR? |
|---|---|---|---|---|---|
| **1** | [google/adk-docs](https://github.com/google/adk-docs) | Add dedicated Model Armor integration page (adapt from adk-python guide); tool-output limitation callout | **PR** | **Yes** — adk-docs “New Documentation” ([CONTRIBUTING](https://github.com/google/adk-docs/blob/main/CONTRIBUTING.md)) | **Soft** — issue first; PR can follow without waiting if issue describes full scope |
| **2** | [google/adk-python](https://github.com/google/adk-python) | CLI README: mark Sequential/Parallel/Loop agents `@deprecated`; link `contributing/samples/workflows/` | **PR** | No | **No** |
| **3** | [google/adk-samples](https://github.com/google/adk-samples) | `safety-plugins/` README banner → prefer `ModelArmorPlugin`; sample is reference for tool-output hooks | **PR** | No | **No** |
| **4** | google/adk-python | Sample `contributing/samples/integrations/model_armor_tool_output/` (`after_tool_callback` screening) | **Issue + PR** | Yes | **No** — see [#6730](https://github.com/google/adk-python/issues/6730) pattern |
| **5** | google/adk-python | First-party tool-output Model Armor (extend plugin or ship companion) | **Issue only** (no core PR yet) | Yes | **Yes** — large change per CONTRIBUTING |
| **6** | google/adk-python and/or adk-docs | Migration narrative: 1.x agents → Workflow + JoinNode / Workflow-as-Tool; reference [#5872](https://github.com/google/adk-python/issues/5872) | **Issue + PR** | Yes on adk-docs; optional on adk-python | **Soft** on adk-docs |
| **7** | google/adk-python | Add `node_as_tool` to Workflow guide “Related samples”; note `input_schema` | **PR** | No | **No** — can bundle into #6 |

**Filing order:** 2 → 3 → 7 (parallel, lowest risk) → 1 (issue then PR) → 4 → 5 → 6.

---

## 5.2 Verification ledger — per item (pass 2, 2026-08-31)

Each row is what we checked, what is true, and what must **not** be overstated in issues/PRs.

### #1 — Model Armor on adk-docs · **GO** (wording must be precise)

| Check | Result | Evidence |
|---|---|---|
| Full guide on adk-python `main` | ✅ | [`docs/guides/integrations/model_armor/index.md`](https://github.com/google/adk-python/blob/main/docs/guides/integrations/model_armor/index.md) — includes **Limitations → “Tool output is not screened.”** |
| Dedicated page on adk.dev | ❌ 404 | `curl -sI https://adk.dev/guides/integrations/model_armor/` → **HTTP 404** |
| Listed in adk-docs `docs/integrations/` | ❌ | `gh api …/docs/integrations` — **no** `model-armor.md` (80+ integrations; ATR guardrail exists, Model Armor does not) |
| Mention anywhere on adk-docs | ⚠️ Brief only | [`docs/safety/index.md`](https://github.com/google/adk-docs/blob/main/docs/safety/index.md) — **two sentences** under plugins; no install, config, limitations, or tool-output gap |
| [#2179](https://github.com/google/adk-docs/issues/2179) covers Model Armor | ❌ | Open bot issue for v2.7.1→v2.8.0; body lists `max_llm_calls`, A2A — **not Model Armor** |
| adk-docs has `docs/guides/` tree | ❌ | `gh api …/docs/guides` → 404; integrations live under **`docs/integrations/*.md`** with `catalog_*` frontmatter (see `atr-guardrail.md`) |

**Honest claim for issue/PR:** “2.8.0 shipped `ModelArmorPlugin`; adk-python has a full in-repo guide; adk-docs only has a safety blurb — need a dedicated integration page.” **Do not claim** “zero documentation on adk-docs.”

**PR target (verified):** `docs/integrations/model-armor.md` + `mkdocs.yml` nav + cross-link from `docs/safety/index.md`. Adapt content from adk-python guide; follow [integration template](https://github.com/google/adk-docs/blob/main/CONTRIBUTING.md#integrations).

**Gate:** `GO` after re-checking 404 and integrations list still true.

---

### #2 — CLI README deprecation · **GO**

| Check | Result | Evidence |
|---|---|---|
| README still lists legacy agents without `@deprecated` | ✅ | [`built_in_agents/README.md`](https://github.com/google/adk-python/blob/main/src/google/adk/cli/built_in_agents/README.md) line: *“Supports all agent types: LlmAgent, SequentialAgent, ParallelAgent, LoopAgent”* |
| Agents actually deprecated in code | ✅ | [`sequential_agent.py`](https://github.com/google/adk-python/blob/main/src/google/adk/agents/sequential_agent.py) `@deprecated(… Workflow cannot yet be used as an LlmAgent sub-agent.)` on `main` |
| Existing PR fixing this | ❌ | `gh search prs --repo google/adk-python "built_in_agents README deprecated"` — none |

**Gate:** `GO` — single-file doc PR.

---

### #3 — adk-samples README banner · **GO**

| Check | Result | Evidence |
|---|---|---|
| No pointer to first-party plugin | ✅ | [`python/agents/safety-plugins/README.md`](https://github.com/google/adk-samples/blob/main/python/agents/safety-plugins/README.md) — **no** `google.adk.integrations.model_armor` |
| Sample still has tool-output hook | ✅ | [`model_armor.py`](https://github.com/google/adk-samples/blob/main/python/agents/safety-plugins/safety_plugins/plugins/model_armor.py) — `async def after_tool_callback` |
| Duplicate README | ⚠️ | `core/python/safety-plugins/README.md` — **identical** SHA256 to `python/agents/…` (2026-08-31); edit **both** or confirm mirror policy before PR |
| Open issue/PR for banner | ❌ | `gh search issues --repo google/adk-samples ModelArmor` — none |

**Honest claim:** Banner + “reference sample, not production guardrail for input/output; use first-party `ModelArmorPlugin`.” **Do not** ask to delete the sample.

**Gate:** `GO` — confirm both README paths still identical before editing.

---

### #4 — `model_armor_tool_output` sample · **GO**

| Check | Result | Evidence |
|---|---|---|
| Sample path exists | ❌ (gap real) | `contributing/samples/integrations/` — **no** `model_armor*` directory; `gh search code model_armor_tool_output` — empty |
| First-party plugin has `after_tool_callback` | ❌ | [`_plugin.py`](https://github.com/google/adk-python/blob/main/src/google/adk/integrations/model_armor/_plugin.py) — only `before_model_callback` / `after_model_callback` |
| Duplicate GitHub issue | ❌ | `gh search issues "tool output" "Model Armor"` / `"Tool output is not screened"` — **no** matching open issue |
| Unit test pattern to follow | ✅ | [`tests/unittests/integrations/model_armor/`](https://github.com/google/adk-python/tree/main/tests/unittests/integrations/model_armor) |

**Gate:** `GO` — issue + PR same day; include `pytest` + sample under `contributing/samples/integrations/`.

---

### #5 — First-party tool-output feature · **GO** (issue only first)

| Check | Result | Evidence |
|---|---|---|
| Documented gap | ✅ | In-repo guide **Limitations** + PRD M-10 |
| Duplicate issue | ❌ | Same searches as #4 |
| Related open issue | ⚠️ Different scope | [#6224](https://github.com/google/adk-python/issues/6224) — around-call hooks for durable execution, **not** Model Armor |

**Honest claim:** Feature request to close documented limitation; reference #4 sample PR as proposed implementation sketch. **Do not** open core plugin PR until maintainer feedback.

**Gate:** `GO` for **issue only** after #4 PR is linked.

---

### #6 — Migration narrative · **GO**

| Check | Result | Evidence |
|---|---|---|
| Official migration doc | ❌ | No adk-docs/adk-python doc titled migration 1.x→2.x; `gh search code "Workflow-as-Tool"` on adk-docs — empty |
| Samples exist | ✅ | [`legacy_workflows/`](https://github.com/google/adk-python/tree/main/contributing/samples/legacy_workflows) (3 dirs); [`workflows/`](https://github.com/google/adk-python/tree/main/contributing/samples/workflows) (20+ dirs) |
| Maintainer direction | ✅ Closed | [#5872](https://github.com/google/adk-python/issues/5872) — closed 2026-07-31; Workflow-as-Tool (≥2.4) is supported path; **do not** re-ask Workflow-as-sub-agent |
| “Workflow-as-Tool” in adk-python docs | ⚠️ Minimal | Only in sample code comment (`node_as_tool/agent.py`); not in narrative guide |

**Honest claim:** Narrative doc linking samples + #5872 resolution — **not** “no samples exist.”

**Gate:** `GO` — issue on adk-docs (or adk-python `docs/guides/`) before large PR.

---

### #7 — Workflow guide → `node_as_tool` · **GO**

| Check | Result | Evidence |
|---|---|---|
| Workflow guide lists related samples | ✅ 7 samples | [`workflow/index.md`](https://github.com/google/adk-python/blob/main/docs/guides/workflow/workflow/index.md) **Related samples** — sequence, route, loop, nested, fan_out, dynamic, retry |
| `node_as_tool` in that list | ❌ | `grep -c node_as_tool` on guide → **0** |
| Sample documents `input_schema` | ✅ | [`node_as_tool/README.md`](https://github.com/google/adk-python/blob/main/contributing/samples/workflows/node_as_tool/README.md) — *“assign both an `input_schema` and a `description`”* |

**Gate:** `GO` — add one bullet to Related samples + optional sentence in Workflow-as-Tool section.

---

## 5.3 Filing gates (checklist before each PR/issue)

| # | Gate — all must be true |
|---|---|
| 1 | adk.dev integration URL still 404; no new `model-armor.md` on adk-docs `main`; issue opened per adk-docs CONTRIBUTING |
| 2 | `built_in_agents/README.md` on `main` still lacks deprecation notice |
| 3 | Both safety-plugins READMEs still lack banner; both paths still identical |
| 4 | No `model_armor_tool_output` sample on `main`; CLA signed; `pytest` + `tox` pass |
| 5 | #4 PR URL ready; issue uses feature_request template + “Willingness: Yes” |
| 6 | #5872 still closed; `docs/2.0/index.md` is runtime migration not agent-pattern migration; no duplicate issue |
| 7 | `workflow/index.md` still omits `node_as_tool` from Related samples |

---

## 5.1 Issue vs PR — guidelines and observed patterns (verified 2026-08-31)

Read the repo CONTRIBUTING before filing. **They do not require explicit maintainer ACK before most PRs** — the rule is *type-dependent*, not “wait for permission.”

### Written rules

| Repo | Small docs / typo | New docs or feature | Large / architectural |
|---|---|---|---|
| **adk-python** | PR OK; issue optional ([CONTRIBUTING](https://github.com/google/adk-python/blob/main/CONTRIBUTING.md)) | Issue **or** full problem/solution in PR body | **Issue first** → gather feedback |
| **adk-docs** | **PR-first, no issue** ([CONTRIBUTING](https://github.com/google/adk-docs/blob/main/CONTRIBUTING.md)) | **Issue first** to discuss content | **Issue first; wait for feedback** before starting |
| **adk-samples** | PR + review | Recipe checklist; new work → `contrib/` | Same — no “wait for ACK” rule |

**adk-python nuance:** “For other issues, please **kindly ask before contributing** to avoid duplication” means **search / comment on an existing issue** — not “maintainers must approve your plan before you open a PR.”

### What maintainers actually do (recent PRs/issues)

| Pattern | Example | Maintainer response |
|---|---|---|
| **Docs PR without issue** | [adk-python #6959](https://github.com/google/adk-python/pull/6959) (fix broken sample links) | Open; CLA only — **no linked issue number** (template mentions “Link to Issue” but body has none) |
| **Docs PR closes issue** | [adk-docs #1853](https://github.com/google/adk-docs/pull/1853) → Fixes #1852 | Merged |
| **Issue → PR invited** | [#6730](https://github.com/google/adk-python/issues/6730) | `@sanketpatil06`: *“If you already have a solution in mind, please feel free to open a PR.”* → landed [#6874](https://github.com/google/adk-python/pull/6874) |
| **Issue + same-day PR** | [#6836](https://github.com/google/adk-python/issues/6836) / [#6837](https://github.com/google/adk-python/pull/6837) | Maintainer confirmed PR resolves issue; review on PR |
| **Issue + PR closes** | [#6887](https://github.com/google/adk-python/issues/6887) / [#6892](https://github.com/google/adk-python/pull/6892) | `Closes: #6887` — no prior ACK required |
| **Feature author owns PR** | [#6817](https://github.com/google/adk-python/issues/6817) / [#6825](https://github.com/google/adk-python/pull/6825) | Author self-assigned; maintainer: *“Thanks for raising a PR… being reviewed”* |
| **Closed without Workflow-as-sub-agent** | [#5872](https://github.com/google/adk-python/issues/5872) | Do not re-file architectural ask; use Workflow-as-Tool in docs (#6) |

### Per-item filing recipe (the 7)

| # | Step |
|---|---|
| 1 | **Open issue** on adk-docs (new integration page scope) → **PR** adapting adk-python guide to `docs/integrations/model-armor.md`. Re-run §5.3 gate first. Optional note on #2179 — it does **not** track Model Armor today. |
| 2 | **PR only** to adk-python. Problem + solution in PR template. |
| 3 | **PR only** to adk-samples. Edit **both** `python/agents/safety-plugins/README.md` and `core/python/safety-plugins/README.md` if still identical. |
| 4 | **Open issue** (feature_request: impact, willingness Yes) → **open PR same day** linking issue. Maintainer pattern favors this over issue-only. |
| 5 | **Open issue** after #4 PR is up; link sample PR. Expect design discussion — do **not** open core-plugin PR until feedback (large change). |
| 6 | For adk-docs new page: **open issue first**, wait ~2–5 days for feedback **or** proceed if silence (CONTRIBUTING says discuss; practice is often PR with clear scope). For adk-python `docs/guides/` only: PR-first OK. |
| 7 | **PR only**; can be part of #6 diff. |

**Copybara reminder:** merged adk-python PRs may show **closed** + `merged` label — not rejected.

---

## 5.4 Template & title guide — each of the 7

Use §2.2 (CLA) + §2.3 (templates). Fill every **required** field; do not paste Product OS–specific URLs/secrets.

### #1 — Model Armor integration page · `google/adk-docs`

| Step | Action |
|---|---|
| Issue template | [feature_request](https://github.com/google/adk-docs/issues/new?template=feature_request.md) |
| Suggested title | `docs(integrations): add Model Armor integration page (ADK 2.8)` |
| Issue — Problem | ADK 2.8 ships `ModelArmorPlugin`; adk-python has full guide; adk-docs only has 2-sentence blurb in `safety/index.md`; dedicated integration URL 404 |
| Issue — Solution | Add `docs/integrations/model-armor.md` adapted from adk-python; include Limitations (tool output not screened); link from safety page |
| Issue — Alternatives | Expand safety blurb only — rejected (insufficient for install/config) |
| PR | After issue; body: `Closes #N`, list files (`model-armor.md`, `mkdocs.yml`, `safety/index.md`), confirm `mkdocs serve` |
| PR testing | “Previewed with `mkdocs serve`; links verified” |

### #2 — CLI README deprecation · `google/adk-python`

| Step | Action |
|---|---|
| Issue | **Skip** — small documentation fix per CONTRIBUTING |
| PR template | [Compare on fork](https://github.com/google/adk-python/compare) — template auto-loads |
| Suggested title | `docs(cli): mark Sequential/Parallel/Loop agents deprecated in Agent Builder README` |
| PR — Problem | `built_in_agents/README.md` lists legacy agents without matching `@deprecated` in code |
| PR — Solution | Add deprecation notice + links to `contributing/samples/workflows/` and `legacy_workflows/` |
| Testing Plan | `N/A — markdown only` |

### #3 — safety-plugins README banner · `google/adk-samples`

| Step | Action |
|---|---|
| Issue | **Skip** — README clarification |
| Suggested PR title | `docs(safety-plugins): point to first-party ModelArmorPlugin` |
| PR body | Problem / Solution / both README paths edited (`python/agents/…` and `core/python/…` if still identical) |
| Do not | Open `[RECIPE]` issue; do not delete sample |

### #4 — tool-output sample · `google/adk-python`

| Step | Action |
|---|---|
| Issue template | [feature_request](https://github.com/google/adk-python/issues/new?template=feature_request.md) |
| Suggested title | `sample: Model Armor tool-output screening via after_tool_callback` |
| Problem | Documented limitation: tool output not screened by `ModelArmorPlugin`; injection via tool results is common |
| Solution | Sample under `contributing/samples/integrations/model_armor_tool_output/` |
| Impact | Security/guardrail completeness for agentic pipelines |
| Willingness | **Yes** |
| Proposed API | Reference `after_tool_callback` + `SanitizeUserPromptRequest` on stringified tool results |
| PR | Same day; `Closes: #N`; full PR template + `pytest tests/unittests/...` summary + `tox` if sample touches core paths |

### #5 — first-party tool-output feature · `google/adk-python`

| Step | Action |
|---|---|
| Issue template | [feature_request](https://github.com/google/adk-python/issues/new?template=feature_request.md) |
| Suggested title | `feat(model_armor): screen tool output in ModelArmorPlugin (or companion plugin)` |
| Problem | Same as #4 but asks for **first-party** support |
| Solution | e.g. `screen_tool_output: bool` on config, or `ToolOutputModelArmorPlugin` in `integrations/model_armor` |
| Willingness | **Yes** — sample in PR linked from #4 |
| PR | **Do not open yet** — issue only until maintainer feedback (Large or Complex Changes) |

### #6 — migration narrative · `adk-docs` and/or `adk-python`

| Step | Action |
|---|---|
| Issue (adk-docs) | [feature_request](https://github.com/google/adk-docs/issues/new?template=feature_request.md) |
| Suggested title | `docs: ADK 1.x → 2.x migration guide (ParallelAgent → Workflow / Workflow-as-Tool)` |
| Problem | Deprecated agents; no single narrative; #5872 closed with Workflow-as-Tool direction |
| Solution | Guide linking `legacy_workflows/` + `workflows/node_as_tool` samples; do **not** re-open sub-agent ask |
| PR | adk-docs and/or adk-python `docs/guides/`; `Closes #N` |

### #7 — node_as_tool cross-link · `google/adk-python`

| Step | Action |
|---|---|
| Issue | **Skip** — small doc fix (can bundle into #6 PR) |
| Suggested title | `docs(workflow): add node_as_tool to Related samples; note input_schema` |
| PR — Problem | Workflow guide lists 7 related samples but omits `node_as_tool` |
| PR — Solution | Add bullet linking `contributing/samples/workflows/node_as_tool/` + one line on mandatory `input_schema` |
| Testing Plan | `N/A — markdown only` |

---

## 6. Reproduction commands (for issue bodies)

```bash
# ADK import paths (verified 2026-08-31, google-adk==2.8.0)
pip install 'google-adk>=2.8.0' -t /tmp/adk-check
python3 -c "
import sys; sys.path.insert(0,'/tmp/adk-check')
from google.adk import Workflow
from google.adk.workflow import START, JoinNode
print('OK', Workflow, JoinNode)
import importlib
importlib.import_module('google.adk.workflows')  # ModuleNotFoundError
"

# GA4 Admin API — BigQuery links (needs analytics.edit token)
# v1beta → 404 on .../bigQueryLinks (not in discovery schema)
# v1alpha → 200
curl -s -H "Authorization: Bearer $GA4_TOKEN" \
  "https://analyticsadmin.googleapis.com/v1alpha/properties/PROPERTY_ID/bigQueryLinks"

# API discovery — no auth required
curl -s 'https://analyticsadmin.googleapis.com/$discovery/rest?version=v1beta' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(sorted(d['resources']['properties']['resources'].keys()))"
curl -s 'https://analyticsadmin.googleapis.com/$discovery/rest?version=v1alpha' \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('bigQueryLinks' in d['resources']['properties']['resources'])"

# bq transfer config — use --location not --transfer_location
bq mk --transfer_config --transfer_location=us  # FATAL: unknown flag
bq mk --transfer_config --project_id=PROJECT --location=us-central1 \
  --data_source=google_ads --target_dataset=loop_ads \
  -p='{"customer_id":"CUSTOMER_ID"}'
```

---

## 7. References in this repo

| Topic | Doc / code |
|---|---|
| ADK 2 architecture honest map | [`ENTERPRISE_TRACK.md`](ENTERPRISE_TRACK.md) |
| Adopted multi-agent patterns | [`HACKATHON_STORY.md`](HACKATHON_STORY.md) |
| ADK Workflow vs 1.x agents | [`LEARNINGS.md`](LEARNINGS.md) § ADK 2 Workflow |
| Model Armor M-6–M-11 | [`PRD.md`](PRD.md) §14.5 |
| Research traps (failOpen, docs lag) | [`RESEARCH_LEARNINGS.md`](RESEARCH_LEARNINGS.md) |
| Workflow graphs | [`services/loop/loop/agents/workflows.py`](../services/loop/loop/agents/workflows.py) |
| Tool output plugin | [`services/loop/loop/plugins/tool_output_armor.py`](../services/loop/loop/plugins/tool_output_armor.py) |
| GA4 automation | [`scripts/setup-ga4-cove.py`](../scripts/setup-ga4-cove.py) |
| Medium tutorial (OAuth/GA4/BQ) | [`medium/TUTORIAL_POST.md`](medium/TUTORIAL_POST.md) |
| **Paste-ready upstream drafts** | [`upstream/DRAFTS.md`](upstream/DRAFTS.md) |

---

## 8. Agent instructions (for the handoff)

**Scope:** File **only §5 (7 items)** unless the user expands scope. **Use [`upstream/DRAFTS.md`](upstream/DRAFTS.md)** for paste-ready bodies.

1. **Search first** — Check §2.4 for duplicates. Do not re-open #5872’s Workflow-as-sub-agent ask.
2. **Sign Google CLA** — §2.2; same GitHub username as PR author; confirm `google-cla` check green.
3. **Use repo templates** — §2.3 and §5.4 for each of the 7; fill all required fields.
4. **Follow §5.1–§5.3** — run gates before filing.
5. **No ACK wait** for #2, #3, #7. adk-docs **#1** and **#6**: issue first per CONTRIBUTING; PR can follow without reply if scope is complete.
6. **Precise claims only** — use §5.2 “Honest claim” rows; never overstate (e.g. Model Armor is not “undocumented everywhere”).
7. **Do not remove** adk-samples Model Armor sample (#3 = banner only).
8. **Cross-link PLAN.md** — hybrid engine is intentional.
9. **Fix locally** — remove `google.adk.workflows` fallback in `workflows.py` (§4).
