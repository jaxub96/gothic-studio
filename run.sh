#!/usr/bin/env bash
# Launch Gothic Studio from source on macOS or Linux.
# Uses .venv if present, otherwise whatever python3 is on PATH.
set -euo pipefail
cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
    exec .venv/bin/python studio.py "$@"
else
    exec python3 studio.py "$@"
fi
