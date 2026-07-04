#!/usr/bin/env bash
set -euo pipefail

port="${TTYD_PORT:-7681}"
https_port="${TAILSCALE_SERVE_HTTPS_PORT:-443}"
target="${TAILSCALE_SERVE_TARGET:-localhost:${port}}"
app_cli="/Applications/Tailscale.app/Contents/MacOS/Tailscale"

if [[ -n "${TAILSCALE_BIN:-}" ]]; then
  tailscale_bin="$TAILSCALE_BIN"
elif command -v tailscale >/dev/null 2>&1; then
  tailscale_bin="$(command -v tailscale)"
else
  tailscale_bin="$app_cli"
fi

if [[ ! -x "$tailscale_bin" ]]; then
  echo "Tailscale CLI not found." >&2
  echo "Expected either 'tailscale' on PATH or $app_cli." >&2
  exit 127
fi

if ! "$tailscale_bin" status >/dev/null 2>&1; then
  echo "Tailscale is not connected yet; will retry later." >&2
  exit 0
fi

exec "$tailscale_bin" serve --bg --yes --https="$https_port" "$target"
