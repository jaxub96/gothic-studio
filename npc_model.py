"""
npc_model.py - one plain object holding everything an NPC instance needs.

No Qt in here. The tabs mutate this; npc_gen.py reads it.
Defaults are Gothic 2 NotR values that exist in this install.
"""


def new_routine(activity="TA_Stand_WP", start=(8, 0), end=(8, 0), waypoint=""):
    return {"activity": activity, "start": list(start), "end": list(end),
            "waypoint": waypoint}


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
        # The daily schedule, one entry per TA_ line. Times are [hour, minute];
        # an entry whose start equals its end runs all day. A blank waypoint
        # means "the first routine's waypoint".
        self.routines = [new_routine()]

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

    # The first routine stands in for "the NPC's routine" wherever one value is
    # wanted - the spawn waypoint defaults to its waypoint, for instance.
    @property
    def routine(self):
        return self.routines[0]["activity"] if self.routines else "TA_Stand_WP"

    @routine.setter
    def routine(self, value):
        if not self.routines:
            self.routines.append(new_routine())
        self.routines[0]["activity"] = value

    @property
    def waypoint(self):
        return self.routines[0]["waypoint"] if self.routines else ""

    @waypoint.setter
    def waypoint(self, value):
        if not self.routines:
            self.routines.append(new_routine())
        self.routines[0]["waypoint"] = value
