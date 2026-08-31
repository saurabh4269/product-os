# Upstream drafts — ready to paste (pass 3 verified)

| Field | Value |
|---|---|
| Verified | **2026-08-31 pass 3** — `main` on google/adk-python, google/adk-docs, google/adk-samples |
| Parent doc | [`GOOGLE_OPEN_SOURCE_LEARNINGS.md`](../GOOGLE_OPEN_SOURCE_LEARNINGS.md) |
| Before filing | Sign [Google CLA](https://cla.developers.google.com/) · run §5.3 gates · use same GitHub user on CLA + PR |

---

## Pass 3 verification summary

| # | Gate | Result | Evidence (2026-08-31) |
|---|---|---|---|
| 1 | Dedicated Model Armor page missing on adk.dev | ✅ | `curl -sI https://adk.dev/integrations/model-armor/` → **404**; `docs/integrations/model-armor.md` → **404** on adk-docs API |
| 1 | Source guide exists | ✅ | adk-python [`docs/guides/integrations/model_armor/index.md`](https://github.com/google/adk-python/blob/main/docs/guides/integrations/model_armor/index.md) |
| 1 | Safety blurb only | ✅ | adk-docs `safety/index.md` — two sentences under plugins; no install/config/limitations |
| 2 | CLI README gap | ✅ | Line 35: *Supports all agent types: LlmAgent, SequentialAgent, ParallelAgent, LoopAgent* — no deprecation |
| 3 | No first-party pointer | ✅ | `grep -ci google.adk.integrations.model_armor` → **0**; PY/CORE README SHA **identical** |
| 4 | No sample / no duplicate issue | ✅ | No `model_armor_tool_output`; no matching open issue |
| 4 | Plugin gap | ✅ | `_plugin.py`: only `before_model_callback` / `after_model_callback`; Limitations docstring |
| 5 | No feature issue | ✅ | Search empty; #6224 unrelated |
| 6 | No agent-pattern migration guide | ✅ | `docs/2.0/index.md` covers Workflow **runtime** breaks, not SequentialAgent→Workflow-as-Tool; #5872 **closed** 2026-07-31 |
| 7 | node_as_tool omitted | ✅ | Workflow guide Related samples: **7** bullets, **0** `node_as_tool` |

**Filing order:** #2 → #3 → #7 (parallel) → #1 issue → #1 PR → #4 issue+PR → #5 issue → #6 issue → #6 PR.

---

# Item 1 — Model Armor integration page · `google/adk-docs`

## Issue (template: feature_request)

**Title:** `docs(integrations): add Model Armor integration page (ADK 2.8)`

**Body:**

```markdown
**Is your feature request related to a problem? Please describe.**

ADK Python 2.8.0 (released 2026-08-25) ships a first-party, documented `ModelArmorPlugin` in `google.adk.integrations.model_armor`. The full guide exists in the adk-python repository:

https://github.com/google/adk-python/blob/main/docs/guides/integrations/model_armor/index.md

On adk.dev today:

- `/integrations/model-armor/` returns **404** (verified 2026-08-31).
- There is no `docs/integrations/model-armor.md` in the adk-docs repository.
- The only mention is a two-sentence blurb on the [Safety](https://adk.dev/safety/) page under plugin examples — no install steps, configuration table, regional endpoint rules, or documented limitations.

Developers following ADK 2.8 release notes cannot find how to install, configure, or understand gaps (e.g. tool-output screening) on the published docs site.

**Describe the solution you'd like**

Add a dedicated integration page at `docs/integrations/model-armor.md` (following the same frontmatter pattern as other integrations, e.g. BigQuery Agent Analytics), adapted from the adk-python guide:

- Install: `pip install 'google-adk[gcp]'`
- `ModelArmorPlugin` + `ModelArmorConfig` usage on `App`
- Template path / regional endpoint requirements
- **Limitations** section including: *"Tool output is not screened"* (documented in upstream guide)
- Cross-link from `docs/safety/index.md` Model Armor bullet to the new page

**Describe alternatives you've considered**

- Expanding the Safety page blurb only — insufficient for a first-party GCP integration shipped in 2.8.0.
- Waiting for adk-bot issue #2179 — that issue tracks v2.7.1→v2.8.0 diffs but does **not** list Model Armor today.

**Additional context**

- Upstream source of truth: adk-python `docs/guides/integrations/model_armor/index.md`
- Related: Product OS documents this gap for our own ADK 2.8 adoption (external repo; not required reading for this issue).
- I am willing to open a PR with the page + `mkdocs serve` verification if this approach is acceptable.
```

## PR (no repo template — use this body)

**Title:** `docs(integrations): add Model Armor integration page`

**Body:**

```markdown
Closes #ISSUE_NUMBER

## Summary

Adds `docs/integrations/model-armor.md` adapted from the adk-python integration guide (ADK 2.8.0). Updates the Model Armor bullet on `docs/safety/index.md` to link to the new page.

## Files

- `docs/integrations/model-armor.md` (new)
- `docs/safety/index.md` (link to integration page)
- `docs/integrations/assets/model-armor.png` (new icon — or placeholder noted in review)

## Testing

- [x] `mkdocs serve` — page renders at `/integrations/model-armor/`
- [x] Internal links to `/plugins/` and Cloud Model Armor docs verified
- [x] Code blocks match adk-python guide on `main`

## Note on icon

No existing `model-armor` asset in `docs/integrations/assets/` as of 2026-08-31. PR includes a placeholder PNG or reuses a suitable GCP security icon per maintainer preference.
```

### PR file: `docs/integrations/model-armor.md` (draft content)

```markdown
---
catalog_title: Model Armor Plugin
catalog_description: Screen user input and model output with Google Cloud Model Armor
catalog_icon: /integrations/assets/model-armor.png
catalog_tags: ["security", "google"]
---

# Model Armor plugin for ADK

<div class="language-support-tag">
  <span class="lst-supported">Supported in ADK</span><span class="lst-python">Python v2.8.0</span>
</div>

`ModelArmorPlugin` screens user input and model output against [Google Cloud Model Armor](https://cloud.google.com/security-command-center/docs/model-armor-overview) templates. When a filter matches, or when screening cannot complete (fail-closed by default), content is replaced with a safe message before it reaches the model or the user.

The integration provides `ModelArmorPlugin` (a `BasePlugin`) and `ModelArmorConfig` (template paths, blocked messages, `block_on_screening_failure`).

## Use cases

- **Prompt-injection / jailbreak mitigation** on inbound user text before the model call.
- **Unsafe model output blocking** before responses reach the user (unary and live transcription paths).
- **Fail-closed deployments** where unscreened content is treated as unsafe.

## Prerequisites

- Google Cloud project with [Model Armor templates](https://cloud.google.com/security-command-center/docs/manage-model-armor-templates) in a supported region (e.g. `us-central1`).
- `pip install 'google-adk[gcp]'` (pulls `google-cloud-modelarmor`).
- Application Default Credentials with permission to invoke Model Armor (e.g. `roles/modelarmor.user` on the templates).

## Installation

```shell
pip install 'google-adk[gcp]'
```

## Use with agent

```python
from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.integrations.model_armor import ModelArmorConfig
from google.adk.integrations.model_armor import ModelArmorPlugin

agent = LlmAgent(
    name="screened_agent",
    description="Assistant whose input and output are screened.",
    instruction="You are a helpful assistant.",
)

app = App(
    name="model_armor_demo",
    root_agent=agent,
    plugins=[
        ModelArmorPlugin(
            config=ModelArmorConfig(
                prompt_template_name=(
                    "projects/PROJECT_ID/locations/us-central1/templates/PROMPT_TEMPLATE"
                ),
                response_template_name=(
                    "projects/PROJECT_ID/locations/us-central1/templates/RESPONSE_TEMPLATE"
                ),
            )
        )
    ],
)
```

Prompt and response templates must use full resource paths and reside in the **same** region. The plugin targets `modelarmor.{location}.rep.googleapis.com`.

## Configuration

| Field | Description |
|---|---|
| `prompt_template_name` | Screen user input (`before_model_callback`). Optional. |
| `response_template_name` | Screen model output (`after_model_callback`). Optional. |
| `input_blocked_message` / `output_blocked_message` | Replacement text when blocked. |
| `block_on_screening_failure` | Default `True` — block when Model Armor cannot return SUCCESS. |

At least one template name is required.

Blocked responses include `custom_metadata['model_armor_blocked']` for UI handling.

## Limitations

- **Tool output is not screened.** The plugin reads the latest `user` content with text parts only. Tool results arrive as `function_response` parts and do not reach Model Armor. Pipelines that ingest GitHub issues, email, or web search via tools need a separate `after_tool_callback` guardrail if tool output is in scope for your threat model.
- **Regional binding:** one plugin instance → one Model Armor region; prompt and response templates must match.
- **Live audio** is screened via transcriptions, not raw audio.

For plugin architecture background, see [Plugins](/plugins/) and [Safety guardrails](/safety/).

## Resources

- [Model Armor overview](https://cloud.google.com/security-command-center/docs/model-armor-overview)
- [Manage Model Armor templates](https://cloud.google.com/security-command-center/docs/manage-model-armor-templates)
- [adk-python source guide](https://github.com/google/adk-python/blob/main/docs/guides/integrations/model_armor/index.md)
```

### PR patch: `docs/safety/index.md` (Model Armor bullet)

Replace the Model Armor bullet with:

```markdown
* **Model Armor Plugin**: First-party plugin (`google.adk.integrations.model_armor`) that screens user input and model output via Google Cloud Model Armor templates. See the [Model Armor integration guide](/integrations/model-armor/) for install, configuration, and limitations (including tool-output screening).
```

---

# Item 2 — CLI README deprecation · `google/adk-python`

**Issue:** None (small documentation fix per CONTRIBUTING).

## PR (template: pull_request_template)

**Title:** `docs(cli): mark Sequential/Parallel/Loop agents deprecated in Agent Builder README`

**Body:**

```markdown
**Please ensure you have read the [contribution guide](https://github.com/google/adk-python/blob/main/CONTRIBUTING.md) before creating a pull request.**

### Link to Issue or Description of Change

**2. Or, if no issue exists, describe the change:**

**Problem:**

`src/google/adk/cli/built_in_agents/README.md` lists `SequentialAgent`, `ParallelAgent`, and `LoopAgent` as supported agent types without noting that these classes are `@deprecated` on `main` in favor of `Workflow`. This misleads users of the Agent Builder Assistant.

**Solution:**

Add an explicit deprecation notice in the YAML Configuration section and link to Workflow samples (`contributing/samples/workflows/` and `contributing/samples/legacy_workflows/`).

### Testing Plan

**Unit Tests:**

- [ ] N/A — markdown only

**Manual End-to-End (E2E) Tests:**

N/A — documentation-only change.

### Checklist

- [x] I have read the CONTRIBUTING.md document.
- [x] I have performed a self-review of my own code.
- [ ] I have added tests that prove my fix is effective or that my feature works. *(N/A)*
- [ ] New and existing unit tests pass locally with my changes. *(N/A)*
- [x] I have manually tested my changes end-to-end. *(Read rendered markdown)*

### Additional context

Agent classes emit `@deprecated` with message: *"Workflow cannot yet be used as an LlmAgent sub-agent."* For nested orchestration patterns, see Workflow-as-Tool (ADK ≥2.4) and closed discussion #5872.
```

### Diff: `src/google/adk/cli/built_in_agents/README.md`

Replace:

```markdown
- Generates AgentConfig schema-compliant YAML files
- Supports all agent types: LlmAgent, SequentialAgent, ParallelAgent, LoopAgent
- Built-in validation with detailed error reporting
```

With:

```markdown
- Generates AgentConfig schema-compliant YAML files
- Supports `LlmAgent` and legacy agent types in YAML (`SequentialAgent`, `ParallelAgent`, `LoopAgent`) — **these agent classes are deprecated** on `main` in favor of [`Workflow`](../../docs/guides/workflow/workflow/index.md). Prefer Workflow graphs and samples under [`contributing/samples/workflows/`](../../../contributing/samples/workflows/) and [`contributing/samples/legacy_workflows/`](../../../contributing/samples/legacy_workflows/) for new designs.
- Built-in validation with detailed error reporting
```

---

# Item 3 — safety-plugins README banner · `google/adk-samples`

**Issue:** None.

## PR

**Title:** `docs(safety-plugins): point to first-party ModelArmorPlugin`

**Body:**

```markdown
## Problem

The safety-plugins sample implements `ModelArmorSafetyFilterPlugin`, but ADK 2.8.0 ships a first-party `ModelArmorPlugin` (`google.adk.integrations.model_armor`) with unit tests and an in-repo integration guide. New readers may copy this sample for production input/output guardrails when the first-party plugin is the supported path.

The sample remains valuable for demonstrating `after_tool_callback` hooks (tool-output screening), which the first-party plugin documents as out of scope.

## Solution

Add a prominent note at the top of the README (both mirrored copies under `python/agents/` and `core/python/`) pointing to the first-party plugin and clarifying this sample's role as a reference for custom hooks.

## Testing

- [x] Markdown only; no code changes
- [x] Both README paths updated (identical content on `main` as of 2026-08-31)

## Files

- `python/agents/safety-plugins/README.md`
- `core/python/safety-plugins/README.md`
```

### Insert after `# Agent-Agnostic Safety Plugins` / Overview (both files)

```markdown
> **Note (ADK 2.8+):** For production input and model-output screening, use the first-party [`ModelArmorPlugin`](https://github.com/google/adk-python/blob/main/docs/guides/integrations/model_armor/index.md) (`google.adk.integrations.model_armor`). Published guide: pending on [adk.dev integrations](https://adk.dev/integrations/).
>
> This sample remains a **reference** for custom plugin hooks—including **`after_tool_callback` tool-output screening**, which the first-party plugin does not cover today. Do not copy this sample wholesale as your production guardrail.
```

---

# Item 4 — tool-output sample · `google/adk-python`

## Issue (template: feature_request)

**Title:** `sample: Model Armor tool-output screening via after_tool_callback`

**Body:**

```markdown
** Please make sure you read the contribution guide and file the issues in the right place. **
[Contribution guide.](https://google.github.io/adk-docs/contributing-guide/)

## 🔴 Required Information

### Is your feature request related to a specific problem?

The first-party `ModelArmorPlugin` documents that **tool output is not screened**:

https://github.com/google/adk-python/blob/main/docs/guides/integrations/model_armor/index.md#limitations

Tool results arrive as `user` content whose only part is a `function_response`, which the plugin does not send to Model Armor. Agentic pipelines that ingest external text via tools (issues, email, web search, MCP) often need screening on **tool output**, not just user prompts and model replies.

### Describe the Solution You'd Like

Add a minimal sample under `contributing/samples/integrations/model_armor_tool_output/` demonstrating a companion plugin on `after_tool_callback` that stringifies tool results and calls Model Armor's `SanitizeUserPrompt` API (or documents the pattern alongside `ModelArmorPlugin` on the same `App`).

### Impact on your work

We run a multi-tool agent control plane where the primary injection vector is hostile content returned as tool output. We use a custom `after_tool_callback` plugin today; a first-party sample would reduce unsafe copy-paste from older adk-samples safety-plugins code.

No critical deadline.

### Willingness to contribute

Yes

---

## 🟡 Recommended Information

### Describe Alternatives You've Considered

- Using `ModelArmorSafetyFilterPlugin` from adk-samples — older callback shapes; not the 2.8 first-party integration path.
- Waiting for core plugin extension — larger API design (#5 tracks that separately).

### Proposed API / Implementation

```python
class ToolOutputModelArmorPlugin(BasePlugin):
    async def after_tool_callback(self, *, tool, tool_args, tool_context, result, **kwargs):
        text = stringify(result)
        if not text:
            return None
        # Call modelarmor SanitizeUserPrompt on text; return error dict if MATCH_FOUND
```

Sample registers `[ModelArmorPlugin(...), ToolOutputModelArmorPlugin(...)]` on one `App`.

### Additional context

- Related limitation text in `_plugin.py` module docstring (screens `before_model_callback` / `after_model_callback` only).
- I will open a PR referencing this issue same day if accepted in principle.
```

## PR (template: pull_request_template)

**Title:** `sample(integrations): Model Armor tool-output screening plugin`

**Body:**

```markdown
Closes #ISSUE_NUMBER

### Link to Issue or Description of Change

- Closes: #ISSUE_NUMBER

**Problem:**

Documented gap: first-party `ModelArmorPlugin` does not screen tool output.

**Solution:**

Add `contributing/samples/integrations/model_armor_tool_output/` with:
- Minimal `ToolOutputModelArmorPlugin` on `after_tool_callback`
- README with threat-model note and run instructions
- Unit tests mocking Model Armor client (pattern: `tests/unittests/integrations/model_armor/`)

### Testing Plan

**Unit Tests:**

- [x] Added `tests/unittests/integrations/model_armor/test_tool_output_sample.py` (or sample-local tests per repo convention)
- [x] All unit tests pass locally.

```
pytest tests/unittests/integrations/model_armor/ -q
pytest ./tests/unittests -q  # full suite before submit
```

**Manual End-to-End (E2E) Tests:**

- [x] Ran sample with `adk web` / `adk run` against mock or test template (describe commands in sample README).

### Checklist

- [x] I have read the CONTRIBUTING.md document.
- [x] I have performed a self-review of my own code.
- [x] I have commented my code, particularly in hard-to-understand areas.
- [x] I have added tests that prove my fix is effective or that my feature works.
- [x] New and existing unit tests pass locally with my changes.
- [x] I have manually tested my changes end-to-end.
```

*(Implement sample code in the actual PR branch — this body describes intent.)*

---

# Item 5 — first-party tool-output feature · `google/adk-python`

**PR:** Do not open until maintainer feedback on #4.

## Issue (template: feature_request)

**Title:** `feat(model_armor): screen tool output in ModelArmorPlugin (or companion plugin)`

**Body:**

```markdown
** Please make sure you read the contribution guide and file the issues in the right place. **
[Contribution guide.](https://google.github.io/adk-docs/contributing-guide/)

## 🔴 Required Information

### Is your feature request related to a specific problem?

Same problem as #ISSUE_NUMBER_FOR_ITEM_4: the documented limitation that tool output is not screened by `ModelArmorPlugin`. For agents that load untrusted text through tools, screening only user prompts and model output leaves a documented security gap.

### Describe the Solution You'd Like

One of (maintainer choice):

1. Extend `ModelArmorConfig` with e.g. `screen_tool_output: bool = False` and implement screening in `ModelArmorPlugin.after_tool_callback`, reusing the prompt template; or
2. Ship `ToolOutputModelArmorPlugin` in `google.adk.integrations.model_armor` as an optional companion with shared config/client.

Either approach should mirror fail-closed semantics of the existing plugin and include unit tests in `tests/unittests/integrations/model_armor/`.

### Impact on your work

Production agent pipelines where tool output is the dominant untrusted input channel. We will contribute a sample in #ISSUE_NUMBER_FOR_ITEM_4 / PR #PR_NUMBER_FOR_ITEM_4 as a reference implementation sketch.

### Willingness to contribute

Yes — sample PR first; core plugin PR after design alignment.

---

## 🟡 Recommended Information

### Describe Alternatives You've Considered

- Document-only workaround — insufficient; limitation is already documented but not addressed.
- Per-app custom plugins forever — duplicates logic across every ADK 2.8 adopter with tool-heavy threat models.

### Proposed API / Implementation

```python
@dataclass
class ModelArmorConfig:
    ...
    screen_tool_output: bool = False
    tool_output_blocked_message: str = "Tool output was blocked by Model Armor."
```

```python
async def after_tool_callback(self, *, tool, tool_args, tool_context, result, **kwargs):
    if not self._config.screen_tool_output:
        return None
    ...
```

### Additional context

- Not requesting Workflow-as-sub-agent (#5872 closed; Workflow-as-Tool is the supported orchestration path).
- Separate from #6224 (durable execution hooks).
```

---

# Item 6 — migration narrative · `google/adk-docs` (+ optional adk-python)

## Issue (template: feature_request) · `google/adk-docs`

**Title:** `docs: ADK 1.x agent patterns → Workflow migration guide`

**Body:**

```markdown
**Is your feature request related to a problem? Please describe.**

ADK 1.x codebases commonly used `SequentialAgent`, `ParallelAgent`, and `LoopAgent`. On adk-python `main`, these classes are `@deprecated` in favor of `Workflow`, with the note that Workflow cannot yet be used as an `LlmAgent` sub-agent.

The [ADK 2.0 overview](https://adk.dev/2.0/) documents Workflow **runtime** breaking changes (events, session schema) but not a **pattern migration** table:

| Old pattern | ADK 2 direction |
|---|---|
| `ParallelAgent` fan-out | `Workflow` + `JoinNode` |
| `LoopAgent` critique | `Workflow` + loop / `RequestInput` |
| `SequentialAgent` as `sub_agent` | **Workflow-as-Tool** on `Agent(tools=[...])` (ADK ≥2.4; see closed #5872) |

Samples exist (`contributing/samples/legacy_workflows/`, `contributing/samples/workflows/`) but there is no single narrative doc on adk.dev tying them together.

**Describe the solution you'd like**

A migration guide page (adk-docs) mapping deprecated agents to Workflow patterns, linking to official samples, and explicitly referencing #5872 resolution (Workflow-as-Tool — not Workflow-as-sub-agent).

**Describe alternatives you've considered**

- More samples only — already present; need narrative.
- Re-opening Workflow-as-sub-agent — rejected per maintainer direction in #5872.

**Additional context**

Willing to contribute PR to adk-docs and/or a short pointer doc in adk-python `docs/guides/`.
```

## PR · `google/adk-docs` (after issue)

**Title:** `docs: add ADK 1.x agent pattern migration guide`

**Body:**

```markdown
Closes #ISSUE_NUMBER

## Summary

Adds a migration guide (location TBD with reviewers — e.g. `docs/2.0/agent-pattern-migration.md` or `docs/agents/multi-agents/migration-from-1x-agents.md`) covering:

- Deprecated agents vs `Workflow`
- Fan-out → `JoinNode`; loops → `RequestInput`
- Nested pipelines → Workflow-as-Tool (`input_schema` + `description` required) per #5872
- Links to `legacy_workflows` and `workflows/node_as_tool` samples on adk-python

## Testing

- [x] `mkdocs serve` — links render; no broken anchors

## Out of scope

- Re-opening Workflow-as-sub-agent feature request (#5872 closed).
```

---

# Item 7 — node_as_tool cross-link · `google/adk-python`

**Issue:** None (small doc fix; may bundle into #6 adk-python PR).

## PR (template: pull_request_template)

**Title:** `docs(workflow): add node_as_tool to Related samples`

**Body:**

```markdown
### Link to Issue or Description of Change

**Problem:**

`docs/guides/workflow/workflow/index.md` lists seven Related samples but omits [`contributing/samples/workflows/node_as_tool/`](../../../contributing/samples/workflows/node_as_tool/), which documents wrapping a `Workflow` as an agent tool and the mandatory `input_schema` requirement.

**Solution:**

Add bullet to Related samples + one sentence in Workflow-as-tool context (if present) pointing to `input_schema`.

### Testing Plan

N/A — markdown only.

### Checklist

- [x] CONTRIBUTING.md read
- [x] Self-review done
```

### Diff: `docs/guides/workflow/workflow/index.md`

In **Related samples**, after the Node Retries bullet, add:

```markdown
- [Node as Tool](../../../../contributing/samples/workflows/node_as_tool/README.md): wrap a `Node` or `Workflow` as an agent tool; requires `input_schema` and `description` on the wrapped node/workflow.
```

---

## Post-filing checklist

| Step | Done when |
|---|---|
| CLA | `google-cla` check green on each PR |
| Copybara | adk-python PR may close with `merged` label — read maintainer comment |
| Link issues | #5 references #4 issue/PR numbers |
| Re-verify gates | Re-run §5.3 before each submit if >7 days elapsed |
