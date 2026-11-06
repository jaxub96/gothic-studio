"""
dialog_page.py - the Dialog half of the studio, as a plain QWidget.

The scene tree, chat editor and code generator. Saves into Content/Story/Dialoge
as CP1250, writes the log-topic constants file, and can take its NPC id straight
from the NPC page.
"""

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (QFileDialog, QFrame, QMessageBox, QScrollArea, QSplitter,
                             QStackedWidget, QVBoxLayout, QWidget)

import config
import gamedata
import project
import ui
from dialog_gen import (DialogBlock, bind_choices, requires_instance, export_block_name, export_followup_name,
                        generate_constants_file, generate_dia_file,
                        export_plain_dialog, parse_dia_file, parse_plain_dialog,
                        resolve_condition, sanitize, KNOWSINFO_RE)
from dialog_widgets import BlockEditor, BlockListItem
from theme import THEME, DaedalusHighlighter, mono_font


def _same_file(a, b):
    """True when two paths (Path or str, any case on macOS/Windows) are one file."""
    if not a or not b:
        return False
    try:
        return os.path.samefile(a, b)
    except OSError:
        return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def decode_text(raw):
    """Plain text from any editor -> (str, encoding name).

    UTF-8 first (what Mac editors write), then the single-byte Polish code
    pages Windows editors use. Decoding UTF-8 with errors="replace" is what
    turned every Polish letter of a CP1250 file into a question-mark box.
    """
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16"), "UTF-16"
    for enc in ("utf-8-sig", "cp1250", "iso-8859-2"):
        try:
            return raw.decode(enc), ("UTF-8" if enc == "utf-8-sig" else enc.upper())
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace"), "UTF-8 (damaged)"


