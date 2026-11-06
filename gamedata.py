"""
gamedata.py - reads the real identifiers straight out of Content/.

Nothing in here is a hardcoded list of game content. If you add an item or a
guild to the mod, it shows up in the pickers on the next launch. Every function
is cached, so the disk scan happens once.
"""

import re
from functools import lru_cache

from daedalus_read import strip_comments
from project import CONTENT, ENCODING, iglob


def _read(path):
    """A script's text without its comments: what is commented out does not exist."""
    try:
        return strip_comments(path.read_text(encoding=ENCODING, errors="ignore"))
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

# Script libraries that live under Content/MOD in a mod that uses Ikarus / LeGo.
# They carry demo instances (Ikarus's _01_MultiTestBuch book, say) that the build
# check compiles from stubs, so an NPC given one fails to compile. Never offer them.
_LIBRARY_DIRS = {"ikarus", "lego", "ikarus_scripts", "lego_scripts", "basic_scripts"}


def _is_library(path):
    return any(part.lower() in _LIBRARY_DIRS for part in path.parts)


def _item_files():
    """Vanilla's Items/ plus the mod package's Mod/ (see mod/README.md), minus the
    bundled script libraries."""
    mod = [f for f in iglob(CONTENT / "Mod", "**/*.d") if not _is_library(f)]
    return sorted(iglob(CONTENT / "Items", "**/*.d")) + sorted(mod)


@lru_cache
def items():
    out = {}
    for f in _item_files():
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
    for f in _item_files():
        for seg in re.split(r"(?im)^[ \t]*INSTANCE[ \t]+", _read(f))[1:]:
            m = re.match(r"(\w+)\s*\(\s*C_Item", seg, re.I)
            if not m:
                continue
            body = seg.split("\n};")[0]
            vis = re.search(r'^\s*visual\s*=\s*"([^"]+)"', body, re.I | re.M)
            if vis:
                out[m.group(1).upper()] = vis.group(1)
    return out


def is_female_armor(code):
    """Women's armors are the ITAR_*Babe* ones (BauBabe, VlkBabe, DJG_BABE)."""
    return "babe" in str(code).lower()


@lru_cache
def armors_by_guild(gender=None):
    """Armors grouped by their guild tag, for the armor tree.

    ITAR_Vlk_H -> group 'VLK'. Anything that does not parse lands in 'Other'.
    With a `gender`, only the armors that gender wears.
    """
    groups = {}
    for code, name in armors().items():
        if gender and is_female_armor(code) != (str(gender).upper() == "FEMALE"):
            continue
        parts = code.split("_")
        tag = parts[1].upper() if len(parts) > 2 else "Other"
        groups.setdefault(tag, []).append((code, name))
    return dict(sorted(groups.items()))


# --- NPC fields -------------------------------------------------------------

_GIL_NUMBER = re.compile(r"^\s*const\s+int\s+(GIL_\w+)\s*=\s*(\d+)", re.I | re.M)
_GIL_ALIAS = re.compile(r"^[ \t]*const\s+int\s+(GIL_\w+)\s*=\s*(GIL_\w+)\s*;[ \t]*(?://[ \t]*(.*))?$",
                        re.I | re.M)
_GIL_SKIP = ("GIL_SEPERATOR", "GIL_EMPTY", "GIL_PUBLIC", "GIL_HUMAN")


def _guild_slots():
    """{GIL_NAME: slot} for the vanilla numbers in _intern/Constants.d."""
    txt = _read(CONTENT / "_intern" / "Constants.d")
    return {n: int(v) for n, v in _GIL_NUMBER.findall(txt)}


@lru_cache
def mod_guilds():
    """[(GIL_ALIAS, vanilla GIL_, display name)] from the mod package's guild file.

    A mod cannot add human guilds - vanilla fills all 16 slots - so it names a
    slot for itself: `const int GIL_WATCH = GIL_MIL;  // City Watch - note`.
    The display name is the comment up to " - ". Read raw, because _read()
    drops comments.
    """
    out = []
    for f in sorted(iglob(CONTENT / "Mod", "**/*.d")):
        try:
            txt = f.read_text(encoding=ENCODING, errors="ignore")
        except OSError:
            continue
        for alias, slot, note in _GIL_ALIAS.findall(txt):
            name = (note or "").split(" - ")[0].strip()
            out.append((alias, slot, name))
    return out


@lru_cache
def guilds():
    """Human guilds only. GIL_SEPERATOR_HUM = 16 divides humans from monsters.

    With the mod package installed, its names come first and the vanilla slots
    they take over are left out - both compile, but the mod's scripts should
    say GIL_WATCH, not GIL_MIL. unknown() still accepts the vanilla names.
    """
    vanilla = [n for n, v in _guild_slots().items()
               if v < 16 and not n.upper().startswith(_GIL_SKIP)]
    mod = mod_guilds()
    taken = {slot.upper() for _, slot, _ in mod}
    return [a for a, _, _ in mod] + [n for n in vanilla if n.upper() not in taken]


