"""
npc_gen.py - turns an Npc into a .d file the compiler accepts.

The template mirrors Content/Story/NPC/GRD_001_Arideus.d, which is the
hand-corrected version of what the old NPC Studio produced. The old output
failed to compile on three calls:

    Mdl_SetNpcVisual  -> not an external in Gothic 2; use B_SetNpcVisual
    B_Scale           -> does not exist; B_SetNpcVisual scales internally
    TA_Position       -> does not exist; pick a real TA_* routine

No Qt in here.
"""

import re

import talents


def sanitize(text):
    return re.sub(r"[^A-Za-z0-9_]", "_", text or "")


def safe_name(npc):
    return sanitize(npc.name.strip()) or "NPC"


def guild_tag(npc):
    """GIL_MIL -> MIL, so the instance is named the way vanilla names them."""
    g = (npc.guild or "GIL_NONE").upper()
    tag = g[4:] if g.startswith("GIL_") else g
    return "MOD" if tag in ("NONE", "") else tag


def instance_name(npc):
    """e.g. GRD_001_Arideus - guild tag, zero-padded id, name."""
    return f"{guild_tag(npc)}_{npc.id}_{safe_name(npc)}"


def routine_name(npc):
    return f"Rtn_{npc.id}_{safe_name(npc)}_01"


def build_npc(npc):
    import gamedata
    inst = instance_name(npc)
    rtn = routine_name(npc)
    npctype = "NPCTYPE_FRIEND" if npc.friend else (npc.type or "NPCTYPE_MAIN")
    flags = "NPC_FLAG_IMMORTAL" if npc.immortal else "0"
    armor = npc.armor if npc.armor else "-1"
    wp = npc.waypoint or "WP_INTRO_FALL3"

    L = []
    a = L.append

    a(f"instance {inst} (Npc_Default)")
    a("{")
    a("\t// ---------------- primary ----------------")
    a(f'\tname\t\t\t= "{npc.name}";')
    a(f"\tguild\t\t\t= {npc.guild};")
    a(f"\tid\t\t\t\t= {npc.id};")
    a(f"\tvoice\t\t\t= {npc.voice};")
    a(f"\tflags\t\t\t= {flags};")
    a(f"\tnpctype\t\t\t= {npctype};")
    a("")
    a("\t// ---------------- attributes ----------------")
    if npc.use_chapter:
        # Careful: this overwrites .level with the chapter preset.
        a(f"\tB_SetAttributesToChapter\t(self, {npc.chapter});")
    else:
        a(f"\tlevel\t\t\t= {npc.level};")
        a(f"\tattribute[ATR_STRENGTH]\t\t= {npc.str};")
        a(f"\tattribute[ATR_DEXTERITY]\t= {npc.dex};")
        a(f"\tattribute[ATR_MANA_MAX]\t\t= {npc.mana};")
        a(f"\tattribute[ATR_MANA]\t\t\t= {npc.mana};")
        a(f"\tattribute[ATR_HITPOINTS_MAX]= {npc.hp};")
        a(f"\tattribute[ATR_HITPOINTS]\t= {npc.hp};")
    a("")
    a("\t// ---------------- visuals ----------------")
    a(f'\tB_SetNpcVisual\t\t(self, {npc.gender}, "{npc.head}", '
      f"{gamedata.face_code(npc.face)}, {npc.body_tex}, {armor});")
    a(f'\tMdl_ApplyOverlayMds\t(self, "{npc.overlay}");')
    a(f"\tMdl_SetModelFatness\t(self, {npc.fatness});")
    a("")
    a("\t// ---------------- fight ----------------")
    a(f"\tfight_tactic\t= {npc.fight};")
    a(f"\tB_SetFightSkills\t(self, {npc.level});")
    for talent, value in (("NPC_TALENT_1H", npc.t1h), ("NPC_TALENT_2H", npc.t2h),
                          ("NPC_TALENT_BOW", npc.bow), ("NPC_TALENT_CROSSBOW", npc.cbow),
                          ("NPC_TALENT_MAGE", npc.magic)):
        if value:
            a(f"\tNpc_SetTalentSkill\t(self, {talent}, {value});")
    a("")
    a("\t// ---------------- inventory ----------------")
    for entry in npc.inv_items:
        if entry.get("item"):
            a(f'\tCreateInvItems\t(self, {entry["item"]}, {entry.get("quantity", 1)});')
    if npc.ambient_inv:
        a("\tB_CreateAmbientInv\t(self);")
    extra = talents.lines(npc.talents)
    if extra:
        a("")
        a("\t// ---------------- talents ----------------")
        for line in extra:
            a(line)
    a("")
    a(f"\tdaily_routine\t= {rtn};")
    a("};")
    a("")
    a(f"FUNC VOID {rtn}()")
    a("{")
    for line in routine_lines(npc, wp):
        a(line)
    a("};")
    a("")
    return "\n".join(L)


