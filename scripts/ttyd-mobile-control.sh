#!/usr/bin/env bash
set -euo pipefail

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

host="${TTYD_MOBILE_HOST:-tailscale}"

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

export TTYD_MOBILE_HOST="$host"

exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/ttyd-mobile-control.py"
