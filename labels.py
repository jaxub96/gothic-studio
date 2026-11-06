"""
labels.py - readable names for Daedalus constants.

The lists in the app are scraped from Content/, so they arrive as raw
identifiers: GIL_STRF, NPCTYPE_OCAMBIENT, FAI_HUMAN_COWARD. Those are precise
but not obvious, and a newcomer has no way to know GIL_STRF means "prisoner".

Every combo shows "Readable name  ·  RAW_CONSTANT" so you get both: the meaning
while you choose, and the exact identifier that ends up in the file.

Only presentation lives here. Nothing in this file affects generated code, and
an unknown constant just shows itself - adding content to the mod never breaks
the UI.
"""

GUILD = {
    "GIL_NONE": "No guild",
    "GIL_PAL": "Paladin",
    "GIL_MIL": "Militia",
    "GIL_VLK": "Citizen",
    "GIL_KDF": "Fire Mage",
    "GIL_NOV": "Novice",
    "GIL_DJG": "Dragon Hunter",
    "GIL_SLD": "Mercenary",
    "GIL_BAU": "Farmer",
    "GIL_BDT": "Bandit",
    "GIL_STRF": "Prisoner",
    "GIL_DMT": "Dementor",
    "GIL_OUT": "Outlander",
    "GIL_PIR": "Pirate",
    "GIL_KDW": "Water Mage",
}

NPCTYPE = {
    "NPCTYPE_AMBIENT": "Ambient (background)",
    "NPCTYPE_MAIN": "Main (story)",
    "NPCTYPE_FRIEND": "Friend",
    "NPCTYPE_OCAMBIENT": "Old Camp ambient",
    "NPCTYPE_OCMAIN": "Old Camp main",
    "NPCTYPE_BL_AMBIENT": "Addon ambient",
    "NPCTYPE_BL_MAIN": "Addon main",
    "NPCTYPE_TAL_AMBIENT": "Valley ambient",
}

TACTIC = {
    "FAI_HUMAN_COWARD": "Coward - flees",
    "FAI_HUMAN_NORMAL": "Normal",
    "FAI_HUMAN_STRONG": "Strong",
    "FAI_HUMAN_MASTER": "Master",
}

HEAD = {
    "HUM_HEAD_BALD": "Bald",
    "HUM_HEAD_FATBALD": "Fat, bald",
    "HUM_HEAD_FIGHTER": "Fighter",
    "HUM_HEAD_PONY": "Ponytail",
    "HUM_HEAD_PSIONIC": "Psionic",
    "HUM_HEAD_BABE": "Female",
    **{f"HUM_HEAD_BABE{n}": f"Female {n}" for n in range(1, 9)},
    "HUM_HEAD_BABEHAIR": "Female, long hair",
}

BODY = {
    "BodyTex_Babe_4": "Fair", "BodyTex_Babe_5": "Light tan", "BodyTex_Babe_6": "Tan",
    "BodyTex_Babe_7": "Dark", "BodyTex_Babe_11": "Black leather outfit",
    "BodyTex_Babe_12": "Lace outfit",
    "BodyTex_P": "Pale",
    "BodyTex_N": "Normal",
    "BodyTex_L": "Latino",
    "BodyTex_B": "Black",
    "BodyTex_T": "Tattooed",
    "BodyTex_Player": "Player",
    "BodyTex_Man_9": "Player 2",
}

OVERLAY = {
    "HUMANS_MILITIA.MDS": "Militia - upright, martial",
    "HUMANS_RELAXED.MDS": "Relaxed - casual",
    "HUMANS_ARROGANCE.MDS": "Arrogant - swaggering",
    "HUMANS_MAGE.MDS": "Mage - measured",
    "HUMANS_TIRED.MDS": "Tired - weary",
    "HUMANS_BABE.MDS": "Female",
}

