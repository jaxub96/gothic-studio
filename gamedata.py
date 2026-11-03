"""
gamedata.py - reads the real identifiers straight out of Content/.

Nothing in here is a hardcoded list of game content. If you add an item or a
guild to the mod, it shows up in the pickers on the next launch. Every function
is cached, so the disk scan happens once.
"""

import re
from functools import lru_cache

from project import CONTENT, ENCODING, iglob


def _read(path):
    try:
        return path.read_text(encoding=ENCODING, errors="ignore")
    except OSError:
        return ""


def _scan(globpat, pattern):
    """Collect every capture group 1 match of `pattern` across `globpat`."""
    found = []
    for f in iglob(CONTENT, globpat):
        found += re.findall(pattern, _read(f), re.I | re.M)
    return sorted(set(found), key=str.lower)


# --- Items ------------------------------------------------------------------
# Returns {instance_id: display_name}. Items whose name is a constant rather
# than a literal fall back to showing their id.

@lru_cache
def items():
    out = {}
    for f in sorted(iglob(CONTENT / "Items", "*.d")):
        for seg in re.split(r"(?im)^[ \t]*INSTANCE[ \t]+", _read(f))[1:]:
            m = re.match(r"(\w+)\s*\(\s*C_Item", seg, re.I)
            if not m:
                continue
            body = seg.split("\n};")[0]
            nm = re.search(r'^\s*name\s*=\s*"([^"]*)"', body, re.I | re.M)
            out[m.group(1)] = nm.group(1) if nm else m.group(1)
    return dict(sorted(out.items(), key=lambda kv: kv[0].lower()))


@lru_cache
def armors():
    """{ITAR_xxx: display name} - the armor subset of items()."""
    return {k: v for k, v in items().items() if k.upper().startswith("ITAR_")}


@lru_cache
def item_visuals():
    """{instance: visual filename} e.g. ITAR_BARKEEPER -> ItAr_Wirt.3DS.

    This is how an item names its 3D model, and the model is what names the
    texture - so it is the first link in resolving an armor preview.
    """
    out = {}
    for f in sorted(iglob(CONTENT / "Items", "*.d")):
        for seg in re.split(r"(?im)^[ \t]*INSTANCE[ \t]+", _read(f))[1:]:
            m = re.match(r"(\w+)\s*\(\s*C_Item", seg, re.I)
            if not m:
                continue
            body = seg.split("\n};")[0]
            vis = re.search(r'^\s*visual\s*=\s*"([^"]+)"', body, re.I | re.M)
            if vis:
                out[m.group(1).upper()] = vis.group(1)
    return out


@lru_cache
def armors_by_guild():
    """Armors grouped by their guild tag, for the armor tree.

    ITAR_Vlk_H -> group 'VLK'. Anything that does not parse lands in 'Other'.
    """
    groups = {}
    for code, name in armors().items():
        parts = code.split("_")
        tag = parts[1].upper() if len(parts) > 2 else "Other"
        groups.setdefault(tag, []).append((code, name))
    return dict(sorted(groups.items()))


# --- NPC fields -------------------------------------------------------------

@lru_cache
def guilds():
    """Human guilds only. GIL_SEPERATOR_HUM = 16 divides humans from monsters."""
    txt = _read(CONTENT / "_intern" / "Constants.d")
    pairs = re.findall(r"^\s*const\s+int\s+(GIL_\w+)\s*=\s*(\d+)", txt, re.I | re.M)
    skip = ("GIL_SEPERATOR", "GIL_EMPTY", "GIL_PUBLIC", "GIL_HUMAN")
    return [n for n, v in pairs if int(v) < 16 and not n.upper().startswith(skip)]


@lru_cache
def npctypes():
    return _scan("AI/AI_Intern/*.d", r"^\s*const\s+int\s+(NPCTYPE_\w+)")


@lru_cache
def tactics():
    """Human fight tactics, from the FAI_*.d filenames. No '.d' suffix."""
    return [f.stem.upper() for f in sorted(iglob(CONTENT / "FAI", "FAI_Human*.d"))]


@lru_cache
def routines():
    """Every TA_* daily-routine function. There is no TA_Position in Gothic 2."""
    return _scan("AI/**/*.d", r"^\s*func\s+void\s+(TA_\w+)")


@lru_cache
def heads():
    """Head meshes actually referenced by this install - 6, not the G1 list of 14."""
    return sorted({h.upper() for h in _scan("**/*.d", r'"(HUM_HEAD_\w+)"')})


def _const_values(prefix):
    """{CONST_NAME: int} for `const int <prefix>... = N;` across Content/."""
    out = {}
    for f in iglob(CONTENT, "**/*.d"):
        for name, value in re.findall(
                rf"^\s*const\s+int\s+({prefix}\w+)\s*=\s*(-?\d+)",
                _read(f), re.I | re.M):
            out.setdefault(name, int(value))
    return out


