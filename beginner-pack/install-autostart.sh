#!/usr/bin/env bash
# Optional one-time setup: start the application automatically when this user
# logs in (systemd user service -- no administrator/rights needed for this).
# To undo:  systemctl --user disable --now legal-app.service
set -u

say()  { printf '%s\n' "$*"; }
fail() { printf '\n!! PROBLEM: %s\n' "$1"; [ -n "${2:-}" ] && printf '%s\n' "$2"; exit 1; }

here="$(dirname "$(readlink -f "$0")")"
d="$(dirname "$here")"
[ -f "$d/compose.yml" ] || fail "This pack must sit inside the project folder (next to compose.yml)."

command -v systemctl >/dev/null 2>&1 ||
  fail "This computer does not use systemd services." "Use the desktop icon instead (install-desktop-shortcut.sh)."

# Probe: can we talk to the user service manager? (fails on systems without systemd)
systemctl --user daemon-reload >/dev/null 2>&1 ||
  fail "Automatic start is not available here (user services are not running on this system)." \
       "Use the desktop icon or 'bash start-legal.sh' instead. Nothing was changed."

case "$here $d" in
  *[[:space:]]*) fail "The project path contains spaces ($d)." \
       "Move the project to a path without spaces (e.g. \$HOME/legal), then rerun this." ;;
esac

unit="$HOME/.config/systemd/user/legal-app.service"
mkdir -p "$HOME/.config/systemd/user" || fail "Could not create $HOME/.config/systemd/user"
cat > "$unit" <<EOF
[Unit]
Description=Court of Inquiry application (Docker Compose stack)

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$d
ExecStart=bash $here/start-legal.sh --quiet
ExecStop=bash $here/stop-legal.sh

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload || fail "The service could not be registered (see above)."
systemctl --user enable --now legal-app.service ||
  fail "The service could not be enabled (see above)." \
       "You can still start everything with:  bash start-legal.sh"

say "Done. The application now starts automatically whenever you log in."
say "  (It is starting right now -- give it up to a minute the first time.)"
say ""
say "Optional -- ask your administrator to also start it at boot, before"
say "anyone logs in:    sudo loginctl enable-linger $USER"
say ""
say "To undo this automatic start:"
say "    systemctl --user disable --now legal-app.service"
