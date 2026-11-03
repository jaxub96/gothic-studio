"""Skills tab - fight tactic, weapon talents, and the daily routine.

Fight tactics come from the FAI_*.d filenames. The old data table carried a
".d" on every value, so picking anything emitted `fight_tactic = FAI_X.d;`,
which is a parse error.

The routine is two shifts, so "smith by day, sleep at night" is a couple of
clicks instead of a hand edit afterwards.
"""

from PyQt6.QtWidgets import QWidget

import gamedata
import labels
import ui

TALENTS = [("1H weapon", "t1h"), ("2H weapon", "t2h"),
           ("Bow", "bow"), ("Crossbow", "cbow")]
LEVELS = [("None", 0), ("Apprentice", 1), ("Master", 2)]
CIRCLES = [("No magic", 0)] + [(f"Circle {n}", n) for n in range(1, 7)]


def build(parent: QWidget, npc, handlers) -> None:
    layout = parent.layout()
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)

    ui.section(layout, "Combat")

    ui.field(layout, "Fight tactic",
             ui.dropdown(labels.label_list(labels.TACTIC, gamedata.tactics()),
                         labels.pretty(labels.TACTIC, npc.fight),
                         lambda t: handlers.assignAttribute(
                             "fight", lambda: labels.raw(t))))

    for text, attr in TALENTS:
        layout.addWidget(ui.radio_row(
            text, LEVELS, getattr(npc, attr),
            lambda v, a=attr: handlers.assignAttribute(a, lambda: v, int)))
    layout.addSpacing(ui.SPACING)

    ui.field_row(layout, "Magic circle",
                 ui.choice(CIRCLES, npc.magic,
                           lambda v: handlers.assignAttribute(
                               "magic", lambda: v, int)))

    # ------------------------------------------------------------- routine
    ui.section(layout, "Daily routine")

    routines = labels.label_list(labels.ROUTINE, gamedata.routines())
    waypoints = gamedata.waypoints()

    day_time = ui.spin(0, 23, npc.day_start,
                       lambda v: handlers.assignAttribute("day_start", lambda: v, int),
                       suffix=":00")
    ui.field_row(layout, "Starts at", day_time)

    ui.field(layout, "Activity",
             ui.search_dropdown(routines, labels.pretty(labels.ROUTINE, npc.routine),
                                lambda t: handlers.assignAttribute(
                                    "routine", lambda: labels.raw(t))))

    ui.field(layout, "Waypoint",
             ui.search_input(waypoints, npc.waypoint,
                             on_change=lambda v: handlers.assignAttribute(
                                 "waypoint", lambda: v)),
             f"{len(waypoints)} waypoints in the loaded worlds."
             if waypoints else "No worldnames.json - type the name by hand.")

    night_time = ui.spin(0, 23, npc.night_start,
                         lambda v: handlers.assignAttribute(
                             "night_start", lambda: v, int),
                         suffix=":00")
    night_activity = ui.search_dropdown(
        routines, labels.pretty(labels.ROUTINE, npc.night_routine),
        lambda t: handlers.assignAttribute("night_routine",
                                           lambda: labels.raw(t)))
    night_waypoint = ui.search_input(
        waypoints, npc.night_waypoint, "Blank = same as the day waypoint",
        lambda v: handlers.assignAttribute("night_waypoint", lambda: v))

    def on_split(enabled):
        handlers.assignAttribute("split_routine", lambda: int(enabled), int)
        for widget in (night_time, night_activity, night_waypoint):
            widget.setEnabled(enabled)

    split = ui.checkbox("Different routine at night", bool(npc.split_routine),
                        on_split)
    layout.addWidget(split)
    layout.addSpacing(ui.GAP)

    ui.field_row(layout, "Starts at", night_time)
    ui.field(layout, "Activity", night_activity)
    ui.field(layout, "Waypoint", night_waypoint)

    on_split(bool(npc.split_routine))
    layout.addStretch()
