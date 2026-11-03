"""
config.py - the one setting Gothic Studio remembers: where your mod lives.

Kept deliberately tiny and dependency-free (no Qt, no project import) so that
project.py can read it while it is still working out its own paths.

The file lands in the usual per-user spot for each OS:

    Windows   %APPDATA%\GothicStudio\config.json
    macOS     ~/Library/Application Support/GothicStudio/config.json
    Linux     ~/.config/GothicStudio/config.json
"""

import json
import os
import sys
from pathlib import Path

APP = "GothicStudio"


def _config_dir():
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / APP


CONFIG_FILE = _config_dir() / "config.json"


def load():
    """The saved settings, or {} if there are none / the file is unreadable."""
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        # A corrupt or missing config must never stop the app starting; the
        # worst case is that we fall back to walking up from the executable.
        return {}


def get(key, default=None):
    return load().get(key, default)


def save(key, value):
    """Write one key, keeping whatever else is in the file. Returns True on success."""
    data = load()
    data[key] = value
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except OSError:
        return False
