#!/usr/bin/env bash
#
# build-macos.sh - one command from a fresh checkout to dist/GothicStudio.app
#
#     cd gothic-studio && ./build-macos.sh
#
# Safe to re-run: the venv is reused, dependencies are only installed when
# missing, and the .app is rebuilt from scratch each time.
#
# Also works on Linux, where it produces dist/GothicStudio instead.

set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
PY="$VENV/bin/python"

say()  { printf '\n\033[1m==> %s\033[0m\n' "$1"; }
warn() { printf '\033[33mwarning: %s\033[0m\n' "$1" >&2; }
die()  { printf '\033[31merror: %s\033[0m\n' "$1" >&2; exit 1; }

# --- 1. Python -------------------------------------------------------------

say "Checking Python"

command -v python3 >/dev/null 2>&1 \
    || die "python3 not found. Install it with: brew install python@3.12"

python3 - <<'EOF' || die "Python 3.10 or newer is required."
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
EOF

echo "python3  $(python3 -c 'import platform; print(platform.python_version())')"

# Building under Rosetta gives an Intel .app that will not run natively. Worth
# saying out loud rather than letting it surface as "bad CPU type" later.
if [ "$(uname -s)" = "Darwin" ]; then
    HOST_ARCH="$(uname -m)"
    PY_ARCH="$(python3 -c 'import platform; print(platform.machine())')"
    echo "machine  $HOST_ARCH (python reports $PY_ARCH)"
    if [ "$HOST_ARCH" != "$PY_ARCH" ]; then
        warn "Python is $PY_ARCH but this Mac is $HOST_ARCH - you are under Rosetta."
        warn "The build will be $PY_ARCH. Use a native python3 for an $HOST_ARCH app."
    fi
fi

# --- 2. Virtual environment ------------------------------------------------

if [ -x "$PY" ]; then
    say "Reusing $VENV"
else
    say "Creating $VENV"
    python3 -m venv "$VENV"
fi

# --- 3. Dependencies -------------------------------------------------------

if "$PY" -c "import PyQt6, numpy, PyInstaller" >/dev/null 2>&1; then
    say "Dependencies already installed"
else
    say "Installing dependencies (a minute or so)"
    "$PY" -m pip install --upgrade --quiet pip
    "$PY" -m pip install --quiet -r requirements.txt
    "$PY" -m pip install --quiet pyinstaller
fi
"$PY" -c "import PyQt6.QtCore as c; print('PyQt6   ', c.QT_VERSION_STR)"

# --- 4. Smoke test ---------------------------------------------------------
#
# Run from source before freezing: a failure here is far easier to read than
# the same failure inside a bundle. Not finding the mod is fine at this point -
# the app asks for the folder on first launch - so this must not be fatal.

say "Checking the source runs"
if "$PY" studio.py --check; then
    :
else
    warn "No Gothic II found yet. That is fine - the app will ask on first launch."
fi

# --- 5. Build --------------------------------------------------------------

say "Building"
"$PY" build_exe.py

# --- 6. Unquarantine -------------------------------------------------------

APP="dist/GothicStudio.app"
if [ "$(uname -s)" = "Darwin" ] && [ -d "$APP" ]; then
    # Only affects this machine. Anyone you send it to has to right-click >
    # Open once themselves, or run the same command.
    xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true

    say "Done"
    echo "  $(pwd)/dist/GothicStudio.app"
    echo
    echo "Open it with:  open '$APP'"
    echo
    echo "Sending it to someone else? They get a Gatekeeper warning on first"
    echo "launch - tell them to right-click the app and choose Open."
else
    say "Done"
fi