@lru_cache
def body_texture_values():
    """BodyTex_N -> 1. The number is what picks HUM_BODY_NAKED_V<n>_C0."""
    return _const_values("BodyTex_")


@lru_cache
def face_values():
    """Face_N_Gomez -> 0. The number is what picks HUM_HEAD_V<n>_C0."""
    return _const_values("Face_")


@lru_cache
def body_textures():
    return sorted(body_texture_values(), key=str.lower)


@lru_cache
def faces():
    """Face constants, ordered by their texture number so scrolling the list
    walks through the faces in the order the game numbers them."""
    values = face_values()
    return sorted(values, key=lambda n: (values[n], n.lower()))


@lru_cache
def overlays():
    """Body/walk MDS overlays, read from Data\\Anims\\mds_overlay.

    Weapon-stance overlays (Humans_1hST1, Humans_BowT2, ...) are applied by the
    engine during combat, so they are filtered out - they are not a walk style.
    The common ones are listed first; the rest follow alphabetically.
    """
    from project import MDS_OVERLAY

    skip = re.compile(r"(ST1|ST2|T1|T2|Acrobatic|Skeleton_Fly)", re.I)
    if MDS_OVERLAY.is_dir():
        found = {f.stem.upper() + ".MDS" for f in iglob(MDS_OVERLAY, "Humans_*.mds")
                 if not skip.search(f.stem)}
    else:
        # No asset folder (tool copied elsewhere): fall back to script references.
        found = set()
        for f in iglob(CONTENT, "**/*.d"):
            found |= {o.upper() for o in
                      re.findall(r'"(HUMANS_[A-Za-z]+\.MDS)"', _read(f), re.I)}

    common = ["HUMANS_MILITIA.MDS", "HUMANS_RELAXED.MDS", "HUMANS_ARROGANCE.MDS",
              "HUMANS_MAGE.MDS", "HUMANS_TIRED.MDS", "HUMANS_BABE.MDS"]
    first = [c for c in common if c in found]
    return first + sorted(found - set(first))


@lru_cache
def voices():
    """Voice numbers backed by a real SVM_<n> instance."""
    nums = _scan("**/*.d", r"^\s*instance\s+SVM_(\d+)")
    return sorted({int(n) for n in nums})


# --- Dialog fields ----------------------------------------------------------

@lru_cache
def npc_instances():
    """{instance: source file} for every Npc_Default instance in Story/NPC.

    This is what links the two halves of the app: the Dialog tab needs an NPC
    id that actually exists, and this is where it comes from.
    """
    out = {}
    for f in sorted(iglob(CONTENT / "Story" / "NPC", "**/*.d")):
        for m in re.finditer(r"^\s*instance\s+(\w+)\s*\(\s*Npc_Default\s*\)",
                             _read(f), re.I | re.M):
            out[m.group(1)] = f.name
    return out


@lru_cache
def xp_constants():
    return _scan("Story/XP_Constants.d", r"^\s*const\s+int\s+(XP_\w+)")


@lru_cache
def log_topics():
    return _scan("Story/Log_Entries/*.d", r"^\s*const\s+string\s+(TOPIC_\w+)")


@lru_cache
def waypoints():
    """Waypoint names from .check/worldnames.json, if the waypoint check made one."""
    import json
    from project import CHECK_DIR
    f = CHECK_DIR / "worldnames.json"
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, ValueError):
        return []
    names = set()

    def walk(node):
        if isinstance(node, str):
            names.add(node)
        elif isinstance(node, list):
            for x in node:
                walk(x)
        elif isinstance(node, dict):
            for x in node.values():
                walk(x)

    walk(data)
    return sorted(n for n in names if n.upper().startswith("WP"))


# --- Validation -------------------------------------------------------------

def unknown(kind, value):
    """True if `value` is not a known identifier of `kind`.

    Used by the Validate button so a typo gets caught in the UI instead of
    turning into a gdc error 20 seconds later.
    """
    if not value:
        return False
    table = {
        "item": lambda: items().keys(),
        "armor": lambda: list(armors().keys()) + ["-1", "NO_ARMOR"],
        "guild": guilds,
        "npctype": npctypes,
        "tactic": tactics,
        "routine": routines,
        "head": heads,
        "npc": lambda: npc_instances().keys(),
        "xp": xp_constants,
    }
    if kind not in table:
        return False
    known = {str(x).upper() for x in table[kind]()}
    return str(value).upper() not in known


if __name__ == "__main__":
    # `python gamedata.py` prints what it found - handy after editing a regex.
    for fn in (items, armors, guilds, npctypes, tactics, routines, heads,
               body_textures, faces, overlays, voices, npc_instances,
               xp_constants, log_topics, waypoints):
        print(f"{fn.__name__:16} {len(fn())}")
