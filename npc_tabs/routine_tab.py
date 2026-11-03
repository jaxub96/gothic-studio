"""Routine tab - the daily schedule.

Two shifts, so "smith by day, sleep at night" is a couple of clicks instead of
a hand edit afterwards.
"""

from PyQt6.QtWidgets import QWidget

import gamedata
import labels
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
    layout.addStretch()