class DialogPage(QWidget):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.block_editors = []
        self.block_items = []
        self.current_block_idx = -1
        self.current_file_path = None
        self._scene_min = 0
        self._npc_id_touched = False
        self._npc_name_touched = False
        # What the editor looked like at the last save / open / new. Anything
        # different from this is work that is not in a file yet.
        self._saved_text = ""
        self._draft_timer = QTimer(self)
        self._draft_timer.setSingleShot(True)
        self._draft_timer.setInterval(1500)
        self._draft_timer.timeout.connect(self._write_draft)
        self._build()
        QShortcut(QKeySequence.StandardKey.Save, self, lambda: self._save())
        QTimer.singleShot(0, self._offer_restore)

    # ------------------------------------------------------------------ layout
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        # Built first: the header wires signals that call _refresh_preview.
        self.side = ui.SidePanel(self._validate, self._save,
                                 lambda: self._save(ask=True),
                                 "Write into Content/Story/Dialoge", on_open=self._open)

        # The spoken lines on their own - the same thing Export text writes,
        # and what you want when you are reading the conversation rather than
        # the code.
        self.text_preview = ui.code_view()
        self.side.add_tab(self.text_preview, "Spoken text")

        self.dia_preview = ui.code_view(mono_font())
        DaedalusHighlighter(self.dia_preview.document())
        self.side.add_tab(self.dia_preview, "Script")

        # The work area: the scene list down the left edge, hanging from the Dialog
        # tab the way the NPC tab's list does, then the header over the editor.
        self.scene_split = QSplitter(Qt.Orientation.Horizontal)
        self.scene_split.setHandleWidth(0)       # locked: the list is not resizable
        self.scene_split.setChildrenCollapsible(False)
        self.scene_split.addWidget(self._sidebar())

        right = QWidget()
        col = QVBoxLayout(right)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        col.addWidget(self._header())

        self.editor_stack = QStackedWidget()
        self.placeholder = ui.placeholder("Select or create a dialog scene")
        self.editor_stack.addWidget(self.placeholder)
        self.editor_stack.setCurrentWidget(self.placeholder)
        body = QWidget()
        body_col = QVBoxLayout(body)
        body_col.setContentsMargins(ui.PADDING, ui.PADDING, 0, 0)
        body_col.addWidget(self.editor_stack)
        col.addWidget(body, 1)
        right.setMinimumWidth(max(right.minimumSizeHint().width(), 320))
        self.scene_split.addWidget(right)
        self.scene_split.setStretchFactor(0, 0)
        self.scene_split.setStretchFactor(1, 1)
        self.set_scene_width(THEME["sidebar_width"])
        work = self.scene_split

        root.addWidget(ui.page(work, self.side, left=0))

        self.npc_name_edit.textChanged.connect(self._refresh_preview)
        self.npc_id_edit.currentTextChanged.connect(self._refresh_preview)
        # activated / textEdited only fire for real user input, never for
        # setCurrentText() - which is how we tell "you chose this" apart from
        # "the NPC tab pushed this".
        self.npc_id_edit.activated.connect(self._mark_npc_id_touched)
        self.npc_id_edit.lineEdit().textEdited.connect(self._mark_npc_id_touched)
        self.npc_name_edit.textEdited.connect(self._mark_npc_name_touched)

    def _header(self):
        """Who this dialog belongs to, and the file actions.

        Two rows on a grey strip directly under the tab bar, so the selected
        Dialog tab and the strip read as one surface.
        """
        holder = QWidget()
        holder.setObjectName("dialogHeader")
        holder.setStyleSheet(f"#dialogHeader {{ background:{THEME['bg_panel']}; }}")
        col = QVBoxLayout(holder)
        col.setContentsMargins(ui.PADDING, ui.PADDING, ui.PADDING, ui.GAP)
        col.setSpacing(ui.GAP)

        who = ui.row()
        self.npc_name_edit = ui.text_input()
        self.npc_id_edit = ui.dropdown([])
        self.npc_id_edit.setEditable(True)
        self.npc_id_edit.setMinimumWidth(150)
        self._reload_npc_ids()

        who.addWidget(ui.label("Speaker"))
        who.addWidget(self.npc_name_edit, 1)
        who.addSpacing(ui.GAP)
        who.addWidget(ui.label("Instance"))
        who.addWidget(self.npc_id_edit, 2)
        col.addLayout(who)

        # Save and Open live in the side panel, which is also where Save as is.
        files = ui.row()
        for text, slot, tip in [
                ("New", self._new_project, "Unload this dialog and start a blank one"),
                ("Import text", self._import_text, "Read a plain Speaker - line file"),
                ("Export text", self._export_text, "Write the spoken lines out as text")]:
            files.addWidget(ui.button(text, slot, ui.DEFAULT, tip, compact=True))
        files.addStretch()
        col.addLayout(files)
        return holder

    def _sidebar(self):
        """The list of conversation topics, styled as the NPC tab's list is."""
        left = QWidget()
        left.setObjectName("sceneColumn")
        self.scene_col = left
        left.setStyleSheet(
            f"#sceneColumn {{ background:{THEME['bg_panel']}; "
            f"  border-right:{THEME['border_width']} solid {THEME['bg_border']}; }}")
        col = QVBoxLayout(left)
        col.setContentsMargins(8, 10, 8, 10)
        col.setSpacing(ui.GAP)

        self.block_list_widget = QWidget()
        self.block_list_widget.setStyleSheet("background:transparent;")
        self.block_list_layout = QVBoxLayout(self.block_list_widget)
        self.block_list_layout.setContentsMargins(0, 0, 0, 0)
        self.block_list_layout.setSpacing(2)
        self.block_list_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self.block_list_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        col.addWidget(scroll, 1)

        col.addWidget(ui.button("+  New scene", lambda: self._add_block(),
                                ui.PRIMARY, "Add another conversation topic"))
        return left

    MAX_SCENE_COL = 260

    def _fit_scene_column(self):
        """Never narrower than the tab bar (so its rule lines up with the Dialog tab),
        wider when a scene name needs it, up to a limit; beyond that names elide."""
        want = max([it.needed_width() for it in self.block_items] or [0]) + 16 + 2
        self.scene_col.setFixedWidth(max(self._scene_min, min(want, self.MAX_SCENE_COL)))

    def set_scene_width(self, width):
        """The scene list is as wide as the tab bar, so its right rule continues the
        edge of the Dialog tab (the NPC tab does the same). It is fixed."""
        self._scene_min = width
        self._fit_scene_column()

    def set_npc_id(self, instance_name):
        """Called whenever the NPC page rebuilds its instance name.

        Keeps following the NPC tab until you pick or type an ID yourself -
        after that this stops touching the field.
        """
        if instance_name and not self._npc_id_touched:
            self.npc_id_edit.setCurrentText(instance_name)

    def _mark_npc_id_touched(self, *_):
        self._npc_id_touched = True

    def set_npc_name(self, name):
        """Mirror the NPC tab's display name until you type your own."""
        if name and not self._npc_name_touched:
            self.npc_name_edit.setText(name)

    def _mark_npc_name_touched(self, *_):
        self._npc_name_touched = True

    def on_npc_saved(self, _path):
        """The NPC tab just wrote a file - refresh the dropdown so it is there."""
        self._reload_npc_ids()

    def refresh_npc_ids(self):
        """Re-scan Content/Story/NPC; the app calls this each time the tab is shown."""
        self._reload_npc_ids()

    def _reload_npc_ids(self):
        gamedata.npc_instances.cache_clear()
        current = self.npc_id_edit.currentText() if hasattr(self, "npc_id_edit") else ""
        self.npc_id_edit.clear()
        self.npc_id_edit.addItems(sorted(gamedata.npc_instances()))
        self.npc_id_edit.setCurrentText(current)

    # ------------------------------------------------------- scene tree wiring
    def _make_editor(self, is_followup):
        ed = BlockEditor(
            on_change=self._refresh_preview,
            on_choice_added=self._on_choice_added,
            on_choice_removed=self._on_choice_removed,
            is_followup=is_followup,
        )
        ed.scene_names = lambda: self._other_scene_names(ed)
        return ed

    def _other_scene_names(self, editor):
        """Every top-level scene except `editor`'s own: what a scene can require."""
        names = []
        for b, ed in zip(self.blocks, self.block_editors):
            name = ed.name_edit.text().strip() or b.name
            if ed is not editor and not b.is_followup and not b.is_exit and name:
                names.append(name)
        return names

    def _is_descendant(self, block, ancestor):
        cur = block.parent_block
        while cur is not None:
            if cur is ancestor:
                return True
            cur = cur.parent_block
        return False

    def _find_insert_pos_after(self, parent_idx):
        parent_block = self.blocks[parent_idx]
        pos = parent_idx + 1
        while pos < len(self.blocks) and self._is_descendant(self.blocks[pos], parent_block):
            pos += 1
        return pos

    def _add_block(self, block=None, parent_idx=None):
        b = block if block is not None else DialogBlock()
        pos = self._find_insert_pos_after(parent_idx) if parent_idx is not None else len(self.blocks)
        if block is None and self.blocks:
            # The commonest condition by far: the scene before has been heard.
            self._collect_blocks()           # settles default names first
            previous = [x for x in self.blocks if not x.is_followup and not x.is_exit]
            if previous:
                b.requires = previous[-1].name

        self.blocks.insert(pos, b)
        ed = self._make_editor(is_followup=b.is_followup)
        if block is not None:
            ed.load_block(b)
        elif b.requires:
            ed.set_requires(b.requires)        # a brand-new scene starts with its default
        self.block_editors.insert(pos, ed)
        self.editor_stack.addWidget(ed)

        item = BlockListItem(pos, b.name, on_select=self._select_block,
                             on_remove=self._remove_block, is_followup=b.is_followup)
        self.block_items.insert(pos, item)
        self.block_list_layout.insertWidget(pos, item)
        self._reindex()
        self._select_block(pos)
        return b, ed

    def _reindex(self):
        for i, it in enumerate(self.block_items):
            it.idx = i

    def _select_block(self, idx):
        if idx < 0 or idx >= len(self.blocks):
            return
        if 0 <= self.current_block_idx < len(self.block_items):
            self.block_items[self.current_block_idx].set_active(False)
        self.current_block_idx = idx
        self.block_items[idx].set_active(True)
        self.editor_stack.setCurrentWidget(self.block_editors[idx])
        self._refresh_preview()

    def _remove_block(self, idx):
        if idx < 0 or idx >= len(self.blocks):
            return
        target = self.blocks[idx]
        doomed = [i for i, b in enumerate(self.blocks)
                  if b is target or self._is_descendant(b, target)]
        for i in sorted(doomed, reverse=True):
            self.blocks.pop(i)
            self.block_editors.pop(i).deleteLater()
            item = self.block_items.pop(i)
            item.setParent(None)
            item.deleteLater()
        self._reindex()
        self.current_block_idx = min(self.current_block_idx, len(self.blocks) - 1)
        if self.current_block_idx >= 0:
            self._select_block(self.current_block_idx)
        else:
            self.editor_stack.setCurrentWidget(self.placeholder)
        self._refresh_preview()

    def _editor_idx_containing(self, choice_widget):
        for i, ed in enumerate(self.block_editors):
            if choice_widget in ed.get_choice_widgets():
                return i
        return None

    def _on_choice_added(self, cw):
        parent_idx = self._editor_idx_containing(cw)
        if parent_idx is None:
            return
        parent_block = self.blocks[parent_idx]
        ni = self._npc_id()
        parent_name = (self.block_editors[parent_idx].name_edit.text().strip()
                       or parent_block.name or f"Scene{parent_idx + 1}")
        if parent_block.is_followup and parent_block.func_name:
            parent_bn = parent_block.func_name
        else:
            parent_bn = export_block_name(ni, parent_name)

        n = len([b for b in self.blocks if b.parent_block is parent_block]) + 1
        nb = DialogBlock()
        nb.is_followup = True
        nb.name = f"Choice {n}"
        nb.func_name = f"{parent_bn}_Choice{n}"
        nb.parent_block = parent_block

        cw.linked_block = nb
        cw.lock_func(nb.func_name)
        self._add_block(nb, parent_idx=parent_idx)

    def _on_choice_removed(self, cw):
        if getattr(cw, "linked_block", None) is None:
            return
        for i, b in enumerate(self.blocks):
            if b is cw.linked_block:
                self._remove_block(i)
                break

    # ------------------------------------------------------------- generation
    def _npc_name(self):
        return self.npc_name_edit.text().strip()

    def _npc_id(self):
        return self.npc_id_edit.currentText().strip()

    def _collect_blocks(self):
        # A scene that was renamed: whatever required it by its old name follows it.
        for b, ed in zip(self.blocks, self.block_editors):
            new = ed.name_edit.text().strip()
            if b.name and new and new != b.name and not b.is_followup:
                for other in self.block_editors:
                    if other.requires_text().upper() == b.name.upper():
                        other.set_requires(new)

        for i, ed in enumerate(self.block_editors):
            b = self.blocks[i]
            fresh = ed.get_block()
            b.name = fresh.name or (f"Choice{i + 1}" if b.is_followup else f"Scene{i + 1}")
            b.description = fresh.description
            b.permanent = fresh.permanent
            b.important = fresh.important
            b.is_trade = fresh.is_trade
            b.requires = fresh.requires
            b.extra_conditions = fresh.extra_conditions
            b.condition_expr = fresh.condition_expr
            b.stop_after = fresh.stop_after
            b.entries = fresh.entries
            b.choices = fresh.choices
            self.block_items[i].update_name(b.name)
        self._fit_scene_column()

        n = 1
        for b in self.blocks:
            if not b.is_followup:
                b.nr = n
                n += 1

        ni = self._npc_id() or "NPC_ID"
        for b in self.blocks:
            if b.is_followup:
                parent_bn = (b.parent_block.func_name if b.parent_block.is_followup
                             else export_block_name(ni, b.parent_block.name))
                b.func_name = export_followup_name(parent_bn, b.name)
        for ed in self.block_editors:
            for cw in ed.get_choice_widgets():
                if cw.linked_block is not None:
                    cw.func.setText(cw.linked_block.func_name)
                    # the Back box on a choice row decides how its reply ends
                    cw.linked_block.clear_after = cw.back_cb.isChecked()
        return self.blocks

    def _emit_exit(self):
        """Only emit the EXIT block if this NPC does not already have one.

        Two dialog files for the same NPC that both emit DIA_<NPC>_EXIT are a
        redefinition error and stop the whole mod compiling. The file this dialog
        is saved to (or was opened from) does not count: it is about to be
        rewritten, so its own EXIT must be written back, not treated as someone
        else's.
        """
        ni = self._npc_id()
        if not ni:
            return True
        exit_name = f"DIA_{sanitize(ni)}_EXIT".upper()
        target = project.DIA_DIR / f"DIA_{sanitize(ni)}.d"
        for f in project.iglob(project.DIA_DIR, "DIA*.d"):
            if _same_file(f, self.current_file_path) or _same_file(f, target):
                continue
            if exit_name in project.read_script(f).upper():
                return False
        return True

    def _dia_text(self):
        blocks = self._collect_blocks()
        return generate_dia_file(self._npc_name() or "NPC",
                                 self._npc_id() or "NPC_ID",
                                 blocks, emit_exit=self._emit_exit())

    def _refresh_preview(self, *_):
        text = self._dia_text()
        self.dia_preview.setPlainText(text)
        if self.is_dirty(text):
            self._draft_timer.start()      # restarts: writes 1.5 s after the last edit
        self.text_preview.setPlainText(export_plain_dialog(self.blocks))

    def _problems(self):
        problems = []
        ni = self._npc_id()
        if not ni:
            problems.append("No NPC ID set.")
        elif gamedata.unknown("npc", ni):
            problems.append(f"No NPC instance named '{ni}' exists in Content/Story/NPC.")

        blocks = self._collect_blocks()
        known_topics = {t.upper() for t in gamedata.log_topics()}
        for b in blocks:
            for e in b.entries:
                kind = getattr(e, "kind", None)
                if kind in ("give_item", "take_item") and gamedata.unknown("item", e.item):
                    problems.append(f"Unknown item: {e.item}")
                if kind == "give_xp" and e.xp and not str(e.xp).strip().isdigit():
                    if gamedata.unknown("xp", e.xp):
                        problems.append(f"Unknown XP constant: {e.xp}")
                if kind == "routine" and e.routine and e.routine.upper() != "START":
                    pass  # routine names are per-NPC strings, not global symbols

        # A required scene must exist here or in Content/; Npc_KnowsInfo in a hand-typed
        # condition must name a dialog instance too.
        own = {export_block_name(ni or "NPC", b.name).upper() for b in blocks if not b.is_followup and not b.is_exit}
        for b in blocks:
            if b.is_followup:
                continue
            req = b.requires.strip()
            if req:
                inst = requires_instance(req, ni or "NPC", blocks)
                if inst.upper() == export_block_name(ni or "NPC", b.name).upper():
                    problems.append(f"Scene '{b.name}' requires itself, so it can never be offered.")
                elif inst.upper() not in own and gamedata.unknown("info", inst):
                    problems.append(f"Scene '{b.name}': requires '{req}', which is no scene of this "
                                    "file and no dialog in Content/")
            typed = "\n".join(list(b.extra_conditions) + [b.condition_expr])
            for m in KNOWSINFO_RE.finditer(resolve_condition(typed, ni or "NPC", blocks)):
                if m.group(2).upper() not in own and gamedata.unknown("info", m.group(2)):
                    problems.append(f"Scene '{b.name}': condition names '{m.group(2)}', which is no dialog "
                                    "(use a scene name of this NPC or a DIA_... instance)")

        new_topics = generate_constants_file(ni or "NPC", blocks, tuple(known_topics))
        if new_topics:
            count = new_topics.count("const string")
            problems.append(f"{count} new log topic(s) will be written to "
                            f"Log_Entries/LOG_Constants_{sanitize(ni) or 'NPC'}.d")
        return problems

    def _validate(self):
        problems = self._problems()
        if not problems:
            QMessageBox.information(self, "Validate",
                                    "Every identifier exists in Content/.\nThis should compile.")
        else:
            QMessageBox.warning(self, "Validate", "\n".join("- " + p for p in problems))
        return problems

    # ------------------------------------------------------------- persistence
    def _save(self, ask=False):
        nn, ni = self._npc_name(), self._npc_id()
        if not nn or not ni:
            QMessageBox.warning(self, "Missing Info",
                                "Please set the Speaker name, and pick this NPC on the NPC tab "
                                "(or open its dialog file) so the dialog knows its instance.")
            return

        # Same rule as the NPC tab: problems are shown first and you decide. A new log
        # topic is not a problem (Save writes it), so it does not stop the save.
        problems = [p for p in self._problems() if "new log topic" not in p]
        if problems:
            answer = QMessageBox.question(
                self, "Save anyway?",
                "\n".join("- " + p for p in problems) + "\n\nThe mod build will fail on these. Save anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return

        blocks = self._collect_blocks()
        # Gothic.src:295 globs DIA*.d - a file not starting with DIA is never compiled.
        target = project.DIA_DIR / f"DIA_{sanitize(ni)}.d"
        if ask:
            chosen, _ = QFileDialog.getSaveFileName(
                self, "Save Dialog File", str(target), "Daedalus (*.d)")
            if not chosen:
                return
            target = chosen

        text = self._dia_text()
        path = project.write_script(target, text)
        self.current_file_path = path
        self._mark_clean(text)

        # The log-topic constants: a dialog with a log entry does not compile without them.
        consts = generate_constants_file(ni, blocks, tuple(gamedata.log_topics()))
        msg = f"Saved as CP1250:\n  {path}"
        if consts:
            cpath = project.write_script(
                project.LOG_DIR / f"LOG_Constants_{sanitize(ni)}.d", consts)
            gamedata.log_topics.cache_clear()
            msg += f"\n\nNew log topics:\n  {cpath}"

        # Non-modal: the status line carries it, same as the NPC tab.
        self.side.say(msg.replace(chr(10), "   "))

    def _export_text(self):
        blocks = self._collect_blocks()
        if not any(b.lines() for b in blocks):
            QMessageBox.information(self, "Nothing to Export", "Add some dialog lines first.")
            return
        default = f"{sanitize(self._npc_id()) or 'NPC'}_dialog.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Plain Dialog Text", default, "Text Files (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(export_plain_dialog(blocks))
        QMessageBox.information(self, "Exported", f"Dialog reference text saved:\n  {path}")

    def _import_text(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Plain Dialog Text", "", "Text Files (*.txt)")
        if not path:
            return
        try:
            raw = Path(path).read_bytes()
            text, encoding = decode_text(raw)
            blocks = parse_plain_dialog(text)
        except OSError as e:
            QMessageBox.critical(self, "Could Not Import", f"{e}")
            return
        if not blocks:
            QMessageBox.information(
                self, "Nothing Found",
                "No dialog lines found.\nExpected:\n\n-- Scene Name --\nNPC - line\nHero - line")
            return
        # Scenes (and the replies under them) join whatever is already open. Each
        # new scene requires the one before it, the usual way a conversation runs.
        keep = self._npc_id_touched, self._npc_name_touched
        existing = self._collect_blocks() if self.blocks else []
        bind_choices(blocks, self._npc_id() or "NPC_ID")
        previous = next((x for x in reversed(existing) if not x.is_followup and not x.is_exit), None)
        for b in blocks:
            if not b.is_followup:
                if previous is not None:
                    b.requires = previous.name
                previous = b
        self._load_project(self._npc_name(), self._npc_id(), existing + blocks)
        self._npc_id_touched, self._npc_name_touched = keep
        replies = sum(1 for b in blocks if b.is_followup)
        self.side.say(f"Imported {len(blocks) - replies} scene(s)"
                      + (f" and {replies} choice repl{'y' if replies == 1 else 'ies'}" if replies else "")
                      + f" from {os.path.basename(path)}  (read as {encoding})")

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Dialog File", str(project.DIA_DIR), "Daedalus (*.d)")
        if not path:
            return
        if self.is_dirty() and QMessageBox.question(
                self, "Open Dialog File",
                "The dialog in the editor has changes that are not saved.\n"
                "Opening a file replaces it. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        notes = []
        try:
            npc_name, npc_id, blocks = parse_dia_file(project.read_script(path), notes)
        except OSError as e:
            QMessageBox.critical(self, "Could Not Open", f"{e}")
            return
        self._load_project(npc_name, npc_id, blocks)
        self.current_file_path = path
        self._mark_clean()
        self.side.say(f"Opened: {path}")
        ui.report_omissions(self, "Open dialog", notes)

    def _new_project(self):
        if self.blocks or self._npc_name() or self._npc_id():
            unsaved = "\nIt has changes that are NOT saved." if self.is_dirty() else ""
            confirm = QMessageBox.question(
                self, "Start New Dialog",
                "This clears the NPC name/ID and every scene." + unsaved + "\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if confirm != QMessageBox.StandardButton.Yes:
                return
        self._load_project("", "", [])
        self.current_file_path = None
        self._mark_clean()
        self.side.say("")

    def _load_project(self, npc_name, npc_id, blocks):
        for ed in self.block_editors:
            self.editor_stack.removeWidget(ed)
            ed.deleteLater()
        for item in self.block_items:
            item.setParent(None)
            item.deleteLater()
        self.blocks, self.block_editors, self.block_items = [], [], []
        self.current_block_idx = -1

        self.npc_name_edit.setText(npc_name)
        self.npc_id_edit.setCurrentText(npc_id)
        # An opened file's NPC wins over the NPC tab; a new project follows it again.
        self._npc_id_touched = bool(npc_id)
        self._npc_name_touched = bool(npc_name)

        if not blocks:
            self.editor_stack.setCurrentWidget(self.placeholder)
        for b in blocks:
            _, ed = self._add_block(b)
            for cw in ed.get_choice_widgets():
                child = next((c for c in blocks
                              if c.is_followup and c.func_name == cw.func.text()
                              and c.parent_block is b), None)
                if child is not None:
                    cw.linked_block = child
                    cw.lock_func(child.func_name)
        if blocks:
            self._select_block(0)
        self._refresh_preview()

    # ------------------------------------------------- unsaved work and drafts
    def is_dirty(self, text=None):
        """True when the editor holds scenes that no saved file has yet."""
        if not self.blocks:
            return False
        return (self._dia_text() if text is None else text) != self._saved_text

    def _mark_clean(self, text=None):
        self._saved_text = self._dia_text() if text is None else text
        self._draft_timer.stop()
        self._clear_draft()

    def _draft_path(self):
        # Dev runs and the selftest drive the page with scratch data: leave the
        # user's real draft alone.
        if os.environ.get("GOTHIC_STUDIO_DEV"):
            return None
        return config.CONFIG_FILE.parent / "dialog_draft.json"

    def _write_draft(self):
        path = self._draft_path()
        if path is None or not self.is_dirty():
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({
                "npc_name": self._npc_name(), "npc_id": self._npc_id(),
                "file": str(self.current_file_path or ""),
                "text": self._dia_text(),
            }, indent=1), encoding="utf-8")
            tmp.replace(path)             # never leaves a half-written draft
        except OSError:
            pass                          # a failed backup must not interrupt editing

    def _clear_draft(self):
        path = self._draft_path()
        if path is not None:
            try:
                path.unlink()
            except OSError:
                pass

    def _offer_restore(self):
        """At start-up: put back the dialog that was open when the app last ended
        without saving it."""
        path = self._draft_path()
        if path is None or not path.is_file():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            notes = []
            name, npc_id, blocks = parse_dia_file(data["text"], notes)
            name = data.get("npc_name") or name
            npc_id = data.get("npc_id") or npc_id
        except (OSError, ValueError, KeyError):
            return
        if not blocks:
            self._clear_draft()
            return
        answer = QMessageBox.question(
            self, "Restore unsaved dialog",
            f"Last time Gothic Studio closed, the dialog for {npc_id or name or 'an NPC'} "
            f"({len(blocks)} scene(s)) had not been saved.\n\nRestore it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if answer != QMessageBox.StandardButton.Yes:
            self._clear_draft()
            return
        self._load_project(name, npc_id, blocks)
        self.current_file_path = data.get("file") or None
        self._saved_text = ""             # still unsaved, so it stays marked dirty
        self._write_draft()
        self.side.say("Restored the unsaved dialog. Save it to put it in the mod.")

    def confirm_close(self):
        """Ask what to do with unsaved scenes. True when the app may close."""
        if not self.is_dirty():
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved dialog")
        box.setText(f"The dialog for {self._npc_id() or self._npc_name() or 'this NPC'} "
                    "has changes that are not saved.")
        save = box.addButton("Save to mod", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save:
            self._save()
            return not self.is_dirty()    # a cancelled or refused save keeps the app open
        if clicked is discard:
            self._clear_draft()
            return True
        return False


def build():
    return DialogPage()
