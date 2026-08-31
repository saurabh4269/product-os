# Upstream filing protocol

Binding rules for every issue and PR to `google/adk-python`, `google/adk-docs`, and `google/adk-samples`. Read before filing. Parent: [`DRAFTS.md`](DRAFTS.md) · [`GOOGLE_OPEN_SOURCE_LEARNINGS.md`](../GOOGLE_OPEN_SOURCE_LEARNINGS.md).

---

## 1. Approval gate

- **Never push, fork, or publish** until the user approves the exact title, body, and diff for that item.
- One item at a time in filing order: **#2 → #3 → #7 → #1 → #4 → #5 → #6**.

---

## 2. No Cursor / AI attribution

| Surface | Rule |
|---|---|
| Commit messages | Product text only. No `Co-authored-by: Cursor`, no tool names. |
| PR / issue bodies | No "Made with Cursor", no links to cursor.com, no agent names. |
| Hooks | Local commit hooks may inject `Co-authored-by: Cursor`. **Always inspect** `git log -1 --format=full` before push. If present, rebuild the commit without the trailer (see §5). |

---

## 3. PR and issue body format

**Do not paste template boilerplate.** The repo template is a form guide, not body content.

| Do not include | Do include |
|---|---|
| `Please ensure you have read the contribution guide...` | `### Link to Issue or Description of Change` |
| `**1. Link to an existing issue**` / `**2. Or, if no issue exists**` | `**Problem:**` and `**Solution:**` |
| Italic placeholder hints from the template | Filled checklist items (adapt like [#6959](https://github.com/google/adk-python/pull/6959)) |

**Typography:** No em dashes (`—`) or en dashes (`–`). Use commas, periods, colons, or hyphen-with-spaces.

**After `gh pr create`:** Immediately run `gh pr view … --json body` and confirm the body does **not** end with `Made with [Cursor](https://cursor.com)`. If it does, `gh pr edit` to remove it before telling the user the PR is done.

---

## 4. GPG-signed commits

- Local config should have `commit.gpgsign=true` and a valid `user.signingkey`.
- Every upstream commit uses `git commit -S`.
- Before push: confirm GitHub will show **Verified** (`git log -1 --show-signature`).
- Strip AI co-author trailers before push (§5).

---

## 5. Strip injected `Co-authored-by: Cursor`

If `git log -1 --format=%B` contains `Co-authored-by: Cursor`:

```bash
TREE=$(git write-tree)
PARENT=$(git rev-parse HEAD^)
MSG='your commit message here'
NEW=$(printf '%s\n' "$MSG" | git commit-tree "$TREE" -p "$PARENT" -S -F -)
git reset --hard "$NEW"
```

Verify: `git log -1 --format=full` must show only the human author.

---

## 6. Relative markdown links

Before push, resolve every new relative link from the **file being edited**, not from repo root.

```bash
python3 - <<'PY'
import os
readme = "src/google/adk/cli/built_in_agents/README.md"  # path under repo root
for rel in ["../../../../../docs/guides/workflow/workflow/index.md"]:
    print(os.path.normpath(os.path.join(os.path.dirname(readme), rel)))
PY
```

Confirm each resolved path exists on `main` (`gh api repos/google/adk-python/contents/...` or directory listing returns an array).

Common mistake: too few `../` segments from deep paths under `src/google/adk/...` (need five levels to repo root from `built_in_agents/`).

---

## 7. Post-create verification (every PR)

Run before reporting success to the user:

```bash
PR=6962  # replace
REPO=google/adk-python
gh pr checks "$PR" --repo "$REPO"
gh pr view "$PR" --repo "$REPO" --json body,commits --jq '{body_has_cursor: (.body | test("cursor"; "i")), commits: [.commits[].messageHeadline]}'
gh pr diff "$PR" --repo "$REPO"
```

| Check | Pass when |
|---|---|
| `cla/google` | Success |
| PR body | No Cursor string |
| Commits | GPG verified on GitHub |
| Diff | Matches approved text; links resolve |

---

## 8. Item-specific reminders

| # | Reminder |
|---|---|
| 1 | Do **not** open a new issue. Comment on [adk-docs #2179](https://github.com/google/adk-docs/issues/2179), then PR referencing that issue. |
| 2–3, 7 | PR only; no issue unless maintainer asks. |
| 4 | Issue + PR same day; implement sample code, not body-only. |
| 5 | Issue only after #4 is filed; link #4 issue/PR numbers. |

---

## 9. Safe PR create (optional)

Prefer `--body-file` from a local file you control, then verify and edit:

```bash
gh pr create --repo google/adk-python \
  --head saurabh4269:your-branch \
  --base main \
  --title "your title" \
  --body-file /tmp/pr-body.md

# mandatory follow-up
gh pr view <number> --repo google/adk-python --json body --jq '.body' | tail -3
```

If the footer appeared, `gh pr edit <number> --repo google/adk-python --body-file /tmp/pr-body-clean.md`.
