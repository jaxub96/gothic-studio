"""General tab - identity, guild, type.

ID and level are exact numbers, so they are number fields. Gender has two
states, so both are on screen rather than hidden behind a dropdown.
"""

from PyQt6.QtWidgets import QWidget

import gamedata
import labels
import ui

GENDERS = [("Male", "MALE"), ("Female", "FEMALE")]


def build(parent: QWidget, npc, handlers) -> None:
    layout = parent.layout()
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)

    ui.section(layout, "Identity")

    # Name, ID and level are one thought - who this is - so they share a row.
    # The ID is stored zero-padded because that is how the game writes instance
    # names: GRD_001_Arideus, not GRD_1_Arideus.
    ui.field_group(layout, [
        ("Name", ui.text_input(
            npc.name, "Arideus",
            lambda v: handlers.assignAttribute("name", lambda: v)), 1),
        ("ID", ui.number(
            0, 999, int(npc.id or 0),
            lambda v: handlers.assignAttribute("id", lambda: f"{v:03d}"),
            width=88), 0),
        ("Level", ui.number(
            1, 100, npc.level,
            lambda v: handlers.assignAttribute("level", lambda: v, int),
            width=88), 0),
    ])

    ui.section(layout, "Allegiance")

    ui.field(layout, "Guild",
             ui.dropdown(labels.label_list(labels.GUILD, gamedata.guilds()),
                         labels.pretty(labels.GUILD, npc.guild),
                         lambda t: handlers.assignAttribute(
                             "guild", lambda: labels.raw(t))))

    ui.field(layout, "NPC type",
             ui.dropdown(labels.label_list(labels.NPCTYPE, gamedata.npctypes()),
                         labels.pretty(labels.NPCTYPE, npc.type),
                         lambda t: handlers.assignAttribute(
                             "type", lambda: labels.raw(t))))

    layout.addWidget(ui.toggle_row(
        "Gender", GENDERS, npc.gender,
        lambda v: handlers.assignAttribute("gender", lambda: v)))
    layout.addSpacing(ui.SPACING)

    ui.section(layout, "Flags")

    flags = ui.row()
    flags.addWidget(ui.checkbox(
        "Immortal", bool(npc.immortal),
        lambda v: handlers.assignAttribute("immortal", lambda: int(v), int),
        "Cannot be killed"))
    flags.addWidget(ui.checkbox(
        "Friend", bool(npc.friend),
        lambda v: handlers.assignAttribute("friend", lambda: int(v), int),
        "Treated as NPCTYPE_FRIEND"))
    flags.addStretch()
    layout.addLayout(flags)

    layout.addStretch()
