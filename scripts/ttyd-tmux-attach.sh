#!/usr/bin/env bash
set -euo pipefail

session="${TTYD_TMUX_SESSION:-remote}"

if ! tmux has-session -t "$session" 2>/dev/null; then
  printf "tmux session '%s' does not exist.\n\n" "$session"
  printf "Create it from a local terminal first:\n\n"
  printf "  tmux new -s %q\n\n" "$session"
  printf "Then reload this browser tab.\n"
  sleep "${TTYD_MISSING_SESSION_SLEEP:-30}"
  exit 1
fi

exec tmux attach-session -t "$session"
