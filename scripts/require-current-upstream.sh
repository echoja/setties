#!/usr/bin/env bash
set -euo pipefail

# Intentionally fail closed: if the network fetch fails, commits are blocked.
# This keeps local commits from being made on top of stale upstream state.

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  exit 0
fi

branch="$(git symbolic-ref --quiet --short HEAD || true)"
if [[ -z "$branch" ]]; then
  echo "Detached HEAD; skipping upstream freshness check."
  exit 0
fi

upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
if [[ -z "$upstream" ]]; then
  echo "No upstream configured for $branch; skipping upstream freshness check."
  exit 0
fi

remote="$(git config --get "branch.${branch}.remote" || true)"
if [[ -z "$remote" ]]; then
  echo "No remote configured for $branch; skipping upstream freshness check."
  exit 0
fi

echo "Fetching $remote before commit..."
if ! git fetch --prune "$remote"; then
  echo "Failed to fetch $remote; commit blocked because upstream freshness cannot be verified." >&2
  exit 1
fi

read -r ahead behind < <(git rev-list --left-right --count HEAD..."@{u}")

if (( behind > 0 )); then
  echo "Commit blocked: $branch is behind $upstream by $behind commit(s)." >&2
  if (( ahead > 0 )); then
    echo "Local branch also has $ahead unpushed commit(s); pull/rebase before committing." >&2
  else
    echo "Pull the latest changes before committing." >&2
  fi
  exit 1
fi

exit 0
