"""Inventory tab - armor picker and starting items.

Both lists are scraped from Content/Items/*.d, so every id here is guaranteed
to exist. The old hand-written table had 512 of its 523 ids missing from this
install.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem, QWidget

import gamedata
import labels
import textures
import ui
from texture_view import TexturePanel

NO_ARMOR = "-1"


def build(parent: QWidget, npc, handlers) -> None:
    layout = parent.layout()
    layout.setSpacing(0)
    layout.setContentsMargins(ui.SPACING, ui.SPACING, ui.SPACING, ui.SPACING)

    items = gamedata.items()

    # ------------------------------------------------------------------ armor
    ui.section(layout, "Armor")

    armor_panel = TexturePanel("Worn", height=116)
    tree = ui.tree()

    none_item = QTreeWidgetItem(tree, ["(no armor)"])
    none_item.setData(0, Qt.ItemDataRole.UserRole, NO_ARMOR)

    bold = ui.bold_font()
    for group, entries in gamedata.armors_by_guild().items():
        node = QTreeWidgetItem(tree, [labels.ARMOR_GROUP.get(group, group)])
        node.setFont(0, bold)
        node.setData(0, Qt.ItemDataRole.UserRole, None)
        for code, name in entries:
            child = QTreeWidgetItem(node, [f"{name}   ({code})"])
            child.setData(0, Qt.ItemDataRole.UserRole, code)

    def show_armor(code):
        armor_panel.show_texture(
            textures.armor_texture(code) if code != NO_ARMOR else None,
            code if code != NO_ARMOR else "no armor")

    def on_armor():
        selected = tree.selectedItems()
        if not selected:
            return
        item = selected[0]
        code = item.data(0, Qt.ItemDataRole.UserRole)
        if code is None:                      # a category row - fold it
            item.setExpanded(not item.isExpanded())
            return
        npc.armor = code
        show_armor(code)
        handlers.refresh()

    tree.itemSelectionChanged.connect(on_armor)

    armor_row = ui.row(ui.SPACING)
    armor_row.addWidget(tree, 1)
    armor_row.addWidget(armor_panel)
    layout.addLayout(armor_row, 1)
    layout.addSpacing(ui.SPACING)

    # ------------------------------------------------------------- inventory
    ui.section(layout, "Starting items")

    layout.addWidget(ui.checkbox(
        "Add ambient inventory", bool(npc.ambient_inv),
        lambda v: handlers.assignAttribute("ambient_inv", lambda: int(v), int),
        "Calls B_CreateAmbientInv: a random food/gold/trinket set chosen by guild"))
    layout.addWidget(ui.hint(
        "B_CreateAmbientInv (self) gives the NPC a random everyday set picked "
        "by their guild: food, a little gold, the odd plant or potion."))
    layout.addSpacing(ui.GAP)

    inventory = ui.listbox()
    search = ui.search_input(
        [f"{code} - {name}" for code, name in items.items()],
        placeholder=f"Search {len(items)} items...")
    quantity = ui.spin(1, 999, 1, lambda _v: None, width=72)

    def redraw():
        inventory.clear()
        for entry in npc.inv_items:
            name = items.get(entry["item"], entry["item"])
            inventory.addItem(f'{entry["item"]}   x{entry["quantity"]}   ({name})')

    def on_add():
        text = search.text().strip()
        if not text:
            return
        code = text.split(" - ")[0].strip()
        if code not in items:
            search.clear()
            search.setPlaceholderText(f"'{code}' is not a real item id")
            return
        handlers.addInventoryItem(code, quantity.value())
        search.clear()
        redraw()

    def on_remove():
        row_index = inventory.currentRow()
        if row_index >= 0:
            npc.inv_items.pop(row_index)
            handlers.refresh()
            redraw()

    search.returnPressed.connect(on_add)

    add_row = ui.row()
    add_row.addWidget(search, 1)
    add_row.addWidget(quantity)
    add_row.addWidget(ui.button("Add", on_add, ui.PRIMARY,
                                "Add the searched item (or press Enter)"))
    layout.addLayout(add_row)
    layout.addSpacing(ui.GAP)

    layout.addWidget(inventory, 1)
    layout.addSpacing(ui.GAP)

    remove_row = ui.row()
    remove_row.addStretch()
    remove_row.addWidget(ui.button("Remove selected", on_remove, ui.DANGER))
    layout.addLayout(remove_row)

    redraw()
    show_armor(npc.armor)

    def resync():
        redraw()
        show_armor(npc.armor)

    # Let the page re-sync us when the model changes from elsewhere.
    parent.refresh_previews = resync
