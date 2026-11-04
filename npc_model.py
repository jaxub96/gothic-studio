"""
npc_model.py - one plain object holding everything an NPC instance needs.

No Qt in here. The tabs mutate this; npc_gen.py reads it.
Defaults are Gothic 2 NotR values that exist in this install.
"""


class Npc:
    def __init__(self):
        # --- Identity ---
        self.name = ""
        self.id = "001"
        self.guild = "GIL_NONE"
        self.type = "NPCTYPE_MAIN"
        self.level = 1
        self.immortal = 0
        self.friend = 0

        # --- Attributes ---
        # use_chapter=True emits B_SetAttributesToChapter instead, which is
        # convenient but OVERWRITES level with the chapter's preset.
        self.use_chapter = False
        self.chapter = 1
        self.str = 10
        self.dex = 10
        self.mana = 10
        self.hp = 40

        # --- Visual ---
        self.gender = "MALE"
        self.voice = 1
        self.fatness = 0
        self.head = "HUM_HEAD_PONY"
        self.face = "Face_N_Player"
        self.body_tex = "BodyTex_N"
        self.overlay = "HUMANS_MILITIA.MDS"
        self.armor = "-1"                 # -1 == no armor

        # --- Fight ---
        self.fight = "FAI_HUMAN_STRONG"
        self.t1h = 0
        self.t2h = 0
        self.bow = 0
        self.cbow = 0
        self.magic = 0

        # --- Routine ---
        # Two shifts. With split_routine off, the night shift mirrors the day
        # one and you get the same single-activity schedule as before.
        self.routine = "TA_Stand_WP"
        self.waypoint = ""
        self.split_routine = False
        self.night_routine = "TA_Sleep"
        self.night_waypoint = ""
        self.day_start = 8            # hour the day shift begins
        self.night_start = 22         # hour the night shift begins

        # --- Spawn ---
        # Wld_InsertNpc in Startup.d, written when the NPC is saved to the mod.
        # Not part of the NPC's own .d file, so reading a file back does not
        # set these; the app looks them up in Startup.d (startup_gen.find_spawn).
        self.spawn = 0
        self.spawn_world = ""         # blank = the first world Startup.d knows
        self.spawn_waypoint = ""      # blank = the day waypoint

        # --- Inventory ---  [{"item": str, "quantity": int}, ...]
        self.inv_items = []
        self.talents = set()          # ids from talents.py
        self.ambient_inv = 0          # emit B_CreateAmbientInv (self)
