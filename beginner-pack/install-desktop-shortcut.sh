#!/usr/bin/env bash
# One-time setup: puts a "Start Court of Inquiry" icon on the Desktop so the
# app can be started by double-clicking -- no terminal needed afterwards.
set -u

say()  { printf '%s\n' "$*"; }
fail() { printf '\n!! PROBLEM: %s\n' "$1"; [ -n "${2:-}" ] && printf '%s\n' "$2"; exit 1; }

here="$(dirname "$(readlink -f "$0")")"
start="$here/start-legal.sh"
[ -f "$start" ] || fail "start-legal.sh was not found next to this script ($here)."
[ -f "$here/../compose.yml" ] || fail "This pack must sit inside the project folder (next to compose.yml)."

# Desktop folder (honours localization via xdg-user-dir)
if command -v xdg-user-dir >/dev/null 2>&1; then desk="$(xdg-user-dir DESKTOP 2>/dev/null)"; fi
desk="${desk:-$HOME/Desktop}"
mkdir -p "$desk" || fail "Could not create the Desktop folder: $desk"

# Pick whatever terminal this computer has; the script works even without one.
if   command -v gnome-terminal  >/dev/null 2>&1; then exe="gnome-terminal -- bash \"$start\""
elif command -v konsole         >/dev/null 2>&1; then exe="konsole -e bash \"$start\""
elif command -v xfce4-terminal  >/dev/null 2>&1; then exe="xfce4-terminal -- bash \"$start\""
elif command -v xterm          >/dev/null 2>&1; then exe="xterm -e bash \"$start\""
else exe="bash \"$start\""
fi

f="$desk/Start Court of Inquiry.desktop"
cat > "$f" <<EOF
[Desktop Entry]
Type=Application
Name=Start Court of Inquiry
Comment=Start the Court of Inquiry application (opens the browser)
Exec=$exe
Icon=system-run
Terminal=true
Categories=Office;
EOF
chmod 755 "$f" 2>/dev/null
command -v gio >/dev/null 2>&1 && gio set "$f" metadata::trusted true >/dev/null 2>&1

say "Done. An icon was created on the Desktop:"
say "    $f"
say ""
say "How to use it:"
say "  * Double-click 'Start Court of Inquiry'. The application starts and"
say "    the browser opens http://localhost:8080."
say "  * If the icon appears as a plain file instead of a program:"
say "      GNOME: right-click it -> 'Allow Launching'"
say "      KDE:   right-click it -> Properties -> Permissions -> 'Is executable'"
say ""
say "Tip: keep the beginner-pack folder inside the project folder; the icon"
say "will keep working as long as that folder does not move."
