#!/usr/bin/env bash
# Start the Court of Inquiry application. No Docker knowledge needed.
#   usage:  bash start-legal.sh [--quiet]
#   --quiet = no browser window / no "press Enter" (used by the auto-start service)
set -u

QUIET=0
[ "${1:-}" = "--quiet" ] && QUIET=1

say()  { printf '%s\n' "$*"; }
pause() { if [ -t 0 ]; then printf '%s' "$1"; read -r _; fi; }
fail() {
  printf '\n!! PROBLEM: %s\n' "$1"
  [ -n "${2:-}" ] && printf '%s\n' "$2"
  pause "Press Enter to close this window..."
  exit 1
}

# --- find the project folder (the folder containing compose.yml) ---
here="$(dirname "$(readlink -f "$0")")"
d="$here"
while [ ! -f "$d/compose.yml" ] && [ "$d" != "/" ]; do d="$(dirname "$d")"; done
[ -f "$d/compose.yml" ] || fail "Could not find the project folder (compose.yml)." \
  "Keep the beginner-pack folder inside the project folder (usually \$HOME/legal)."
cd "$d" || fail "Cannot open the project folder: $d"

# --- locate Docker ---
if command -v docker >/dev/null 2>&1; then DOCKER=docker
elif command -v docker.exe >/dev/null 2>&1; then DOCKER=docker.exe
else fail "Docker is not installed on this computer (the 'docker' command was not found)." \
  "Ask your administrator to install Docker Engine, then run this again."
fi
$DOCKER info >/dev/null 2>&1 || fail "Docker is installed but not running." \
  "Start it (an administrator can run: sudo systemctl start docker), then run this again."

# --- locate Docker Compose (needs 2.24.4+) ---
if $DOCKER compose version >/dev/null 2>&1; then DC="$DOCKER compose"
elif [ -x "$HOME/.docker/cli-plugins/docker-compose" ]; then DC="$HOME/.docker/cli-plugins/docker-compose"
else fail "Docker Compose is missing." "Install the carried plugin -- see setup.md, section 5."
fi

say "Checking the application..."

# --- images: load them automatically if they are missing ---
if ! $DOCKER image inspect legal-backend:1.0 >/dev/null 2>&1; then
  if [ -f offline/images/legal-images.tar.gz ]; then
    say "The Docker images are missing -- loading them now (one time, a few minutes)..."
    gzip -dc offline/images/legal-images.tar.gz | $DOCKER load >/dev/null ||
      fail "The images could not be loaded from offline/images/legal-images.tar.gz." \
           "Re-copy that file from DVD 1 into offline/images/, then run this again."
    say "Images loaded."
  else
    fail "The Docker images are missing and offline/images/legal-images.tar.gz is not here." \
         "Copy legal-images.tar.gz from DVD 1 into offline/images/ (setup.md section 5), then run this again."
  fi
fi

# --- AI model: must be present ---
[ -d offline/ollama/models/blobs ] || fail "The AI model folder offline/ollama/models is missing." \
  "If \$HOME/legal-staging still exists, run:  cp -a \"\$HOME/legal-staging/ollama\" offline/   (setup.md section 5)."

# --- start ---
say "Starting the application (first start: 30-60 seconds)..."
$DC -f compose.yml up -d --pull never --no-build ||
  fail "Docker could not start the application." \
       "Run 'bash beginner-pack/status-legal.sh' -- it prints what is wrong."

# --- wait until everything is healthy ---
printf 'Waiting'
ok=""
fe=missing; be=missing; ol=missing
for i in $(seq 1 90); do
  fe=$($DOCKER inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' legal-frontend 2>/dev/null || echo missing)
  be=$($DOCKER inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' legal-backend  2>/dev/null || echo missing)
  ol=$($DOCKER inspect --format '{{.State.Status}}' legal-ollama 2>/dev/null || echo missing)
  if [ "$fe" = "healthy" ] && [ "$be" = "healthy" ] && [ "$ol" = "running" ]; then ok=1; break; fi
  [ $((i % 5)) -eq 0 ] && printf '.'
  sleep 2
done
printf '\n'

if [ -z "$ok" ]; then
  fail "The application did not become ready in time." \
       "Current state: frontend=$fe  backend=$be  ollama=$ol.
Run 'bash beginner-pack/status-legal.sh' for recent log lines, then ask for help."
fi

say ""
say "=========================================================="
say "  OK -- the Court of Inquiry application is running."
say "  In the browser open:   http://localhost:8080"
say "  To stop it later:      bash stop-legal.sh   (data is kept)"
say "  To check it:           bash status-legal.sh"
say "=========================================================="
if [ "$QUIET" = "0" ] && [ -t 0 ] && command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://localhost:8080 >/dev/null 2>&1 &
fi
pause "Press Enter to close this window..."
