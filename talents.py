"""
talents.py - Gothic's crafting, gathering and utility talents, grouped.

Taken from Constants.d in the Gothic II MDK. No Qt in here.

Two kinds of entry:

  skill   a talent on its own (theft, regeneration, fire master)
  recipe  one thing a talent can make; its talent is the list's master

Ticking an entry makes the NPC know the talent
(Npc_SetTalentSkill (self, NPC_TALENT_X, 1);) and, where Gothic has a teaching
function for it, teach it: see teachable() and teach_gen.py.
"""

SKILL_LINE = "\tNpc_SetTalentSkill\t(self, {}, 1);"


def _skill(const, label):
    return {"id": const, "label": label, "line": SKILL_LINE.format(const)}


def _recipes(array, items):
    return [{"id": f"{array}[{c}]", "label": label} for c, label in items]


POTIONS = [
    ("POTION_Health_01", "Health essence"), ("POTION_Health_02", "Health extract"),
    ("POTION_Health_03", "Health elixir"), ("POTION_Health_04", "Pure health"),
    ("POTION_Mana_01", "Mana essence"), ("POTION_Mana_02", "Mana extract"),
    ("POTION_Mana_03", "Mana elixir"), ("POTION_Mana_04", "Pure mana"),
    ("POTION_Speed", "Speed potion"), ("POTION_Perm_STR", "Elixir of strength"),
    ("POTION_Perm_DEX", "Elixir of dexterity"), ("POTION_Perm_Mana", "Elixir of spirit"),
    ("POTION_Perm_Health", "Elixir of life"), ("POTION_MegaDrink", "Mega drink"),
    ("CHARGE_Innoseye", "Eye of Innos charge"),
]

RUNES = [
    ("SPL_Light", "Light"), ("SPL_Firebolt", "Fire bolt"),
    ("SPL_LightHeal", "Light healing"), ("SPL_SummonGoblinSkeleton", "Summon goblin skeleton"),
    ("SPL_Zap", "Zap"), ("SPL_Icebolt", "Ice bolt"),
    ("SPL_InstantFireball", "Fireball"), ("SPL_SummonWolf", "Summon wolf"),
    ("SPL_WindFist", "Wind fist"), ("SPL_Sleep", "Sleep"),
    ("SPL_MediumHeal", "Medium healing"), ("SPL_LightningFlash", "Lightning flash"),
    ("SPL_ChargeFireball", "Charged fireball"), ("SPL_SummonSkeleton", "Summon skeleton"),
    ("SPL_Fear", "Fear"), ("SPL_IceCube", "Ice cube"),
    ("SPL_ChargeZap", "Charged zap"), ("SPL_SummonGolem", "Summon golem"),
    ("SPL_DestroyUndead", "Destroy undead"), ("SPL_Pyrokinesis", "Pyrokinesis"),
    ("SPL_Firestorm", "Fire storm"), ("SPL_IceWave", "Ice wave"),
    ("SPL_SummonDemon", "Summon demon"), ("SPL_FullHeal", "Full healing"),
    ("SPL_Firerain", "Fire rain"), ("SPL_BreathOfDeath", "Breath of death"),
    ("SPL_MassDeath", "Mass death"), ("SPL_ArmyOfDarkness", "Army of darkness"),
    ("SPL_Shrink", "Shrink"),
]

WEAPONS = [
    ("WEAPON_Common", "Common weapons"),
    ("WEAPON_1H_Special_01", "1H special 1"), ("WEAPON_2H_Special_01", "2H special 1"),
    ("WEAPON_1H_Special_02", "1H special 2"), ("WEAPON_2H_Special_02", "2H special 2"),
    ("WEAPON_1H_Special_03", "1H special 3"), ("WEAPON_2H_Special_03", "2H special 3"),
    ("WEAPON_1H_Special_04", "1H special 4"), ("WEAPON_2H_Special_04", "2H special 4"),
    ("WEAPON_1H_Harad_01", "Harad 1H 1"), ("WEAPON_1H_Harad_02", "Harad 1H 2"),
    ("WEAPON_1H_Harad_03", "Harad 1H 3"), ("WEAPON_1H_Harad_04", "Harad 1H 4"),
]

TROPHIES = [
    ("TROPHY_Teeth", "Teeth"), ("TROPHY_Claws", "Claws"), ("TROPHY_Fur", "Fur"),
    ("TROPHY_ReptileSkin", "Reptile skin"), ("TROPHY_Heart", "Heart (golems, demons)"),
    ("TROPHY_ShadowHorn", "Shadowbeast horn"), ("TROPHY_FireTongue", "Firewaran tongue"),
    ("TROPHY_BFWing", "Bloodfly wing"), ("TROPHY_BFSting", "Bloodfly sting"),
    ("TROPHY_Mandibles", "Mandibles"), ("TROPHY_CrawlerPlate", "Crawler plate"),
    ("TROPHY_DrgSnapperHorn", "Dragon snapper horn"), ("TROPHY_DragonScale", "Dragon scale"),
    ("TROPHY_DragonBlood", "Dragon blood"),
]

