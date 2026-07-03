#!/bin/bash
set -euo pipefail

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

if ! command -v brew >/dev/null 2>&1; then
  log "brew not found"
  exit 1
fi

export HOMEBREW_NO_ENV_HINTS=1

log "running brew update..."
brew update

log "running brew upgrade..."
brew upgrade --greedy-auto-updates

log "upgrade complete"

if command -v terminal-notifier >/dev/null 2>&1; then
  terminal-notifier \
    -title "Homebrew" \
    -message "Homebrew upgrade complete" \
    -group "com.echoja.brew-upgrade"
fi
