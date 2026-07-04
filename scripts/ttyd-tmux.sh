#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

session="${TTYD_TMUX_SESSION:-remote}"
host="${TTYD_HOST:-127.0.0.1}"
port="${TTYD_PORT:-7681}"
ttyd_bin="${TTYD_BIN:-ttyd}"

if ! command -v "$ttyd_bin" >/dev/null 2>&1; then
  echo "ttyd is not installed or not on PATH." >&2
  echo "Install it with: brew install ttyd" >&2
  exit 127
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is not installed or not on PATH." >&2
  echo "Install it with: brew install tmux" >&2
  exit 127
fi

args=(
  -i "$host"
  -p "$port"
  -W
)

if [[ -n "${TTYD_CREDENTIAL:-}" ]]; then
  args+=(-c "$TTYD_CREDENTIAL")
fi

exec "$ttyd_bin" "${args[@]}" "$repo_dir/scripts/ttyd-tmux-attach.sh"