@lru_cache
def guild_names():
    """{GIL_ALIAS: display name} for the mod's guilds, for labels.pretty()."""
    return {alias: name for alias, _, name in mod_guilds() if name}


def all_guilds():
    """Every name a script may use for a human guild: the mod's and vanilla's."""
    return guilds() + [n for n in _guild_slots() if n not in guilds()]


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
    """Head meshes referenced by the scripts in this install, plus the female
    ones (HUM_HEAD_BABE*) the game ships even when no script names them."""
    import textures

    found = {h.upper() for h in _scan("**/*.d", r'"(HUM_HEAD_\w+)"')}
    for key in textures._mesh_index():
        m = re.fullmatch(r"(HUM_HEAD_BABE\w*)\.MMB", key)
        if m:
            found.add(m.group(1))
    return sorted(found)


def is_female_head(name):
    return str(name).upper().startswith("HUM_HEAD_BABE")


#: Voice sets spoken by women. SVM_16 and SVM_17 are the two full sets that are
#: not the male voices 1-15 (SVM_0 and SVM_18 are empty placeholders).
FEMALE_VOICES = (16, 17)


def _const_values(prefix):
    """{CONST_NAME: int} for `const int <prefix>... = N;` across Content/."""
    out = {}
    for f in iglob(CONTENT, "**/*.d"):
        for name, value in re.findall(
                rf"^\s*const\s+int\s+({prefix}\w+)\s*=\s*(-?\d+)",
                _read(f), re.I | re.M):
            out.setdefault(name, int(value))
    return out


# --- Female faces and skins --------------------------------------------------
# The game ships head and body textures for women that this install's scripts
# give no constant to. They are offered under a name of their own and written to
# the .d file as the bare number, which is all B_SetNpcVisual needs.

FEMALE_FACE_PREFIX = "Face_Babe_"
FEMALE_BODY_PREFIX = "BodyTex_Babe_"
#: Male skins no script names (V9 here); offered as BodyTex_Man_<n>.
MALE_BODY_PREFIX = "BodyTex_Man_"
BODY_PREFIXES = (FEMALE_BODY_PREFIX, MALE_BODY_PREFIX)

#: HUM_BODY_NAKED_V<n>_C0 textures drawn for the female body (V4-V7 are bare
#: skin in four tones, V11 and V12 are special outfits). Found by rendering
#: every V0..V12 on HUM_BODY_BABE0 - the rest are male chests or male clothes.
FEMALE_BODY_TEXTURES = (4, 5, 6, 7, 11, 12)


def _is_female(name, *prefixes):
    return str(name).lower().startswith(tuple(p.lower() for p in prefixes))


def is_female_face(name):
    return _is_female(name, FEMALE_FACE_PREFIX, "FaceBabe_")


def is_female_body(name):
    return _is_female(name, FEMALE_BODY_PREFIX, "BodyTexBabe_")


@lru_cache
def face_values():
    """Face_N_Gomez -> 0. The number is what picks HUM_HEAD_V<n>_C0.

    Head textures that no script names are added as Face_Babe_<n>.
    """
    import textures

    out = dict(_const_values("Face_"))
    named = set(out.values())
    for key in textures._index():
        m = re.fullmatch(r"HUM_HEAD_V(\d+)_C0", key)
        if m and int(m.group(1)) not in named:
            out[f"{FEMALE_FACE_PREFIX}{m.group(1)}"] = int(m.group(1))
    return out


@lru_cache
def body_texture_values():
    """BodyTex_N -> 1. The number is what picks HUM_BODY_NAKED_V<n>_C0.

    Skins no script names are added: BodyTex_Babe_<n> for the female ones,
    BodyTex_Man_<n> for any other.
    """
    import textures

    out = dict(_const_values("BodyTex_"))
    named = set(out.values())
    found = sorted(int(m.group(1)) for key in textures._index()
                   if (m := re.fullmatch(r"HUM_BODY_NAKED_V(\d+)_C0", key)))
    for n in found:
        if n in named:
            continue
        prefix = FEMALE_BODY_PREFIX if n in FEMALE_BODY_TEXTURES else MALE_BODY_PREFIX
        out[f"{prefix}{n}"] = n
    return out


def _code(name, prefix):
    """What to write in a script: the number for a synthesised name."""
    name = str(name)
    for p in ((prefix,) if isinstance(prefix, str) else prefix):
        if name.lower().startswith(p.lower()):
            return name[len(p):]
    return name


def _from_code(code, values, prefix):
    code = str(code).strip()
    if code.isdigit():
        for name, value in values.items():
            if value == int(code) and name.startswith(prefix if isinstance(prefix, str) else tuple(prefix)):
                return name
    return code


def face_code(face):
    return _code(face, FEMALE_FACE_PREFIX)


def face_from_code(code):
    return _from_code(code, face_values(), FEMALE_FACE_PREFIX)


