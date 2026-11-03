"""Talents tab - crafting, gathering and utility talents, as checkboxes.

One section per group in talents.py: talents that have no recipes, then each
recipe list in a grid with All / None. A ticked recipe adds its talent itself.
"""

from PyQt6.QtWidgets import QFrame, QGridLayout, QScrollArea, QVBoxLayout, QWidget

import talents
import ui

COLUMNS = 3


def build(parent: QWidget, npc, handlers) -> None:
    outer = parent.layout()
    outer.setContentsMargins(0, 0, 0, 0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)
    scroll.setWidget(inner)
    outer.addWidget(scroll)

    def toggle(ident, on):
        (npc.talents.add if on else npc.talents.discard)(ident)
        handlers.refresh()

    def box(entry):
        return ui.checkbox(entry["label"], entry["id"] in npc.talents,
                           lambda on, i=entry["id"]: toggle(i, on), compact=True)

    for title, skills, recipe_lists in talents.GROUPS:
        ui.section(layout, title)

        for entry in skills:
            layout.addWidget(box(entry))

        for list_title, _master, recipes in recipe_lists:
            layout.addSpacing(ui.GAP)
            head = ui.row()
            head.addWidget(ui.label(list_title))
            head.addStretch()
            boxes = [box(r) for r in recipes]
            head.addWidget(ui.button("All", lambda bs=boxes: _set_all(bs, True),
                                     compact=True))
            head.addWidget(ui.button("None", lambda bs=boxes: _set_all(bs, False),
                                     compact=True))
            layout.addLayout(head)

            grid = QGridLayout()
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setHorizontalSpacing(ui.SPACING)
            for n, widget in enumerate(boxes):
                grid.addWidget(widget, n // COLUMNS, n % COLUMNS)
            for c in range(COLUMNS):
                grid.setColumnStretch(c, 1)
            layout.addLayout(grid)

    layout.addSpacing(ui.GAP)
    layout.addWidget(ui.hint(
        "Ticking a recipe also gives the NPC its talent. Recipes are Gothic's "
        "global PLAYER_TALENT_* flags: the game keeps one set, for the hero."))
    layout.addStretch()


def _set_all(boxes, on):
    for b in boxes:
        b.setChecked(on)