def routine_lines(npc, wp=None):
    """The TA_ lines for the daily routine.

    Two shifts that wrap around the clock. With split_routine off both use the
    same activity and waypoint, which is the plain all-day schedule.
    """
    wp = wp or npc.waypoint or "WP_INTRO_FALL3"
    day_start = int(getattr(npc, "day_start", 8)) % 24
    night_start = int(getattr(npc, "night_start", 22)) % 24

    if not getattr(npc, "split_routine", False):
        return [f'\t{npc.routine}\t({day_start:02d},00,{day_start:02d},00,"{wp}");']

    night_rtn = getattr(npc, "night_routine", None) or npc.routine
    night_wp = getattr(npc, "night_waypoint", "") or wp
    return [
        f'\t{npc.routine}\t({day_start:02d},00,{night_start:02d},00,"{wp}");',
        f'\t{night_rtn}\t({night_start:02d},00,{day_start:02d},00,"{night_wp}");',
    ]


def default_filename(npc):
    """Vanilla naming: the instance name plus .d, e.g. GRD_001_Arideus.d"""
    return f"{instance_name(npc)}.d"


# --- Validation -------------------------------------------------------------

def validate(npc):
    """Check every identifier against what actually exists in Content/.

    Returns a list of human-readable problems. Empty list means the file
    should compile.
    """
    import gamedata

    problems = []

    if not npc.name.strip():
        problems.append("NPC has no name.")
    if not str(npc.id).strip().isdigit():
        problems.append(f"id '{npc.id}' is not a number.")

    checks = [
        ("guild", npc.guild, "guild"),
        ("npctype", npc.type, "NPC type"),
        ("tactic", npc.fight, "fight tactic"),
        ("routine", npc.routine, "daily routine"),
        ("head", npc.head, "head mesh"),
    ]
    if getattr(npc, "split_routine", False):
        checks.append(("routine", npc.night_routine, "night routine"))
    for kind, value, label in checks:
        if gamedata.unknown(kind, value):
            problems.append(f"Unknown {label}: {value}")

    if npc.armor not in ("-1", "", None) and gamedata.unknown("armor", npc.armor):
        problems.append(f"Unknown armor: {npc.armor}")

    for entry in npc.inv_items:
        if gamedata.unknown("item", entry.get("item")):
            problems.append(f"Unknown item: {entry.get('item')}")

    wps = gamedata.waypoints()
    if wps and npc.waypoint and npc.waypoint.upper() not in {w.upper() for w in wps}:
        problems.append(f"Waypoint not found in any world: {npc.waypoint}")

    existing = gamedata.npc_instances()
    inst = instance_name(npc)
    if inst in existing:
        problems.append(f"Instance {inst} already exists in {existing[inst]}")

    return problems


# --- Parsing ----------------------------------------------------------------

_TALENT_FIELDS = {"NPC_TALENT_1H": "t1h", "NPC_TALENT_2H": "t2h", "NPC_TALENT_BOW": "bow",
                  "NPC_TALENT_CROSSBOW": "cbow", "NPC_TALENT_MAGE": "magic"}
_ATTRIBUTES = {"ATR_STRENGTH": "str", "ATR_DEXTERITY": "dex",
               "ATR_MANA_MAX": "mana", "ATR_HITPOINTS_MAX": "hp"}
_SHIFT = re.compile(r'(TA_\w+)\s*\(\s*(\d+)\s*,\s*\d+\s*,\s*(\d+)\s*,\s*\d+\s*,\s*"([^"]*)"\s*\)', re.I)


def _skill_level(percent):
    """Gothic's 30 / 60 percent boundaries between the talent levels."""
    return 2 if percent >= 60 else 1 if percent >= 30 else 0


def _args(call):
    """The comma-separated arguments of `Name (a, "b, c", d)`, strings kept whole."""
    inner = call[call.index("(") + 1:call.rindex(")")]
    parts, cur, quoted = [], "", False
    for ch in inner:
        if ch == '"':
            quoted = not quoted
        if ch == "," and not quoted:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    return parts