def body_code(body):
    return _code(body, BODY_PREFIXES)


def body_from_code(code):
    return _from_code(code, body_texture_values(), BODY_PREFIXES)


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

    # Not walk styles: weapon stances, plus movement or situation sets the engine
    # switches to by itself (fleeing, sprinting, swimming, a held torch) and
    # the skeleton's own.
    skip = re.compile(r"(ST1|ST2|T1|T2|Acrobatic|Skeleton|Flee|Sprint|Swim|Torch)",
                      re.I)
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


FEMALE_WALK = "HUMANS_BABE.MDS"


# --- What each gender may pick ----------------------------------------------
# Women and men have their own head meshes, face and skin textures, walk and
# voice sets; offering the other's gives a character that looks or sounds wrong.

def _female(gender):
    return str(gender).upper() == "FEMALE"


def heads_for(gender):
    return [h for h in heads() if is_female_head(h) == _female(gender)]


def faces_for(gender):
    return [f for f in faces() if is_female_face(f) == _female(gender)]


def body_textures_for(gender):
    values = body_texture_values()
    mine = [b for b in body_textures() if is_female_body(b) == _female(gender)]
    return sorted(mine, key=lambda b: (values[b], b.lower()))


def overlays_for(gender):
    """Women get the female walk first; men do not get it at all."""
    others = [o for o in overlays() if o != FEMALE_WALK]
    return [FEMALE_WALK] + others if _female(gender) and FEMALE_WALK in overlays() else others


def voices_for(gender):
    return [v for v in voices() if (v in FEMALE_VOICES) == _female(gender)]


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
    """XP_ constants, and XP_ vars too: vanilla XP_Ambient is a var and works the same in B_GivePlayerXP."""
    pat = r"^\s*(?:const|var)\s+int\s+(XP_\w+)"
    return sorted(set(_scan("Story/XP_Constants.d", pat) + _scan("Mod/**/*.d", pat)),
                  key=str.lower)


@lru_cache
def log_topics():
    return _scan("Story/Log_Entries/**/*.d", r"^\s*const\s+string\s+(TOPIC_\w+)")


@lru_cache
def info_instances():
    """Every dialog (C_INFO instance) in Content/ - what Npc_KnowsInfo can name."""
    return _scan("**/*.d", r"^\s*instance\s+(\w+)\s*\(\s*C_INFO\s*\)")


def _world_files():
    """Every .zen under Data/Worlds. The folder is WORLDS on this install and
    Worlds elsewhere, so find it by name ignoring case (Linux cares)."""
    from project import SCRIPTS
    data = SCRIPTS.parent
    try:
        base = next((d for d in data.iterdir()
                     if d.is_dir() and d.name.lower() == "worlds"), None)
    except OSError:
        return []
    return sorted(iglob(base, "**/*.zen")) if base else []


# ASCII archives spell it out; binary (BIN_SAFE) ones, which is what the stock
# worlds are, store a type byte, a 16-bit length, then the name.
_WP_ASCII = re.compile(rb"wpName=string:([^\r\n]+)")
_WP_BINARY = re.compile(rb"zCWaypoint 0 \d+\]\x12.\[\x00\x00\x01", re.S)


def _zen_waypoints(path):
    try:
        data = path.read_bytes()
    except OSError:
        return set()
    names = {m.group(1).decode(ENCODING, "ignore").strip()
             for m in _WP_ASCII.finditer(data)}
    for m in _WP_BINARY.finditer(data):
        n = int.from_bytes(data[m.end():m.end() + 2], "little")
        raw = data[m.end() + 2:m.end() + 2 + n]
        if 0 < n < 128:
            names.add(raw.decode(ENCODING, "ignore").strip())
    return names


@lru_cache
def waypoints():
    """Waypoint names from every world in Data/Worlds, plus any listed in
    .check/worldnames.json if a waypoint check left one there."""
    import json
    from project import CHECK_DIR
    names = set()
    for f in _world_files():
        names |= _zen_waypoints(f)

    f = CHECK_DIR / "worldnames.json"
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
        except (OSError, ValueError):
            data = []

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
    return sorted((n for n in names if re.fullmatch(r"\w+", n)), key=str.lower)


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
        "guild": all_guilds,
        "npctype": npctypes,
        "tactic": tactics,
        "routine": routines,
        "head": heads,
        "npc": lambda: npc_instances().keys(),
        "xp": xp_constants,
        "info": info_instances,
    }
    if kind not in table:
        return False
    known = {str(x).upper() for x in table[kind]()}
    return str(value).upper() not in known


if __name__ == "__main__":
    # `python gamedata.py` prints what it found - handy after editing a regex.
    for fn in (items, armors, guilds, mod_guilds, npctypes, tactics, routines, heads,
               body_textures, faces, overlays, voices, npc_instances,
               xp_constants, log_topics, info_instances, waypoints):
        print(f"{fn.__name__:16} {len(fn())}")
