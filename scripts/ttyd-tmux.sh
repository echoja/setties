#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export LANG="${LANG:-ko_KR.UTF-8}"
export LC_CTYPE="${LC_CTYPE:-ko_KR.UTF-8}"
export LC_ALL="${LC_ALL:-ko_KR.UTF-8}"

session="${TTYD_TMUX_SESSION:-remote}"
host="${TTYD_HOST:-127.0.0.1}"
port="${TTYD_PORT:-7681}"
ttyd_bin="${TTYD_BIN:-ttyd}"
font_family="${TTYD_FONT_FAMILY:-Menlo, Monaco, 'Apple SD Gothic Neo', 'Apple Color Emoji', monospace}"
app_tailscale_bin="/Applications/Tailscale.app/Contents/MacOS/Tailscale"

tailscale_bin() {
  if [[ -n "${TAILSCALE_BIN:-}" ]]; then
    printf "%s\n" "$TAILSCALE_BIN"
  elif command -v tailscale >/dev/null 2>&1; then
    command -v tailscale
  elif [[ -x "$app_tailscale_bin" ]]; then
    printf "%s\n" "$app_tailscale_bin"
  else
    return 1
  fi
}

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

if [[ "$host" == "tailscale" ]]; then
  ts_bin="$(tailscale_bin)" || {
    echo "Tailscale CLI not found." >&2
    echo "Expected either 'tailscale' on PATH or $app_tailscale_bin." >&2
    exit 127
  }
  host="$("$ts_bin" ip -4 2>/dev/null | sed -n '1p' || true)"
  if [[ -z "$host" ]]; then
    echo "Could not resolve this machine's Tailscale IPv4 address." >&2
    exit 1
  fi
fi

args=(
  -i "$host"
  -p "$port"
  -W
  -T xterm-256color
  -t rendererType=canvas
  -t "fontFamily=$font_family"
)

if [[ -n "${TTYD_CREDENTIAL:-}" ]]; then
  args+=(-c "$TTYD_CREDENTIAL")
fi

exec "$ttyd_bin" "${args[@]}" "$repo_dir/scripts/ttyd-tmux-attach.sh"