# Armor tree groups. The tag is pulled out of ITAR_<TAG>_<weight>.
ARMOR_GROUP = dict(GUILD, **{
    "VLK": "Citizen", "MIL": "Militia", "PAL": "Paladin", "KDF": "Fire Mage",
    "KDW": "Water Mage", "NOV": "Novice", "DJG": "Dragon Hunter",
    "SLD": "Mercenary", "BAU": "Farmer", "BDT": "Bandit", "STRF": "Prisoner",
    "DMT": "Dementor", "OUT": "Outlander", "PIR": "Pirate", "LEG": "Legionnaire",
    "BABE": "Female", "BAUBABE": "Farm woman", "VLKBABE": "Townswoman",
    "RANGER": "Ranger", "XARDAS": "Xardas", "CRAWLER": "Crawler armor",
    "FAKE": "Disguise", "GRD": "Guard", "STT": "Shadow", "ORG": "Rogue",
})

# Common routines. Anything not listed shows its raw TA_ name, which is
# already fairly readable.
ROUTINE = {
    "TA_Stand_WP": "Stand still",
    "TA_Stand_Guarding": "Stand guard",
    "TA_Stand_ArmsCrossed": "Stand, arms crossed",
    "TA_Stand_Eating": "Stand, eating",
    "TA_Stand_Drinking": "Stand, drinking",
    "TA_Stand_Sweeping": "Sweeping",
    "TA_Sit_Bench": "Sit on a bench",
    "TA_Sit_Campfire": "Sit at a campfire",
    "TA_Sit_Chair": "Sit on a chair",
    "TA_Sit_Throne": "Sit on a throne",
    "TA_Sleep": "Sleep",
    "TA_Sleep_Deep": "Sleep deeply",
    "TA_Smith_Anvil": "Smith at an anvil",
    "TA_Smith_Fire": "Smith at the forge",
    "TA_Smith_Sharp": "Sharpen a blade",
    "TA_Smith_Cool": "Cool a blade",
    "TA_Cook_Cauldron": "Cook at a cauldron",
    "TA_Cook_Pan": "Cook at a pan",
    "TA_Cook_Stove": "Cook at a stove",
    "TA_Pray_Innos": "Pray to Innos",
    "TA_Pray_Sleeper": "Pray to the Sleeper",
    "TA_Practice_Sword": "Practise swordplay",
    "TA_Practice_Magic": "Practise magic",
    "TA_Read_Bookstand": "Read at a bookstand",
    "TA_Pick_Ore": "Mine ore",
    "TA_Pick_FP": "Pick at a spot",
    "TA_Rake_FP": "Rake a field",
    "TA_Saw": "Saw wood",
    "TA_Repair_Hut": "Repair a hut",
    "TA_Smoke_Joint": "Smoke",
    "TA_Smoke_Waterpipe": "Smoke a waterpipe",
    "TA_Play_Lute": "Play a lute",
    "TA_Dance": "Dance",
    "TA_Potion_Alchemy": "Brew potions",
    "TA_Stomp_Herb": "Grind herbs",
    "TA_Wash_FP": "Wash",
    "TA_Sweep_FP": "Sweep",
    "TA_Roast_Scavenger": "Roast a scavenger",
    "TA_Guard_Passage": "Guard a passage",
    "TA_Guard_Hammer": "Guard with a hammer",
    "TA_Circle": "Patrol a circle",
    "TA_Smalltalk": "Chat with someone",
    "TA_Pee": "Relieve themselves",
}

SEP = "  ·  "


def pretty(table, constant):
    """'Militia  ·  GIL_MIL', or just the constant when we have no name for it."""
    name = table.get(constant) or table.get(str(constant).upper())
    return f"{name}{SEP}{constant}" if name else str(constant)


def raw(text):
    """Inverse of pretty(): pull the constant back out of a combo entry."""
    return str(text).split(SEP)[-1].strip()


def label_list(table, constants):
    return [pretty(table, c) for c in constants]
