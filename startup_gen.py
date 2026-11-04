"""
startup_gen.py - putting an NPC into the world: Wld_InsertNpc in Startup.d.

Gothic only creates an NPC when a script calls Wld_InsertNpc, and the place for
that is the STARTUP_<WORLD> function in Content/Story/Startup.d, which runs
once, the first time the world is entered. An NPC instance on its own, however
well written, never appears in the game.

Startup.d is a hand-edited file that holds other people's code, so this module
changes as little as it can: it adds or removes single Wld_InsertNpc lines and
touches nothing else. It works on the raw bytes (decoded as latin-1, which
cannot fail or change anything) and keeps the file's own line endings.
No Qt in here.
"""

import re

import daedalus_read
from project import CONTENT

STARTUP_FILE = CONTENT / "Story" / "Startup.d"

_STARTUP = re.compile(r"\bfunc\s+void\s+STARTUP_(\w+)\s*\(\s*\)\s*\{", re.I)


def _read():
    try:
        raw = STARTUP_FILE.read_bytes()
    except OSError:
        return None
    return raw.decode("latin-1")


def _write(text):
    STARTUP_FILE.write_bytes(text.encode("latin-1"))


def _functions(text):
    """[(world, body_start, body_end)] for every STARTUP_<WORLD> function."""
    out = []
    for m in _STARTUP.finditer(text):
        end = daedalus_read.match_brace(text, m.end() - 1)
        if end >= 0:
            out.append((m.group(1), m.end(), end))
    return out


def worlds():
    """The worlds Startup.d already has a STARTUP function for."""
    text = _read()
    if text is None:
        return []
    return [w for w, _, _ in _functions(text) if w.upper() != "GLOBAL"]


def _insert_re(instance):
    return re.compile(
        r"^[ \t]*Wld_InsertNpc\s*\(\s*" + re.escape(instance) +
        r'\s*,\s*"([^"]*)"\s*\)\s*;[^\r\n]*(\r?\n)?', re.I | re.M)


def find_spawn(instance):
    """(world, waypoint) where Startup.d inserts `instance`, or None."""
    text = _read()
    if text is None:
        return None
    pattern = _insert_re(instance)
    for world, start, end in _functions(text):
        m = pattern.search(text, start, end)
        if m:
            return world, m.group(1)
    return None


def set_spawn(instance, world, waypoint):
    """Make Startup.d insert `instance` at `waypoint` when `world` first loads.

    Any earlier insert of the same instance is removed first, so an NPC is
    never spawned twice. Returns a short note for the status line, or "" when
    nothing needed changing. Raises ValueError if the world has no STARTUP
    function to put the line in.
    """
    text = _read()
    if text is None:
        raise ValueError(f"{STARTUP_FILE} not found")
    if not waypoint:
        raise ValueError("no spawn waypoint")

    target = next((f for f in _functions(text) if f[0].upper() == str(world).upper()), None)
    if target is None:
        raise ValueError(f"Startup.d has no STARTUP_{world} function")

    eol = "\r\n" if "\r\n" in text else "\n"
    line = f'\tWld_InsertNpc\t({instance}, "{waypoint}");'

    cleaned = _insert_re(instance).sub("", text)
    target = next(f for f in _functions(cleaned) if f[0].upper() == str(world).upper())
    _, start, end = target
    body = cleaned[start:end]

    # Put the line after the last statement, before the closing brace, keeping
    # whatever comment or blank lines the function already has above it.
    stripped = body.rstrip()
    new_body = stripped + eol + line + eol
    result = cleaned[:start] + new_body + cleaned[end:]
    if result == text:
        return ""
    _write(result)
    return f"spawn in STARTUP_{target[0]} at {waypoint}"


def clear_spawn(instance):
    """Remove `instance` from Startup.d. Returns a note, or "" if it was not there."""
    text = _read()
    if text is None:
        return ""
    result = _insert_re(instance).sub("", text)
    if result == text:
        return ""
    _write(result)
    return "removed from Startup.d"


def sync(instance, npc):
    """Bring Startup.d in line with the NPC's spawn settings. Returns a note."""
    if not getattr(npc, "spawn", False):
        return clear_spawn(instance)
    world = npc.spawn_world or (worlds() or [""])[0]
    waypoint = npc.spawn_waypoint or npc.waypoint or "WP_INTRO_FALL3"
    return set_spawn(instance, world, waypoint)
