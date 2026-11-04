"""
npc_page.py - the NPC half of the studio, as a plain QWidget.

Saves into Content/Story/NPC in CP1250, validates identifiers before saving,
and announces the instance name it built so the Dialog page can pick it up.
"""

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QFileDialog, QMessageBox, QVBoxLayout,
                             QWidget)

import npc_gen
import startup_gen
import teach_gen
import project
import ui
from npc_handlers import NpcHandlers
from npc_model import Npc
from model_view import ModelView
from npc_tabs import (general_tab, inventory_tab, routine_tab, skills_tab,
                      stats_tab, talents_tab, visual_tab)
from theme import DaedalusHighlighter, mono_font


class NpcPage(QWidget):
    #: fires whenever the computed instance name changes, e.g. "GRD_001_Name"
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
                                 "Write into Content/Story/NPC", on_open=self._open)

        self.model_view = ModelView(self.npc)
        self.side.add_tab(self.model_view, "3D view")

        self.preview = ui.code_view(mono_font())
        DaedalusHighlighter(self.preview.document())
        self.side.add_tab(self.preview, "Script")

        self.teaching = ui.code_view(mono_font())
        DaedalusHighlighter(self.teaching.document())
        self.side.add_tab(self.teaching, "Teaching")
        self.side.tabs.currentChanged.connect(self._preview_tab_changed)

        self.tabs = ui.SideTabs()
        self._fill_tabs()

        root.addWidget(ui.page(self.tabs, self.side, left=0))

    def _fill_tabs(self):
        """Build every tab's widgets from the current Npc."""
        for title, module in [("General", general_tab), ("Stats", stats_tab),
                              ("Skills", skills_tab), ("Talents", talents_tab),
                              ("Visual", visual_tab),
                              ("Inventory", inventory_tab),
                              ("Routine", routine_tab)]:
            page = QWidget()
            page.setLayout(QVBoxLayout())
            self.tabs.addTab(page, title)
            module.build(page, self.npc, self.handlers)

    # ------------------------------------------------------------------ actions
    def refresh(self):
        self.preview.setPlainText(npc_gen.build_npc(self.npc))
        self.teaching.setPlainText(
            teach_gen.build_teaching(self.npc)
            or "// Tick talents on the Talents tab to make this NPC a teacher.")
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

    def _open(self):
        """Load a saved NPC .d back into the editor, with its teaching file."""
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Open NPC", str(project.NPC_DIR), "Daedalus (*.d)")
        if not chosen:
            return
        npc = npc_gen.parse_npc(project.read_script(Path(chosen)))
        if npc is None:
            QMessageBox.warning(self, "Open NPC",
                                "No Npc_Default instance found in that file.")
            return

        found = startup_gen.find_spawn(npc_gen.instance_name(npc))
        if found:
            npc.spawn, npc.spawn_world, npc.spawn_waypoint = 1, found[0], found[1]

        lesson = Path(chosen).parent / teach_gen.filename(npc)
        if not lesson.is_file():
            lesson = project.DIA_DIR / teach_gen.filename(npc)
        if lesson.is_file():
            npc.talents |= teach_gen.parse_teaching(project.read_script(lesson))

        # The handlers and tabs hold the existing Npc, so overwrite it in place
        # and rebuild the widgets from it.
        self.npc.__dict__.clear()
        self.npc.__dict__.update(npc.__dict__)
        current = self.tabs.currentIndex()
        self.tabs.clear()
        self._fill_tabs()
        self.tabs.setCurrentIndex(max(current, 0))
        self.refresh()
        self.side.say(f"Opened  {Path(chosen).name}")
        ui.report_omissions(self, "Open NPC", npc.unread)

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
        lesson = teach_gen.build_teaching(self.npc)
        if lesson:
            folder = Path(target).parent if ask else project.DIA_DIR
            project.write_script(folder / teach_gen.filename(self.npc), lesson)
        # An NPC is only in the game if Startup.d inserts it. That file belongs to
        # the mod, so it is only touched by a save into the mod, not Save as.
        spawn_note = ""
        if not ask:
            try:
                spawn_note = startup_gen.sync(npc_gen.instance_name(self.npc), self.npc)
            except ValueError as exc:
                spawn_note = f"NOT spawned: {exc}"
        import gamedata
        gamedata.npc_instances.cache_clear()   # so the Dialog page sees it
        # No modal on success. Saving happens dozens of times a session and a
        # dialog to dismiss every time breaks the edit-compile-test loop; the
        # status line under the preview says what happened instead.
        extra = f"  +  {teach_gen.filename(self.npc)}" if lesson else ""
        if spawn_note:
            extra += f"  +  {spawn_note}"
        self.side.say(f"Saved  {path.name}{extra}  ->  {path.parent}")
        self.saved.emit(str(path))


def build():
    return NpcPage()
