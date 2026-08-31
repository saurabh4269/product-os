# Upstream contributions log

Record of Product OS research contributions filed to Google ADK repositories (**2026-08-31**).

| Field | Value |
|---|---|
| GitHub user | [saurabh4269](https://github.com/saurabh4269) |
| Forks | `saurabh4269/adk-python`, `saurabh4269/adk-docs`, `saurabh4269/adk-samples` |
| Local clones | `/tmp/upstream-adk/{adk-python,adk-docs,adk-samples}` |
| Drafts | [`DRAFTS.md`](DRAFTS.md) |
| Filing rules | [`FILING_PROTOCOL.md`](FILING_PROTOCOL.md) |
| Research source | [`GOOGLE_OPEN_SOURCE_LEARNINGS.md`](../GOOGLE_OPEN_SOURCE_LEARNINGS.md) |

**Status snapshot:** all items below were **open** as of 2026-08-31.

---

## Summary

| # | Repo | Topic | Issue | PR | Notes |
|---|---|---|---|---|---|
| 1 | adk-docs | Model Armor integration page | (comment on [#2179](https://github.com/google/adk-docs/issues/2179)) | [#2184](https://github.com/google/adk-docs/pull/2184) | No new issue; #2179 tracks v2.7.1→v2.8.0 doc gaps |
| 2 | adk-python | CLI README deprecation notice | — | [#6962](https://github.com/google/adk-python/pull/6962) | Doc-only |
| 3 | adk-samples | safety-plugins → first-party plugin | — | [#2581](https://github.com/google/adk-samples/pull/2581) | Both README copies |
| 4 | adk-python | Model Armor tool-output sample | [#6964](https://github.com/google/adk-python/issues/6964) | [#6965](https://github.com/google/adk-python/pull/6965) | PR closes #6964 |
| 5 | adk-python | First-party tool-output screening | [#6966](https://github.com/google/adk-python/issues/6966) | — | Issue only; wait on #6965 feedback |
| 6 | adk-docs | 1.x agent pattern → Workflow migration | [#2185](https://github.com/google/adk-docs/issues/2185) | [#2186](https://github.com/google/adk-docs/pull/2186) | PR closes #2185 |
| 7 | adk-python | `node_as_tool` in Related samples | — | [#6963](https://github.com/google/adk-python/pull/6963) | Doc-only |

**Filing order used:** #2 → #3 → #7 → #1 → #4 (issue + PR) → #5 (issue) → #6 (issue + PR).

---

## Item 1 — Model Armor integration page

**Repo:** [google/adk-docs](https://github.com/google/adk-docs)

| Type | # | URL |
|---|---|---|
| Existing issue (comment) | 2179 | https://github.com/google/adk-docs/issues/2179 |
| Comment | — | https://github.com/google/adk-docs/issues/2179#issuecomment-5477226210 |
| PR | 2184 | https://github.com/google/adk-docs/pull/2184 |

**What:** Add `docs/integrations/model-armor.md` on adk.dev (install, config, limitations including tool-output gap), cross-link from Safety page.

**Branch:** `docs/integrations-model-armor`

---

## Item 2 — CLI README deprecation

**Repo:** [google/adk-python](https://github.com/google/adk-python)

| Type | # | URL |
|---|---|---|
| PR | 6962 | https://github.com/google/adk-python/pull/6962 |

**What:** Deprecation notice in `src/google/adk/cli/built_in_agents/README.md` for `SequentialAgent` / `ParallelAgent` / `LoopAgent`; link to Workflow samples.

**Branch:** `docs/cli-builtin-agents-deprecation-notice`

**Follow-up:** Link depth fix (5× `../` from `built_in_agents/`) pushed on same PR.

---

## Item 3 — safety-plugins README banner

**Repo:** [google/adk-samples](https://github.com/google/adk-samples)

| Type | # | URL |
|---|---|---|
| PR | 2581 | https://github.com/google/adk-samples/pull/2581 |

**What:** Banner on both safety-plugins READMEs pointing to first-party `ModelArmorPlugin`; sample kept as custom-hook reference.

**Files:** `python/agents/safety-plugins/README.md`, `core/python/safety-plugins/README.md`

**Branch:** `docs/safety-plugins-first-party-pointer`

---

## Item 4 — Model Armor tool-output sample

**Repo:** [google/adk-python](https://github.com/google/adk-python)

| Type | # | URL |
|---|---|---|
| Issue | 6964 | https://github.com/google/adk-python/issues/6964 |
| PR | 6965 | https://github.com/google/adk-python/pull/6965 |

**What:** Sample `contributing/samples/integrations/model_armor_tool_output/` with `ToolOutputModelArmorPlugin` on `after_tool_callback`; unit tests in `tests/unittests/integrations/model_armor/test_tool_output_plugin.py`.

**Branch:** `sample/model-armor-tool-output`

---

## Item 5 — First-party tool-output screening

**Repo:** [google/adk-python](https://github.com/google/adk-python)

| Type | # | URL |
|---|---|---|
| Issue | 6966 | https://github.com/google/adk-python/issues/6966 |

**What:** Feature request for core `ModelArmorPlugin` extension or shipped companion in `google.adk.integrations.model_armor`. References #6964 and #6965. No core PR filed yet.

---

## Item 6 — Agent pattern migration guide

**Repo:** [google/adk-docs](https://github.com/google/adk-docs)

| Type | # | URL |
|---|---|---|
| Issue | 2185 | https://github.com/google/adk-docs/issues/2185 |
| PR | 2186 | https://github.com/google/adk-docs/pull/2186 |

**What:** `docs/2.0/agent-pattern-migration.md` mapping deprecated workflow agents to `Workflow`, `JoinNode`, loops, and Workflow-as-Tool per [adk-python#5872](https://github.com/google/adk-python/issues/5872). Nav entry in `mkdocs.yml`; cross-link from `docs/2.0/index.md`.

**Branch:** `docs/agent-pattern-migration`

---

## Item 7 — node_as_tool Related samples link

**Repo:** [google/adk-python](https://github.com/google/adk-python)

| Type | # | URL |
|---|---|---|
| PR | 6963 | https://github.com/google/adk-python/pull/6963 |

**What:** Add `contributing/samples/workflows/node_as_tool/` to Related samples in `docs/guides/workflow/workflow/index.md`.

**Branch:** `docs/workflow-node-as-tool-sample-link`

---

## Upstream issues referenced (not filed by us)

| Repo | # | Why cited |
|---|---|---|
| adk-docs | [2179](https://github.com/google/adk-docs/issues/2179) | v2.7.1→v2.8.0 doc tracker; Model Armor comment landed here |
| adk-python | [5872](https://github.com/google/adk-python/issues/5872) | Workflow-as-Tool resolution (closed); cited in #6 |
| adk-python | [5581](https://github.com/google/adk-python/discussions/5581) | Native Workflow-as-sub-agent discussion; cited in #6 |

---

## Refresh status

```bash
# Quick open/closed check
for spec in \
  "google/adk-python#6962" "google/adk-python#6963" "google/adk-python#6964" \
  "google/adk-python#6965" "google/adk-python#6966" \
  "google/adk-samples#2581" \
  "google/adk-docs#2184" "google/adk-docs#2185" "google/adk-docs#2186"; do
  repo="${spec%%#*}" num="${spec##*#}"
  gh pr view "$num" --repo "$repo" --json state,title --jq '"PR \(.state): '"$spec"' — \(.title)"' 2>/dev/null \
    || gh issue view "$num" --repo "$repo" --json state,title --jq '"Issue \(.state): '"$spec"' — \(.title)"'
done
```

Update this file when any PR merges or new follow-ups are filed.
