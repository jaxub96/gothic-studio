#!/usr/bin/env bash
#
# make-shortcut.sh - a "Gothic Studio" app on the Desktop and in ~/Applications
# that runs the app from this source folder, like make-shortcut.bat on Windows:
# no Terminal window, the app's own icon, and every edit to the .py files is
# picked up on the next launch. No build needed.
#
#     cd gothic-studio && ./make-shortcut.sh
#
# Sets up .venv first if it is missing. Run it again if you move this folder,
# since the shortcut points at the old location. If the app fails to start it
# shows a dialog; ./run.sh runs the same thing with the error in the terminal.

set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
VENV=".venv"
PY="$VENV/bin/python"

say() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

# --- 1. Virtual environment with the app's dependencies ---------------------

if [ ! -x "$PY" ]; then
    say "Creating $VENV"
    command -v python3 >/dev/null 2>&1 \
        || { echo "error: python3 not found. brew install python@3.12" >&2; exit 1; }
    python3 -m venv "$VENV"
fi
if ! "$PY" -c "import PyQt6, numpy" >/dev/null 2>&1; then
    say "Installing dependencies (a minute or so)"
    "$PY" -m pip install --quiet -r requirements.txt
fi

# --- 2. The shortcut app ----------------------------------------------------

make_app() {  # make_app <parent dir>
    local app="$1/Gothic Studio.app"
    rm -rf "$app"
    mkdir -p "$app/Contents/MacOS" "$app/Contents/Resources"
    cp assets/icon.icns "$app/Contents/Resources/icon.icns"

    cat > "$app/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleName</key><string>Gothic Studio</string>
  <key>CFBundleDisplayName</key><string>Gothic Studio</string>
  <key>CFBundleIdentifier</key><string>local.gothicstudio.source</string>
  <key>CFBundleExecutable</key><string>launcher</string>
  <key>CFBundleIconFile</key><string>icon</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1</string>
  <key>NSHighResolutionCapable</key><true/>
</dict></plist>
PLIST

    cat > "$app/Contents/MacOS/launcher" <<LAUNCH
#!/bin/bash
cd "$ROOT" || exit 1
if [ ! -x "$ROOT/$PY" ]; then
    osascript -e 'display dialog "Gothic Studio: the .venv is missing. Run make-shortcut.sh again." buttons {"OK"} with icon stop'
    exit 1
fi
LOG="\$(mktemp -t gothicstudio)"
"$ROOT/$PY" studio.py "\$@" 2>"\$LOG"
status=\$?
if [ \$status -ne 0 ]; then
    osascript -e "display dialog \"Gothic Studio failed to start:\n\n\$(tail -n 8 "\$LOG" | tr '"' "'")\" buttons {\"OK\"} with icon stop"
fi
rm -f "\$LOG"
exit \$status
LAUNCH
    chmod +x "$app/Contents/MacOS/launcher"
    touch "$app"   # nudge Finder to refresh the icon
    echo "   $app"
}

say "Creating shortcuts"
mkdir -p "$HOME/Applications"
make_app "$HOME/Applications"
make_app "$HOME/Desktop"

echo
echo "Done. Start Gothic Studio from the Desktop or Launchpad/Spotlight; keep it"
echo "in the Dock from there if you like. First launch may need right-click > Open."
