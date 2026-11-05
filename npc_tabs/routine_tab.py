"""Routine tab - the daily schedule.

A list of routines, each a time range with an activity and a waypoint - one
TA_ line each in the generated Rtn_ function. Add as many as the day needs:
smith 08-20, drink 20-23, sleep 23-08. The line under the list says whether
the day is fully covered, because a gap leaves the NPC standing idle.
"""

from PyQt6.QtWidgets import QVBoxLayout, QWidget

import gamedata
import labels
import npc_gen
import startup_gen
import ui
from npc_model import new_routine


def build(parent: QWidget, npc, handlers) -> None:
    layout = parent.layout()
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)

    ui.section(layout, "Daily routine")

    activities = labels.label_list(labels.ROUTINE, gamedata.routines())
    waypoints = gamedata.waypoints()

    holder = QWidget()
    rows = QVBoxLayout(holder)
    rows.setContentsMargins(0, 0, 0, 0)
    rows.setSpacing(ui.GAP)
    layout.addWidget(holder)
    layout.addSpacing(ui.GAP)

    coverage = ui.hint("")

    def update_coverage():
        if not npc.routines:
            coverage.setText("No routine yet - add one so the NPC has something to do.")
            return
        gaps, overlaps = npc_gen.routine_coverage(npc.routines)
        notes = []
        if gaps:
            notes.append("Nothing to do " + ", ".join(
                npc_gen.describe_span(g) for g in gaps))
        if overlaps:
            notes.append("Overlap " + ", ".join(
                npc_gen.describe_span(o) for o in overlaps))
        coverage.setText("  ·  ".join(notes) if notes
                         else "Covers the whole day.")

    def changed():
        update_coverage()
        handlers.refresh()

    def set_field(r, key, value):
        r[key] = value
        changed()

    def rebuild():
        while rows.count():
            item = rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for i, r in enumerate(npc.routines):
            rows.addWidget(routine_card(i, r))
        update_coverage()

    def routine_card(index, r):
        frame, lay = ui.card()

        head = ui.row()
        head.addWidget(ui.heading(f"Routine {index + 1}"))
        head.addStretch()
        if len(npc.routines) > 1:
            head.addWidget(ui.button("Remove", lambda: remove(index), ui.SUBTLE,
                                     "Delete this routine", compact=True))
        lay.addLayout(head)
        lay.addSpacing(ui.GAP)

        times = ui.row()
        times.addWidget(ui.time_input(
            *r["start"], lambda h, m: set_field(r, "start", [h, m])))
        times.addWidget(ui.label("to"))
        times.addWidget(ui.time_input(
            *r["end"], lambda h, m: set_field(r, "end", [h, m])))
        times.addStretch()
        span = QWidget()
        span.setLayout(times)
        span.setStyleSheet("background:transparent;")
        ui.field(lay, "Time", span,
                 "Same start and end = all day." if index == 0 and
                 len(npc.routines) == 1 else None)

        ui.field(lay, "Activity", ui.search_dropdown(
            activities, labels.pretty(labels.ROUTINE, r["activity"]),
            lambda t: set_field(r, "activity", labels.raw(t))))

        ui.field(lay, "Waypoint", ui.search_input(
            waypoints, r.get("waypoint", ""),
            "" if index == 0 else "Blank = routine 1's waypoint",
            lambda v: set_field(r, "waypoint", v)))
        return frame

    def add():
        """A new routine fills the first free time; on a full day it takes
        the second half of the last routine, so nothing overlaps."""
        if not npc.routines:
            npc.routines.append(new_routine())
        else:
            gaps, _ = npc_gen.routine_coverage(npc.routines)
            if gaps:
                s, e = gaps[0]
            else:
                last = npc.routines[-1]
                s0 = last["start"][0] * 60 + last["start"][1]
                e0 = last["end"][0] * 60 + last["end"][1]
                length = (e0 - s0) % 1440 or 1440
                s = (s0 + (length // 2) // 30 * 30) % 1440
                e = e0
                last["end"] = [s // 60, s % 60]
            npc.routines.append(new_routine(
                "TA_Sleep", (s // 60 % 24, s % 60), (e // 60 % 24, e % 60)))
        rebuild()
        changed()

    def remove(index):
        if 0 <= index < len(npc.routines) and len(npc.routines) > 1:
            del npc.routines[index]
            rebuild()
            changed()

    rebuild()

    actions = ui.row()
    actions.addWidget(ui.button("+ Add routine", add, ui.DEFAULT,
                                "Another time range with its own activity and waypoint"))
    actions.addStretch()
    layout.addLayout(actions)
    layout.addSpacing(ui.GAP)
    layout.addWidget(coverage)
    layout.addSpacing(ui.SECTION_SPACING)

    # ------------------------------------------------------------------ spawn
    ui.section(layout, "Spawn")
    spawn_worlds = startup_gen.worlds()
    if npc.spawn_world and npc.spawn_world not in spawn_worlds:
        spawn_worlds.append(npc.spawn_world)

    world_box = ui.dropdown(
        spawn_worlds, npc.spawn_world or (spawn_worlds[0] if spawn_worlds else None),
        lambda v: handlers.assignAttribute("spawn_world", lambda: v))
    spawn_wp = ui.search_input(
        waypoints, npc.spawn_waypoint, "Blank = routine 1's waypoint",
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
