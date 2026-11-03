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
      f"{npc.face}, {npc.body_tex}, {armor});")
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
