"""Stats tab - attributes, or the chapter preset.

Attributes are exact numbers you look up and type, not proportions you judge by
eye, so they are number fields. Chapter is one of seven named presets, so it is
a list. Neither was ever a slider's job.

The old tool emitted `level = N;` and then called B_SetAttributesToChapter,
which overwrites level with the chapter preset - so whatever you typed was
silently thrown away. Here it is an explicit either/or.
"""

from PyQt6.QtWidgets import QWidget

import ui

ATTRIBUTES = [
    ("Strength", "str", 0, 400),
    ("Dexterity", "dex", 0, 400),
    ("Mana", "mana", 0, 1000),
    ("Hitpoints", "hp", 1, 4000),
]

CHAPTERS = [(f"Chapter {n}", n) for n in range(7)]


def build(parent: QWidget, npc, handlers) -> None:
    layout = parent.layout()
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)

    ui.section(layout, "Attributes")

    manual = []
    level = ui.number(
        1, 100, npc.level,
        lambda v: handlers.assignAttribute("level", lambda: v, int))
    ui.field_row(layout, "Level", level)
    manual.append(level)
    for text, attr, lo, hi in ATTRIBUTES:
        widget = ui.number(
            lo, hi, getattr(npc, attr),
            lambda v, a=attr: handlers.assignAttribute(a, lambda: v, int))
        ui.field_row(layout, text, widget)
        manual.append(widget)

    layout.addSpacing(ui.GAP)
    ui.section(layout, "Chapter preset")

    chapter = ui.choice(
        CHAPTERS, npc.chapter,
        lambda v: handlers.assignAttribute("chapter", lambda: v, int))

    def on_toggle(enabled):
        handlers.assignAttribute("use_chapter", lambda: int(enabled), int)
        chapter.setEnabled(enabled)
        for widget in manual:
            widget.setEnabled(not enabled)

    layout.addWidget(ui.checkbox(
        "Use B_SetAttributesToChapter instead of the numbers above",
        bool(npc.use_chapter), on_toggle))
    layout.addWidget(ui.hint(
        "The preset also overwrites Level, which is why it is either/or."))
    layout.addSpacing(ui.SPACING)

    ui.field_row(layout, "Chapter", chapter)

    on_toggle(bool(npc.use_chapter))
    layout.addStretch()
