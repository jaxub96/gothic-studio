"""Routine tab - the daily schedule.

Two shifts, so "smith by day, sleep at night" is a couple of clicks instead of
a hand edit afterwards.
"""

from PyQt6.QtWidgets import QWidget

import gamedata
import labels
import startup_gen
import ui


def build(parent: QWidget, npc, handlers) -> None:
    layout = parent.layout()
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)

    ui.section(layout, "Day")

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
    layout.addSpacing(ui.SPACING)

    # ------------------------------------------------------------------ spawn
    ui.section(layout, "Spawn")
    spawn_worlds = startup_gen.worlds()
    if npc.spawn_world and npc.spawn_world not in spawn_worlds:
        spawn_worlds.append(npc.spawn_world)

    world_box = ui.dropdown(
        spawn_worlds, npc.spawn_world or (spawn_worlds[0] if spawn_worlds else None),
        lambda v: handlers.assignAttribute("spawn_world", lambda: v))
    spawn_wp = ui.search_input(
        waypoints, npc.spawn_waypoint, "Blank = the day waypoint",
        lambda v: handlers.assignAttribute("spawn_waypoint", lambda: v))

    def on_spawn(enabled):
        handlers.assignAttribute("spawn", lambda: int(enabled), int)
        for widget in (world_box, spawn_wp):
            widget.setEnabled(enabled and bool(spawn_worlds))

    layout.addWidget(ui.checkbox(
        "Put this NPC into the world", bool(npc.spawn), on_spawn,
        "Saving to the mod adds Wld_InsertNpc to STARTUP_<world> in "
        "Story/Startup.d. Without it the NPC exists but never appears."))
    layout.addSpacing(ui.GAP)
    ui.field(layout, "World", world_box,
             "Worlds that have a STARTUP function in Startup.d."
             if spawn_worlds else "Startup.d has no STARTUP_<world> function yet.")
    ui.field(layout, "Spawn waypoint", spawn_wp)
    on_spawn(bool(npc.spawn))

    layout.addStretch()
