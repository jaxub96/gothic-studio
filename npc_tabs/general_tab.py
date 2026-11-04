"""General tab - identity, guild, type.

ID is an exact number, so it is a number field. Gender has two
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

    # Name and ID are one thought - who this is - so they share a row.
    # The ID is stored zero-padded because that is how the game writes instance
    # names: GRD_001_Name, not GRD_1_Name.
    ui.field_group(layout, [
        ("Name", ui.text_input(
            npc.name, "",
            lambda v: handlers.assignAttribute("name", lambda: v)), 1),
        ("ID", ui.number(
            0, 99999, int(npc.id or 0),
            lambda v: handlers.assignAttribute("id", lambda: f"{v:03d}"),
            width=88), 0),
    ])

    ui.section(layout, "Allegiance")

    guild_names = {**labels.GUILD, **gamedata.guild_names()}   # the mod's names win
    ui.field(layout, "Guild",
             ui.dropdown(labels.label_list(guild_names, gamedata.guilds()),
                         labels.pretty(guild_names, npc.guild),
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
