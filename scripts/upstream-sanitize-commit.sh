#!/usr/bin/env bash
# Rebuild HEAD without Co-authored-by: Cursor if a hook injected it.
# Usage: upstream-sanitize-commit.sh "commit message line"
set -euo pipefail

MSG="${1:?usage: upstream-sanitize-commit.sh \"commit message\"}"

if git log -1 --format=%B | grep -qi 'Co-authored-by:.*Cursor'; then
  TREE=$(git write-tree)
  PARENT=$(git rev-parse HEAD^)
  NEW=$(printf '%s\n' "$MSG" | git commit-tree "$TREE" -p "$PARENT" -S -F -)
  git reset --hard "$NEW"
  echo "Sanitized commit: removed Cursor co-author trailer"
else
  echo "Commit clean: no Cursor co-author trailer"
fi

git log -1 --format=full
