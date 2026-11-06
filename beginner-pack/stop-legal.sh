#!/usr/bin/env bash
# Stop the Court of Inquiry application. Safe: nothing is deleted.
set -u

say()  { printf '%s\n' "$*"; }
pause() { if [ -t 0 ]; then printf '%s' "$1"; read -r _; fi; }
fail() {
  printf '\n!! PROBLEM: %s\n' "$1"
  [ -n "${2:-}" ] && printf '%s\n' "$2"
  pause "Press Enter to close this window..."
  exit 1
}

here="$(dirname "$(readlink -f "$0")")"
d="$here"
while [ ! -f "$d/compose.yml" ] && [ "$d" != "/" ]; do d="$(dirname "$d")"; done
[ -f "$d/compose.yml" ] || fail "Could not find the project folder (compose.yml)."
cd "$d" || fail "Cannot open the project folder: $d"

if command -v docker >/dev/null 2>&1; then DOCKER=docker
elif command -v docker.exe >/dev/null 2>&1; then DOCKER=docker.exe
else fail "Docker is not installed on this computer."
fi

if $DOCKER compose version >/dev/null 2>&1; then DC="$DOCKER compose"
elif [ -x "$HOME/.docker/cli-plugins/docker-compose" ]; then DC="$HOME/.docker/cli-plugins/docker-compose"
else fail "Docker Compose is missing (see setup.md section 5)."
fi

say "Stopping the application..."
$DC -f compose.yml down >/dev/null 2>&1 || $DC -f compose.yml down || fail "Stopping reported an error (see above)."

say ""
say "  Stopped. Nothing was deleted:"
say "    - your cases       are in backend/uploads"
say "    - law documents    are in data/"
say "    - the AI model     is in offline/ollama"
say "  Start again with:  bash start-legal.sh"
pause "Press Enter to close this window..."
