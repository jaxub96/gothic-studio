"""
talents.py - Gothic's crafting, gathering and utility talents, grouped.

Taken from Constants.d in the Gothic II MDK. No Qt in here.

Two kinds of entry, both keyed by the Daedalus they emit:

  skill   Npc_SetTalentSkill (self, NPC_TALENT_X, 1);   a talent with no recipes
  recipe  PLAYER_TALENT_X[CONST] = TRUE;                 one thing a talent can make

Recipes are Gothic's global PLAYER_TALENT_* flags: the game keeps one set, for
the hero, so ticking one on an NPC unlocks it for the hero when that NPC is
created. The skills are per NPC.
"""

SKILL_LINE = "\tNpc_SetTalentSkill\t(self, {}, 1);"
RECIPE_LINE = "\t{}[{}]\t= TRUE;"


def _skill(const, label):
    return {"id": const, "label": label, "line": SKILL_LINE.format(const)}


def _recipes(array, items):
    return [{"id": f"{array}[{c}]", "label": label,
             "line": RECIPE_LINE.format(array, c)} for c, label in items]


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
    ("Alchemy and runes", [],
     [("Potions", "NPC_TALENT_ALCHEMY", _recipes("PLAYER_TALENT_ALCHEMY", POTIONS)),
      ("Runes", "NPC_TALENT_RUNES", _recipes("PLAYER_TALENT_RUNES", RUNES))]),
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
    """Daedalus lines for the ticked ids, in the order the tab lists them.

    A ticked recipe brings its master talent along, once, ahead of the recipes.
    """
    out = []
    for _, skills, recipe_lists in GROUPS:
        out += [e["line"] for e in skills if e["id"] in selected]
        for _, master, recipes in recipe_lists:
            ticked = [r["line"] for r in recipes if r["id"] in selected]
            if ticked:
                out += [SKILL_LINE.format(master), *ticked]
    return out
