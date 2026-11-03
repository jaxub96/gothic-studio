"""
npc_page.py - the NPC half of the studio, as a plain QWidget.

Was Gothic-2-NPC-Studio/ui/app.py. The differences: it is a widget rather
than its own QMainWindow, it saves into Content/Story/NPC in CP1250, it
validates identifiers before saving, and it announces the instance name it
built so the Dialog page can pick it up.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QLabel,
                             QMessageBox, QPushButton, QTabWidget, QTextEdit,
                             QVBoxLayout, QWidget)

import npc_gen
import project
import ui
from npc_handlers import NpcHandlers
from npc_model import Npc
from model_view import ModelView
from npc_tabs import general_tab, inventory_tab, skills_tab, stats_tab, visual_tab
from theme import THEME, DaedalusHighlighter, mono_font


class NpcPage(QWidget):
    #: fires whenever the computed instance name changes, e.g. "GRD_001_Arideus"
    instance_changed = pyqtSignal(str)
    #: the plain display name, so the Dialog tab does not make you retype it
    name_changed = pyqtSignal(str)
    #: emitted after a successful save, with the path written
    saved = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.npc = Npc()
        self.handlers = NpcHandlers(self.npc, self.refresh)
        self._last_instance = ""
        self._last_name = ""
        self._build()
        self.refresh()

    # ------------------------------------------------------------------ layout
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # The side panel is built first: the tabs fire handlers while they are
        # being constructed, and those call refresh(), which needs it to exist.
        self.side = ui.SidePanel(self._validate, self._save,
                                 lambda: self._save(ask=True),
                                 "Write into Content/Story/NPC")

        self.model_view = ModelView(self.npc)
        self.side.add_tab(self.model_view, "3D view")

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(mono_font())
        self.preview.setStyleSheet(ui.code_view_css())
        DaedalusHighlighter(self.preview.document())
        self.side.add_tab(self.preview, "Script")
        self.side.tabs.currentChanged.connect(self._preview_tab_changed)

        self.tabs = QTabWidget()
        for title, module in [("General", general_tab), ("Stats", stats_tab),
                              ("Skills", skills_tab), ("Visual", visual_tab),
                              ("Inventory", inventory_tab)]:
            page = QWidget()
            page.setLayout(QVBoxLayout())
            self.tabs.addTab(page, title)
            module.build(page, self.npc, self.handlers)

        root.addWidget(ui.page(self.tabs, self.side))

    # ------------------------------------------------------------------ actions
    def refresh(self):
        self.preview.setPlainText(npc_gen.build_npc(self.npc))
        inst = npc_gen.instance_name(self.npc)
        if inst != self._last_instance:
            self._last_instance = inst
            self.instance_changed.emit(inst)
        if self.npc.name != self._last_name:
            self._last_name = self.npc.name
            self.name_changed.emit(self.npc.name)
        self.side.say(f"Instance: {inst}   ->   {npc_gen.default_filename(self.npc)}")
        if self._model_tab_visible():
            self.model_view.refresh()
        else:
            self.model_view.mark_stale()
        for i in range(self.tabs.count()):
            fn = getattr(self.tabs.widget(i), "refresh_previews", None)
            if fn:
                fn()

    def _model_tab_visible(self):
        return self.side.current_tab() == 0

    def _preview_tab_changed(self, index):
        """Catch the 3D view up on anything it skipped while hidden."""
        if index == 0:
            self.model_view.refresh()

    def _validate(self):
        problems = npc_gen.validate(self.npc)
        if not problems:
            QMessageBox.information(
                self, "Validate",
                "Every identifier exists in Content/.\nThis should compile.")
        else:
            QMessageBox.warning(self, "Validate",
                                "\n".join("- " + p for p in problems))
        return problems

    def _save(self, ask=False):
        problems = npc_gen.validate(self.npc)
        # An existing-instance clash is a real error; everything else is a warning
        # you may legitimately want to override (e.g. an item you are adding next).
        if problems:
            answer = QMessageBox.question(
                self, "Save anyway?",
                "\n".join("- " + p for p in problems) + "\n\nSave anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return

        target = project.NPC_DIR / npc_gen.default_filename(self.npc)
        if ask:
            chosen, _ = QFileDialog.getSaveFileName(
                self, "Save NPC", str(target), "Daedalus (*.d)")
            if not chosen:
                return
            target = chosen

        path = project.write_script(target, npc_gen.build_npc(self.npc))
        import gamedata
        gamedata.npc_instances.cache_clear()   # so the Dialog page sees it
        # No modal on success. Saving happens dozens of times a session and a
        # dialog to dismiss every time breaks the edit-compile-test loop; the
        # status line under the preview says what happened instead.
        self.side.say(f"Saved  {path.name}  ->  {path.parent}")
        self.saved.emit(str(path))


def build():
    return NpcPage()
