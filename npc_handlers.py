"""
npc_handlers.py - the tiny layer between the NPC tabs and the Npc object.

Every tab widget calls one of these, they mutate the model, then refresh()
redraws the preview. That is the whole contract.
"""


class NpcHandlers:
    def __init__(self, npc, refresh):
        self.npc = npc
        self.refresh = refresh

    def assignAttribute(self, attr, var, cast=str):
        """Set npc.<attr> to cast(var()). `var` is a callable so the tabs can
        pass a lambda that captures the widget's current value."""
        setattr(self.npc, attr, cast(var()))
        self.refresh()

    def addInventoryItem(self, item_id, quantity):
        for entry in self.npc.inv_items:
            if entry["item"] == item_id:
                entry["quantity"] += quantity
                self.refresh()
                return
        self.npc.inv_items.append({"item": item_id, "quantity": quantity})
        self.refresh()