LANGUAGES = [("LANGUAGE_1", "Language 1"), ("LANGUAGE_2", "Language 2"),
             ("LANGUAGE_3", "Language 3")]

WISP = [
    ("WISPSKILL_NF", "Melee weapons"), ("WISPSKILL_FF", "Ranged weapons"),
    ("WISPSKILL_NONE", "Nothing"), ("WISPSKILL_RUNE", "Runes"),
    ("WISPSKILL_MAGIC", "Magic items"), ("WISPSKILL_FOOD", "Food"),
    ("WISPSKILL_POTIONS", "Potions"),
]

#: title, [skills], [(recipe title, master talent, [recipes])]
#: A recipe list has no checkbox for its master talent: ticking any recipe adds
#: `Npc_SetTalentSkill (self, <master>, 1)` by itself.
GROUPS = [
    ("Alchemy", [],
     [("Potions", "NPC_TALENT_ALCHEMY", _recipes("PLAYER_TALENT_ALCHEMY", POTIONS))]),
    ("Runes", [],
     [("Runes", "NPC_TALENT_RUNES", _recipes("PLAYER_TALENT_RUNES", RUNES))]),
    ("Smithing", [],
     [("Weapons", "NPC_TALENT_SMITH", _recipes("PLAYER_TALENT_SMITH", WEAPONS))]),
    ("Hunting", [],
     [("Trophies", "NPC_TALENT_TAKEANIMALTROPHY",
       _recipes("PLAYER_TALENT_TAKEANIMALTROPHY", TROPHIES))]),
    ("Theft",
     [_skill("NPC_TALENT_PICKLOCK", "Lockpicking"), _skill("NPC_TALENT_PICKPOCKET", "Pickpocketing"),
      _skill("NPC_TALENT_SNEAK", "Sneaking"), _skill("NPC_TALENT_ACROBAT", "Acrobatics")],
     []),
    ("Special",
     [_skill("NPC_TALENT_REGENERATE", "Regeneration"), _skill("NPC_TALENT_FIREMASTER", "Fire master")],
     [("Languages", "NPC_TALENT_FOREIGNLANGUAGE", _recipes("PLAYER_TALENT_FOREIGNLANGUAGE", LANGUAGES)),
      ("Wisp finds", "NPC_TALENT_WISPDETECTOR", _recipes("PLAYER_TALENT_WISPDETECTOR", WISP))]),
]


def lines(selected):
    """Npc_SetTalentSkill lines for the ticked ids, in the order the tab lists them.

    A ticked recipe brings its master talent along, once.
    """
    out = []
    for _, skills, recipe_lists in GROUPS:
        out += [e["line"] for e in skills if e["id"] in selected]
        for _, master, recipes in recipe_lists:
            if any(r["id"] in selected for r in recipes):
                out.append(SKILL_LINE.format(master))
    return out


# ----------------------------------------------------------------- teaching

TEACH_FUNC = {
    "NPC_TALENT_ALCHEMY": "B_TeachPlayerTalentAlchemy",
    "NPC_TALENT_RUNES": "B_TeachPlayerTalentRunes",
    "NPC_TALENT_SMITH": "B_TeachPlayerTalentSmith",
    "NPC_TALENT_TAKEANIMALTROPHY": "B_TeachPlayerTalentTakeAnimalTrophy",
    "NPC_TALENT_FOREIGNLANGUAGE": "B_TeachPlayerTalentForeignLanguage",
    "NPC_TALENT_WISPDETECTOR": "B_TeachPlayerTalentWispDetector",
}

#: B_TeachThiefTalent covers these four; regeneration and fire master have no
#: teaching function in the scripts.
THIEF_TALENTS = ("NPC_TALENT_PICKLOCK", "NPC_TALENT_PICKPOCKET",
                 "NPC_TALENT_SNEAK", "NPC_TALENT_ACROBAT")


def group_titles():
    return [title for title, _, _ in GROUPS]


def teachable(title):
    """What a teacher in this group can offer, as dicts for teach_gen.

    Each has the id (as ticked in the tab), the label, the constant (for naming), the Daedalus condition that
    is true while the hero has not learned it, the learning-point cost
    expression, and the teaching call.
    """
    items = []
    for group, skills, recipe_lists in GROUPS:
        if group != title:
            continue
        for e in skills:
            if e["id"] in THIEF_TALENTS:
                items.append({
                    "id": e["id"], "label": e["label"], "const": e["id"],
                    "unknown": f"Npc_GetTalentSkill (other, {e['id']}) == 0",
                    "cost": f"B_GetLearnCostTalent (other, {e['id']}, 1)",
                    "call": f"B_TeachThiefTalent (self, other, {e['id']})"})
        for _, master, recipes in recipe_lists:
            for r in recipes:
                array, const = r["id"].rstrip("]").split("[")
                items.append({
                    "id": r["id"], "label": r["label"], "const": const,
                    "unknown": f"{r['id']} == FALSE",
                    "cost": f"B_GetLearnCostTalent (other, {master}, {const})",
                    "call": f"{TEACH_FUNC[master]} (self, other, {const})"})
    return items
