#!/usr/bin/env bash
set -euo pipefail

# Git runs post-rewrite for both rebase and amend. Only rebase represents the
# pull/rebase path where we want automatic settings verification.
if [[ "${PRE_COMMIT_HOOK_STAGE:-}" == "post-rewrite" && "${1:-}" != "rebase" ]]; then
  exit 0
fi

repo_dir="$(git rev-parse --show-toplevel)"
cd "$repo_dir"

./v
