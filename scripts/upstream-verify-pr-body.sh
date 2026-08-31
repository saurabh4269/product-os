#!/usr/bin/env bash
# Verify PR body has no Cursor footer; optionally rewrite from a clean file.
# Usage:
#   upstream-verify-pr-body.sh google/adk-python 6962
#   upstream-verify-pr-body.sh google/adk-python 6962 /tmp/pr-body-clean.md
set -euo pipefail

REPO="${1:?usage: upstream-verify-pr-body.sh REPO PR [BODY_FILE]}"
PR="${2:?usage: upstream-verify-pr-body.sh REPO PR [BODY_FILE]}"
BODY_FILE="${3:-}"

BODY=$(gh pr view "$PR" --repo "$REPO" --json body --jq '.body')

if printf '%s' "$BODY" | grep -qi 'cursor'; then
  echo "FAIL: PR #$PR body mentions Cursor"
  printf '%s\n' "$BODY" | tail -5
  if [[ -n "$BODY_FILE" && -f "$BODY_FILE" ]]; then
    gh pr edit "$PR" --repo "$REPO" --body-file "$BODY_FILE"
    echo "Rewrote PR body from $BODY_FILE"
  else
    echo "Re-run with a clean body file to fix: upstream-verify-pr-body.sh $REPO $PR /path/to/body.md"
    exit 1
  fi
else
  echo "OK: PR #$PR body has no Cursor mention"
fi