def parse_npc(text):
    """Read an NPC instance back into an Npc: this tool's files and vanilla-style ones.

    Returns None if there is no Npc_Default instance in `text`. Whatever the
    editor has no field for (aivars, EquipItem, B_GiveNpcTalents, extra routine
    functions, ...) is listed in `npc.unread` so the caller can say so instead
    of dropping it quietly. Names are matched to the mod's own spelling where
    they exist, since vanilla scripts mix upper and lower case freely.
    Talent skills that belong to a recipe list come back as `npc.master_talents`;
    the recipes live in the teaching dialog (see teach_gen.parse_teaching).
    """
    import gamedata
    import talents
    from daedalus_read import (assignment, canon, functions, instances, norm,
                               split_statements, unquote)
    from npc_model import Npc

    found = [i for i in instances(text) if i[1].lower() == "npc_default"]
    if not found:
        return None
    _, _, body = found[0]
    funcs = functions(text)
    npc = Npc()
    unread = []
    skill_ids = {e["id"] for _, skills, _ in talents.GROUPS for e in skills}
    explicit_level = fight_percent = None
    explicit_weapons = False
    overlay_seen = False
    routine_name = ""
    npc.master_talents = set()

    def number(value, default):
        try:
            return int(value)
        except ValueError:
            return default

    for raw, _comment in split_statements(body):
        st = norm(raw)
        low = st.lower()
        kv = assignment(raw) if "(" not in st.split("=")[0] else None
        if kv:
            key, value = kv[0].lower(), kv[1]
            if key == "name":
                npc.name = unquote(value)
            elif key == "guild":
                npc.guild = canon(value, gamedata.guilds())
            elif key == "id":
                npc.id = str(number(value, 1)).zfill(3)
            elif key == "voice":
                npc.voice = number(value, npc.voice)
            elif key == "flags":
                npc.immortal = int("immortal" in value.lower())
            elif key == "npctype":
                if value.upper() == "NPCTYPE_FRIEND":
                    npc.friend = 1
                else:
                    npc.type = canon(value, gamedata.npctypes())
            elif key == "level":
                explicit_level = number(value, 1)
                npc.level = explicit_level
            elif key.startswith("attribute[") and key[10:-1].upper() in _ATTRIBUTES:
                setattr(npc, _ATTRIBUTES[key[10:-1].upper()], number(value, 10))
            elif key == "attribute[atr_mana]" or key == "attribute[atr_hitpoints]":
                pass
            elif key == "fight_tactic":
                npc.fight = canon(value, gamedata.tactics())
            elif key == "daily_routine":
                routine_name = value.lower()
            else:
                unread.append(st)
            continue

        m = re.match(r"(\w+)\s*\(", st)
        call = m.group(1).lower() if m else ""
        args = _args(st) if m else []
        if call == "b_setattributestochapter" and len(args) >= 2:
            npc.use_chapter, npc.chapter = True, number(args[1], 1)
        elif call == "b_setnpcvisual" and len(args) >= 6:
            npc.gender = args[1].upper()
            npc.head = canon(unquote(args[2]).rstrip(". "), gamedata.heads())
            npc.face = canon(gamedata.face_from_code(args[3]), gamedata.faces())
            npc.body_tex = canon(args[4], gamedata.body_textures())
            npc.armor = "-1" if args[5] in ("-1", "NO_ARMOR") else canon(args[5], gamedata.armors())
        elif call == "mdl_applyoverlaymds" and len(args) >= 2 and not overlay_seen:
            npc.overlay = canon(unquote(args[1]), gamedata.overlays())
            overlay_seen = True
        elif call == "mdl_setmodelfatness" and len(args) >= 2:
            try:
                npc.fatness = float(args[1])
            except ValueError:
                unread.append(st)
        elif call == "b_setfightskills" and len(args) >= 2:
            fight_percent = number(args[1], 0)
        elif call == "npc_settalentskill" and len(args) >= 3:
            const, level = args[1].upper(), number(args[2], 1)
            if const in _TALENT_FIELDS:
                setattr(npc, _TALENT_FIELDS[const], level)
                explicit_weapons = True
            elif const in skill_ids:
                npc.talents.add(const)
            else:
                npc.master_talents.add(const)
        elif call in ("createinvitems", "createinvitem") and len(args) >= 2:
            item = canon(args[1], gamedata.items())
            qty = number(args[2], 1) if len(args) > 2 else 1
            for entry in npc.inv_items:
                if entry["item"] == item:
                    entry["quantity"] += qty
                    break
            else:
                npc.inv_items.append({"item": item, "quantity": qty})
        elif call == "b_createambientinv":
            npc.ambient_inv = 1
        elif low:
            unread.append(st)

    # Vanilla scripts set every weapon talent from one percentage. This tool's own
    # files write `level` instead and list the talents explicitly.
    if fight_percent is not None and explicit_level is None and not explicit_weapons:
        for attr in ("t1h", "t2h", "bow", "cbow"):
            setattr(npc, attr, _skill_level(fight_percent))

    name = routine_name
    if name and name in funcs:
        shifts, other = [], 0
        for raw, _comment in split_statements(funcs[name][1]):
            s = _SHIFT.search(norm(raw))
            if s:
                shifts.append(s.groups())
            elif norm(raw):
                other += 1
        if shifts:
            npc.routine, day, _, npc.waypoint = shifts[0]
            npc.routine = canon(npc.routine, gamedata.routines())
            npc.day_start = int(day)
            if len(shifts) > 1:
                npc.split_routine = True
                night_rtn, night, _, npc.night_waypoint = shifts[1]
                npc.night_routine = canon(night_rtn, gamedata.routines())
                npc.night_start = int(night)
            if len(shifts) > 2:
                unread.append(f"{len(shifts) - 2} further routine shift(s) in {funcs[name][0]}")
        if other:
            unread.append(f"{other} non-schedule statement(s) in {funcs[name][0]}")
    elif name:
        unread.append(f"routine function {name} not found in this file")

    others = [f[0] for key, f in funcs.items() if key != name]
    if others:
        unread.append("other functions: " + ", ".join(others))
    npc.unread = unread
    return npc
