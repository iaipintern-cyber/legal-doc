#!/usr/bin/env bash
# Plain-English status of the Court of Inquiry application.
set -u

here="$(dirname "$(readlink -f "$0")")"
d="$here"
while [ ! -f "$d/compose.yml" ] && [ "$d" != "/" ]; do d="$(dirname "$d")"; done
[ -f "$d/compose.yml" ] || { echo "!! Could not find the project folder (compose.yml)."; exit 1; }
cd "$d" || exit 1

if command -v docker >/dev/null 2>&1; then DOCKER=docker
elif command -v docker.exe >/dev/null 2>&1; then DOCKER=docker.exe
else echo "PROBLEM: Docker is not installed (the 'docker' command was not found)."; exit 1
fi

if ! $DOCKER info >/dev/null 2>&1; then
  echo "PROBLEM: Docker is not running. Start Docker (sudo systemctl start docker) and try again."
  exit 1
fi

word() {
  case "$1" in
    healthy|running) echo "OK (running)" ;;
    starting|restarting) echo "still starting..." ;;
    unhealthy) echo "RUNNING BUT NOT RESPONDING" ;;
    missing|exited|created) echo "STOPPED" ;;
    *) echo "$1" ;;
  esac
}

echo "Court of Inquiry application -- status"
echo "-------------------------------------"
fe=$($DOCKER inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' legal-frontend 2>/dev/null || echo missing)
be=$($DOCKER inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' legal-backend  2>/dev/null || echo missing)
ol=$($DOCKER inspect --format '{{.State.Status}}' legal-ollama 2>/dev/null || echo missing)
printf '  website   : %s\n' "$(word "$fe")"
printf '  engine    : %s\n' "$(word "$be")"
printf '  AI model  : %s\n' "$(word "$ol")"
echo "-------------------------------------"

if [ "$ol" = "running" ]; then
  if $DOCKER exec legal-ollama ollama list 2>/dev/null | grep -q "gemma3:4b"; then
    echo "  AI model file: OK (gemma3:4b present)"
  else
    echo "  AI model file: MISSING -- restore offline/ollama from the DVD (setup.md section 5)."
  fi
fi

if [ "$fe" = "healthy" ] && [ "$be" = "healthy" ] && [ "$ol" = "running" ]; then
  echo ""
  echo "RESULT: RUNNING. Open http://localhost:8080 in the browser."
  exit 0
fi

echo ""
echo "RESULT: not fully running."
echo "Try:  bash start-legal.sh   (it checks and fixes most problems)"
if [ "$fe" != "healthy" ] || [ "$be" != "healthy" ]; then
  bad="legal-frontend"; [ "$be" != "healthy" ] && bad="legal-backend"
  if [ "$fe" != "missing" ] && [ "$be" != "missing" ]; then
    echo ""
    echo "Recent messages from $bad (for a helper/administrator):"
    $DOCKER logs --tail 15 "$bad" 2>&1 | sed 's/^/    /'
  fi
fi
exit 1
