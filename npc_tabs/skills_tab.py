"""Skills tab - fight tactic and weapon talents.

Fight tactics come from the FAI_*.d filenames. The old data table carried a
".d" on every value, so picking anything emitted `fight_tactic = FAI_X.d;`,
which is a parse error.
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
