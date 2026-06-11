#!/bin/bash
input=$(cat)

DIR=$(echo "$input" | jq -r '.workspace.current_dir')

CYAN='\033[36m'
YELLOW='\033[33m'
RED='\033[31m'
GREEN='\033[32m'
GREY='\033[90m'
RESET='\033[0m'

GIT_INFO=""
GIT_ROOT=$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null)
if [ -n "$GIT_ROOT" ]; then
  DIR="$GIT_ROOT"
  branch=$(git -C "$GIT_ROOT" branch --show-current 2>/dev/null)
  [ -z "$branch" ] && branch=$(git -C "$GIT_ROOT" rev-parse --short HEAD 2>/dev/null)

  status=$(git -C "$GIT_ROOT" status --porcelain=v1 --branch 2>/dev/null)

  # branch.ab line: '## br...origin/br [ahead 2, behind 1]'
  ahead=$(echo "$status" | head -1 | grep -oE 'ahead [0-9]+' | awk '{print $2}')
  behind=$(echo "$status" | head -1 | grep -oE 'behind [0-9]+' | awk '{print $2}')

  body=$(echo "$status" | tail -n +2)
  untracked=$(echo "$body" | grep -c '^??')
  unstaged=$(echo "$body" | grep -cE '^.[MD]')
  staged=$(echo "$body" | grep -cE '^[MADRC]')
  conflict=$(echo "$body" | grep -cE '^(UU|AA|DD|AU|UA|DU|UD)')
  stash=$(git -C "$GIT_ROOT" stash list 2>/dev/null | wc -l | tr -d ' ')

  flags=""
  [ "$untracked" -gt 0 ] && flags+=" ${GREY}?${untracked}${YELLOW}"
  [ "$unstaged" -gt 0 ] && flags+=" *${unstaged}"
  [ "$staged" -gt 0 ] && flags+=" ${GREEN}+${staged}${YELLOW}"
  [ "$conflict" -gt 0 ] && flags+=" ${RED}!${conflict}${YELLOW}"
  [ -n "$ahead" ] && flags+=" ↑${ahead}"
  [ -n "$behind" ] && flags+=" ↓${behind}"
  [ "$stash" -gt 0 ] && flags+=" ~${stash}"

  GIT_INFO=" | ${YELLOW}${branch}${flags}${RESET}"
fi

# rate limit windows: only present for Pro/Max after the first API response
RL_INFO=""
five_reset=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
seven_reset=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')
five_used=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
seven_used=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
fmt_reset() {
  if [ "$(date -r "$1" +%Y%m%d)" = "$(date +%Y%m%d)" ]; then
    date -r "$1" +%H:%M
  else
    date -r "$1" +'%m/%d %H:%M'
  fi
}
fmt_used() { # used %, color-coded
  local used=${1%%.*}
  local color="$GREEN"
  [ "$used" -ge 50 ] && color="$YELLOW"
  [ "$used" -ge 80 ] && color="$RED"
  printf '%b%s%%%b' "$color" "$used" "$GREY"
}
rl_parts=""
if [ -n "$five_reset" ]; then
  rl_parts+="5h "
  [ -n "$five_used" ] && rl_parts+="$(fmt_used "$five_used") "
  rl_parts+="↻$(fmt_reset "$five_reset")"
fi
if [ -n "$seven_reset" ]; then
  [ -n "$rl_parts" ] && rl_parts+="  "
  rl_parts+="7d "
  [ -n "$seven_used" ] && rl_parts+="$(fmt_used "$seven_used") "
  rl_parts+="↻$(fmt_reset "$seven_reset")"
fi
[ -n "$rl_parts" ] && RL_INFO=" | ${GREY}${rl_parts}${RESET}"

echo -e "${CYAN}${DIR##*/}${RESET}${GIT_INFO}${RL_INFO}"
