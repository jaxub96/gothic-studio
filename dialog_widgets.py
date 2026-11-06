"""
widgets.py — All custom Qt widgets: the chat-style line/effect input, choice
rows, the per-scene editor, and the sidebar list item.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QTabWidget,
    QSplitter,
    QApplication,
    QPlainTextEdit,
)
from PyQt6.QtCore import QSize, Qt, QTimer, QMimeData
from PyQt6.QtGui import QDrag, QFont, QFontMetrics, QPainter

from theme import THEME
import ui
from ui import SS
from dialog_gen import (
    DialogLine,
    DialogChoice,
    DialogBlock,
    EffectEntry,
    is_hero_speaker,
    speaker_display_name,
)


# ── Chat-based dialog line input ────────────────────────────────────────────────
class ChatInput(QLineEdit):
    """Enter submits the current line. Up/Down always switch speaker; Left/Right
    switch speaker only when the field is empty, so normal text editing still works."""

    def __init__(self, on_submit=None, on_toggle=None, parent=None):
        super().__init__(parent)
        self.on_submit = on_submit
        self.on_toggle = on_toggle

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            text = self.text().strip()
            if text and self.on_submit:
                self.on_submit(text)
                self.clear()
            e.accept()
            return
        if k in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            if self.on_toggle:
                self.on_toggle()
            e.accept()
            return
        if k in (Qt.Key.Key_Left, Qt.Key.Key_Right) and not self.text():
            if self.on_toggle:
                self.on_toggle()
            e.accept()
            return
        super().keyPressEvent(e)


#: the whole dialog panel uses the chat bubble's text size
CHAT_PX = int(THEME["font_size_chat"].rstrip("px"))


# ── Drag-and-drop reordering for chat bubbles ───────────────────────────────
class _BubbleDragState:
    """In-process bookkeeping for a drag. QDrag.exec() blocks the event loop
    until the drop lands, so a single class-level slot is all that's needed
    to remember which bubble is being dragged."""
    source = None
    MIME = "application/x-daedalogue-bubble"


class DragHandle(QLabel):
    """Small grip on each bubble — press and drag it to reorder the line."""

    def __init__(self, drag_target):
        super().__init__("⋮⋮")
        self._target = drag_target
        self._press_pos = None
        self.setFixedWidth(14)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Drag to reorder")
        self.setStyleSheet(f"color:{THEME['text_muted']}; background:transparent; font-size:11px;")

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.pos()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._press_pos is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            if (e.pos() - self._press_pos).manhattanLength() >= QApplication.startDragDistance():
                self._start_drag()
                return
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._press_pos = None
        super().mouseReleaseEvent(e)

    def _start_drag(self):
        _BubbleDragState.source = self._target
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(_BubbleDragState.MIME, b"1")
        drag.setMimeData(mime)
        drag.setPixmap(self._target.grab())
        drag.exec(Qt.DropAction.MoveAction)
        _BubbleDragState.source = None
        self._press_pos = None


class _DropTargetMixin:
    """Lets a bubble accept another bubble dropped onto it, reordering the
    conversation. Which half of the widget the drop lands on decides whether
    the dragged bubble ends up before or after this one."""

    def _init_drop_target(self):
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(_BubbleDragState.MIME) and _BubbleDragState.source not in (None, self):
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(_BubbleDragState.MIME):
            e.acceptProposedAction()

    def dropEvent(self, e):
        src = _BubbleDragState.source
        if src is None or src is self:
            e.ignore()
            return
        drop_after = e.position().y() > self.height() / 2
        container = self.parent()
        if hasattr(container, "reorder_bubble"):
            container.reorder_bubble(src, self, drop_after)
        e.acceptProposedAction()


class ChatDropContainer(QWidget):
    """The scrollable column that holds all bubbles. Dropping onto empty
    space below the last bubble moves the dragged one to the end."""

    def __init__(self, owner):
        super().__init__()
        self._owner = owner
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat(_BubbleDragState.MIME):
            e.acceptProposedAction()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat(_BubbleDragState.MIME):
            e.acceptProposedAction()

    def dropEvent(self, e):
        src = _BubbleDragState.source
        if src is not None:
            self._owner.reorder_bubble(src, None, True)
        e.acceptProposedAction()

    def reorder_bubble(self, src_bubble, target_bubble, drop_after):
        self._owner.reorder_bubble(src_bubble, target_bubble, drop_after)


class ChatBubble(QFrame, _DropTargetMixin):
    """Shows one dialog line. Double-click the text to edit it in place.
    Drag the ⋮⋮ handle to reorder it within the conversation."""

    def __init__(self, line: DialogLine, on_remove=None, on_edit=None):
        super().__init__()
        self._init_drop_target()
        self.line = line
        self.on_remove = on_remove
        self.on_edit = on_edit
        is_hero = is_hero_speaker(line.speaker)
        bg = THEME["bubble_hero_bg"] if is_hero else THEME["bubble_npc_bg"]
        fg = THEME["bubble_hero_text"] if is_hero else THEME["bubble_npc_text"]

        outer = QHBoxLayout(self)
        outer.setContentsMargins(2, 1, 2, 1)
        outer.setSpacing(0)
        if is_hero:
            outer.addStretch(1)

        bubble = QFrame()
        bubble.setStyleSheet(
            f"QFrame {{ background:{bg}; border-radius:{THEME['radius_lg']}; }}"
        )
        bl = QHBoxLayout(bubble)
        bl.setContentsMargins(14, 10, 8, 10)
        bl.setSpacing(8)

        grip = DragHandle(self)
        bl.addWidget(grip, 0, Qt.AlignmentFlag.AlignTop)

        tag = QLabel(speaker_display_name(line.speaker))
        tag.setStyleSheet(
            f"color:{fg}; background:transparent; font-weight:600; "
            f"font-size:12px; letter-spacing:1px;"
        )

        self.text_lbl = QLabel(line.text)
        self.text_lbl.setWordWrap(True)
        self.text_lbl.setStyleSheet(
            f"color:{fg}; background:transparent; font-family:{THEME['font_ui']}; "
            f"font-size:{THEME['font_size_chat']};"
        )
        self.text_lbl.setMaximumWidth(440)
        self.text_lbl.setCursor(Qt.CursorShape.IBeamCursor)
        self.text_lbl.setToolTip("Double-click to edit")
        self.text_lbl.mouseDoubleClickEvent = lambda e: self._enter_edit()

        self.text_edit = QLineEdit(line.text)
        self.text_edit.setStyleSheet(
            f"QLineEdit {{ background:{THEME['bg_input']}; color:{THEME['text_primary']}; "
            f"border:{THEME['border_width']} solid {THEME['accent_primary']}; "
            f"border-radius:{THEME['radius_sm']}; padding:4px 6px; font-size:{THEME['font_size_chat']}; }}"
        )
        self.text_edit.setMaximumWidth(440)
        self.text_edit.hide()
        self.text_edit.editingFinished.connect(self._commit_edit)

        col = QVBoxLayout()
        col.setSpacing(3)
        col.addWidget(tag)
        col.addWidget(self.text_lbl)
        col.addWidget(self.text_edit)
        bl.addLayout(col, 1)

        rm = QPushButton("✕")
        rm.setFixedSize(18, 18)
        rm.setStyleSheet(SS["rm_btn"])
        rm.clicked.connect(lambda: self.on_remove(self) if self.on_remove else None)
        bl.addWidget(rm, 0, Qt.AlignmentFlag.AlignTop)

        outer.addWidget(bubble)
        if not is_hero:
            outer.addStretch(1)

    def _enter_edit(self):
        self.text_edit.setText(self.line.text)
        self.text_lbl.hide()
        self.text_edit.show()
        self.text_edit.setFocus()
        self.text_edit.selectAll()

    def _commit_edit(self):
        new_text = self.text_edit.text().strip()
        if new_text:
            self.line.text = new_text
            self.text_lbl.setText(new_text)
        self.text_edit.hide()
        self.text_lbl.show()
        if self.on_edit:
            self.on_edit()


class EffectBubble(QFrame, _DropTargetMixin):
    """Shows one inline effect (give/take item, XP, log entry), centered
    and visually distinct from spoken lines. Remove and re-insert to edit.
    Drag the ⋮⋮ handle to reorder it within the conversation."""

    ICONS = {
        "give_item": "🎘",
        "take_item": "📤",
        "give_xp": "⭘",
        "log": "📜",
        "routine": "🧭",
        "follow": "🧭",
        "unfollow": "🏠",
    }

    def __init__(self, entry: EffectEntry, on_remove=None):
        super().__init__()
        self._init_drop_target()
        self.entry = entry
        self.on_remove = on_remove

        outer = QHBoxLayout(self)
        outer.setContentsMargins(2, 2, 2, 2)
        outer.setSpacing(0)
        outer.addStretch(1)

        pill = QFrame()
        pill.setStyleSheet(
            f"QFrame {{ background:{THEME['bg_bar']}; "
            f"border:{THEME['border_width']} dashed {THEME['bg_input_border']}; "
            f"border-radius:{THEME['radius_lg']}; }}"
        )
        pl = QHBoxLayout(pill)
        pl.setContentsMargins(10, 6, 8, 6)
        pl.setSpacing(8)

        grip = DragHandle(self)
        pl.addWidget(grip)

        icon = self.ICONS.get(entry.kind, "•")
        lbl = QLabel(f"{icon}  {entry.summary()}")
        # Wrap rather than widen: an unwrapped long condition pushed the whole
        # chat column past its pane and clipped the line bubbles beside it.
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            f"color:{THEME['text_secondary']}; background:transparent; "
            f"font-size:{THEME['font_size_small']}; font-style:italic;"
        )
        rm = QPushButton("✕")
        rm.setFixedSize(16, 16)
        rm.setStyleSheet(SS["rm_btn"])
        rm.clicked.connect(lambda: self.on_remove(self) if self.on_remove else None)

        pl.addWidget(lbl)
        pl.addWidget(rm)
        outer.addWidget(pill)
        outer.addStretch(1)


class EffectInsertRow(QWidget):
    """A compact row for inserting an item/xp/log effect at the current
    point in the conversation. Fields shown depend on the selected kind."""

    def __init__(self, on_insert=None):
        super().__init__()
        self.on_insert = on_insert
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self.kind_cmb = ui.Dropdown()
        self.kind_cmb.addItems(
            ["Give Item", "Take Item", "Give XP", "Change Routine", "Follow", "Stop Following", "Log Entry"]
        )
        self.kind_cmb.setMinimumWidth(140)
        self.kind_cmb.setStyleSheet(SS["combo"])
        self.kind_cmb.currentIndexChanged.connect(self._update_visibility)

        self.item_edit = QLineEdit()
        self.item_edit.setPlaceholderText("Item  e.g. ItAm_Prot_Fire_01")
        self.item_edit.setStyleSheet(SS["field"])
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 999)
        self.count_spin.setValue(1)
        self.count_spin.setFixedWidth(50)
        self.count_spin.setStyleSheet(SS["spin"])

        self.xp_edit = QLineEdit()
        self.xp_edit.setPlaceholderText("XP constant  e.g. XP_KilledBandit")
        self.xp_edit.setStyleSheet(SS["field"])

        self.routine_edit = QLineEdit()
        self.routine_edit.setPlaceholderText("routine  e.g. Rtn_Lead_MyNpc")
        self.routine_edit.setStyleSheet(SS["field"])

        self.topic_edit = QLineEdit()
        self.topic_edit.setPlaceholderText("Log topic  e.g. CH1_JoinPsi")
        self.topic_edit.setStyleSheet(SS["field"])
        self.status_cmb = ui.Dropdown()
        self.status_cmb.addItems(
            ["LOG_RUNNING", "LOG_SUCCESS", "LOG_FAILED", "LOG_NOTE"]
        )
        self.status_cmb.setMinimumWidth(140)
        self.status_cmb.setStyleSheet(SS["combo"])
        self.entry_edit = QLineEdit()
        self.entry_edit.setPlaceholderText("Log entry text")
        self.entry_edit.setStyleSheet(SS["field"])

        insert_btn = QPushButton("＋ Insert")
        insert_btn.setStyleSheet(SS["add_btn"])
        insert_btn.clicked.connect(self._insert)

        lay.addWidget(self.kind_cmb)
        lay.addWidget(self.item_edit, 1)
        lay.addWidget(self.count_spin)
        lay.addWidget(self.xp_edit, 1)
        lay.addWidget(self.routine_edit, 1)
        lay.addWidget(self.topic_edit, 1)
        lay.addWidget(self.status_cmb)
        lay.addWidget(self.entry_edit, 1)
        lay.addWidget(insert_btn)

        self._update_visibility()

    def _update_visibility(self):
        kind = self.kind_cmb.currentIndex()
        show_item = kind in (0, 1)
        show_xp = kind == 2
        show_routine = kind in (3, 5)  # Change Routine and Stop Following both take a routine name
        show_log = kind == 6
        self.item_edit.setVisible(show_item)
        self.count_spin.setVisible(show_item)
        self.xp_edit.setVisible(show_xp)
        self.routine_edit.setVisible(show_routine)
        self.topic_edit.setVisible(show_log)
        self.status_cmb.setVisible(show_log)
        self.entry_edit.setVisible(show_log)
        if kind == 5:
            self.routine_edit.setPlaceholderText("Routine to resume  e.g. START")
        else:
            self.routine_edit.setPlaceholderText("Change routine  e.g. Rtn_Change_MyNpc")

    def _insert(self):
        kind = self.kind_cmb.currentIndex()
        if kind == 0:
            if not self.item_edit.text().strip():
                return
            e = EffectEntry(
                "give_item",
                item=self.item_edit.text().strip(),
                count=self.count_spin.value(),
            )
        elif kind == 1:
            if not self.item_edit.text().strip():
                return
            e = EffectEntry(
                "take_item",
                item=self.item_edit.text().strip(),
                count=self.count_spin.value(),
            )
        elif kind == 2:
            if not self.xp_edit.text().strip():
                return
            e = EffectEntry("give_xp", xp=self.xp_edit.text().strip())
        elif kind == 3:
            routine = self.routine_edit.text().strip() or "PLACEHOLDER_ROUTINE"
            e = EffectEntry("routine", routine=routine)
        elif kind == 4:
            e = EffectEntry("follow")
        elif kind == 5:
            routine = self.routine_edit.text().strip() or "START"
            e = EffectEntry("unfollow", routine=routine)
        else:
            if not self.topic_edit.text().strip():
                return
            e = EffectEntry(
                "log",
                log_topic=self.topic_edit.text().strip(),
                log_status=self.status_cmb.currentText(),
                log_entry=self.entry_edit.text().strip(),
            )
        if self.on_insert:
            self.on_insert(e)
        self.item_edit.clear()
        self.xp_edit.clear()
        self.routine_edit.clear()
        self.topic_edit.clear()
        self.entry_edit.clear()
        self.count_spin.setValue(1)


class ChatLinesWidget(QWidget):
    """The scene's whole conversational flow: dialog lines and inline
    effects (item/xp/log), in the exact order they'll play out."""

    def __init__(self, on_change=None):
        super().__init__()
        self.on_change = on_change
        self.entries: list = []  # DialogLine | EffectEntry, in flow order
        self.current_speaker = "self"  # NPC speaks first, as is typical
        self._bubble_map = {}
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        self.chat_container = ChatDropContainer(self)
        self.chat_container.setStyleSheet(f"background:{THEME['bg_main']};")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(6, 6, 6, 6)
        self.chat_layout.setSpacing(3)
        self.chat_layout.addStretch()

        self.scroll = QScrollArea()
        self.scroll.setWidget(self.chat_container)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(110)
        self.scroll.setStyleSheet(
            f"QScrollArea {{ border:{THEME['border_width']} solid {THEME['bg_input_border']}; "
            f"border-radius:{THEME['radius_md']}; background:{THEME['bg_main']}; }}"
        )
        root.addWidget(self.scroll, 1)

        inrow = QHBoxLayout()
        inrow.setSpacing(6)
        self.speaker_btn = QPushButton()
        self.speaker_btn.setFixedWidth(64)
        self.speaker_btn.clicked.connect(self._toggle_speaker)
        self.input = ChatInput(on_submit=self._submit, on_toggle=self._toggle_speaker)
        self.input.setPlaceholderText(
            "Type a line, Enter to add  ·  ↑↓ switch speaker  ·  double-click a line to edit"
        )
        self.input.setStyleSheet(SS["field"])
        inrow.addWidget(self.speaker_btn)
        inrow.addWidget(self.input, 1)
        root.addLayout(inrow)

        self.effect_row = EffectInsertRow(on_insert=self._insert_effect)
        root.addWidget(self.effect_row)

        self._update_speaker_style()
        

    def _toggle_speaker(self):
        self.current_speaker = "other" if self.current_speaker == "self" else "self"
        self._update_speaker_style()
        self.input.setFocus()

    def _update_speaker_style(self):
        is_hero = is_hero_speaker(self.current_speaker)
        self.speaker_btn.setText(speaker_display_name(self.current_speaker))
        color = THEME["accent_primary"] if is_hero else THEME["accent_secondary"]
        self.speaker_btn.setStyleSheet(
            f"QPushButton {{ background:{color}; color:{THEME['text_on_accent']}; border:none; "
            f"border-radius:{THEME['radius_md']}; font-weight:600; padding:7px 0; }}"
            f"QPushButton:hover {{ background:{THEME['accent_hover']}; }}"
        )

    def _submit(self, text):
        line = DialogLine(speaker=self.current_speaker, text=text)
        self._append(line)

    def _insert_effect(self, entry):
        self._append(entry)

    def _append(self, entry):
        self.entries.append(entry)
        self._add_bubble(entry)
        if self.on_change:
            self.on_change()
        QTimer.singleShot(
            0,
            lambda: self.scroll.verticalScrollBar().setValue(
                self.scroll.verticalScrollBar().maximum()
            ),
        )

    def _add_bubble(self, entry):
        if isinstance(entry, DialogLine):
            bubble = ChatBubble(
                entry, on_remove=self._remove_bubble, on_edit=self._on_edit
            )
        else:
            bubble = EffectBubble(entry, on_remove=self._remove_bubble)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        self._bubble_map[bubble] = entry

    def _on_edit(self):
        if self.on_change:
            self.on_change()

    def _remove_bubble(self, bubble):
        entry = self._bubble_map.pop(bubble, None)
        if entry in self.entries:
            self.entries.remove(entry)
        bubble.setParent(None)
        bubble.deleteLater()
        if self.on_change:
            self.on_change()

    def reorder_bubble(self, src_bubble, target_bubble, drop_after):
        """Move src_bubble to sit before/after target_bubble (or to the end
        if target_bubble is None), then rebuild self.entries from whatever
        order the bubbles now actually appear in on screen — simplest way
        to guarantee the data model never drifts from what's visible."""
        if src_bubble not in self._bubble_map:
            return
        self.chat_layout.removeWidget(src_bubble)
        if target_bubble is None or target_bubble not in self._bubble_map:
            insert_at = self.chat_layout.count() - 1  # keep trailing stretch last
        else:
            idx = self.chat_layout.indexOf(target_bubble)
            insert_at = idx + 1 if drop_after else idx
        insert_at = max(0, min(insert_at, self.chat_layout.count() - 1))
        self.chat_layout.insertWidget(insert_at, src_bubble)
        self._sync_entries_from_layout()
        if self.on_change:
            self.on_change()

    def _sync_entries_from_layout(self):
        ordered = []
        for i in range(self.chat_layout.count() - 1):  # last slot is the trailing stretch
            item = self.chat_layout.itemAt(i)
            w = item.widget() if item else None
            if w in self._bubble_map:
                ordered.append(self._bubble_map[w])
        self.entries = ordered

    def load_entries(self, entries):
        for b in list(self._bubble_map.keys()):
            b.setParent(None)
            b.deleteLater()
        self._bubble_map = {}
        self.entries = []
        for e in entries:
            self.entries.append(e)
            self._add_bubble(e)

    def get_entries(self):
        return list(self.entries)


# ── Scene conditions ──────────────────────────────────────────────────────────
class SceneCombo(ui.Dropdown):
    """An editable list of the other scenes in this file. It is refilled each time
    it opens, so scenes added or renamed since are always there; typing a DIA_
    instance from another file works too."""

    def __init__(self, names=None):
        super().__init__()
        self.names = names or (lambda: [])
        self.setEditable(True)
        self.lineEdit().setPlaceholderText("a scene the hero must already have heard")
        self.setStyleSheet(SS["combo"])

    def showPopup(self):
        current = self.currentText()
        self.blockSignals(True)
        self.clear()
        self.addItem("")
        self.addItems(self.names())
        self.setEditText(current)
        self.blockSignals(False)
        super().showPopup()


class ConditionRow(QFrame):
    """One extra, hand-typed condition. Only the expression goes in; the scene's
    function wraps it in `if (...) { return 1; }` itself."""

    def __init__(self, text="", on_remove=None, on_change=None):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.edit = QLineEdit(text)
        self.edit.setPlaceholderText("e.g.  Kapitel >= 2   or   Npc_HasItems(other, ItMi_Gold) >= 50")
        self.edit.setStyleSheet(SS["field"])
        rm = QPushButton("✕")
        rm.setFixedSize(22, 22)
        rm.setStyleSheet(SS["rm_btn"])
        rm.clicked.connect(lambda: on_remove(self) if on_remove else None)
        if on_change:
            self.edit.textChanged.connect(on_change)
        lay.addWidget(self.edit, 1)
        lay.addWidget(rm)


# ── Choices ───────────────────────────────────────────────────────────────────
class ChoiceWidget(QFrame):
    def __init__(self, parent=None, on_remove=None):
        super().__init__(parent)
        self.on_remove = on_remove
        self.linked_block = None  # the auto-created follow-up DialogBlock, if any
        self.setStyleSheet(
            f"QFrame {{ background:{THEME['bg_panel']}; "
            f"border:none; "
            f"border-radius:{THEME['radius_md']}; margin:1px; "
            f"border-left:3px solid {THEME['accent_secondary']}; }}"
        )
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(6)
        self.label = QLineEdit()
        self.label.setPlaceholderText("Choice shown to player…")
        self.label.setStyleSheet(
            f"QLineEdit {{ background:{THEME['bg_panel']}; color:{THEME['accent_hover']}; "
            f"border:none; border-radius:2px; padding:4px 6px; font-weight:400; }}"
        )
        self.func = QLineEdit()
        self.func.setPlaceholderText("Handler func")
        self.func.setMinimumWidth(150)
        self.func.setStyleSheet(SS["field"])
        # Whether this reply sends the hero back to the menu it came from
        # (Info_ClearChoices). Untick it and the other choices stay on offer.
        self.back_cb = QCheckBox("Back")
        self.back_cb.setChecked(True)
        self.back_cb.setStyleSheet(SS["check"])
        self.back_cb.setToolTip(
            "Ticked: after this reply the menu closes and the conversation goes back "
            "(Info_ClearChoices).\nUnticked: the other choices stay, so the player can "
            "pick several before going back.")
        rm = QPushButton("✕")
        rm.setFixedSize(22, 22)
        rm.setStyleSheet(SS["rm_btn"])
        rm.clicked.connect(lambda: self.on_remove(self) if self.on_remove else None)
        lay.addWidget(self.label, 3)
        lay.addWidget(self.func, 2)
        lay.addWidget(self.back_cb)
        lay.addWidget(rm)
        ui.fit_font(self, CHAT_PX)

    def lock_func(self, name):
        """Called once a follow-up scene has been auto-created for this choice —
        the function name is now managed by that scene, not free text."""
        self.func.setText(name)
        self.func.setReadOnly(True)
        # Managed by the scene, so it needs no box of its own: the choice text gets
        # the whole row, and the handler's full name is on hover.
        self.func.hide()
        self.label.setToolTip(f"Handler: {name}")

    def get_choice(self):
        return DialogChoice(self.label.text(), self.func.text(), self.back_cb.isChecked())


class BlockEditor(QWidget):
    def __init__(
        self,
        parent=None,
        on_change=None,
        on_choice_added=None,
        on_choice_removed=None,
        is_followup=False,
    ):
        super().__init__(parent)
        self.on_change = on_change
        self.on_choice_added = on_choice_added
        self.on_choice_removed = on_choice_removed
        self.is_followup = is_followup
        self.setStyleSheet(f"QWidget {{ background:{THEME['bg_main']}; }}")
        self._suppress_emit = True
        self._build()
        self._suppress_emit = False

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        def lbl(text, width=60):
            w = QLabel(text)
            if width:                      # 0: as wide as the text, never clipped
                w.setFixedWidth(width)
            w.setStyleSheet(
                f"color:{THEME['text_secondary']}; font-weight:400; font-size:{THEME['font_size_small']};"
            )
            return w

        if self.is_followup:
            hint = QLabel("↳  Follow-up scene, shown after a choice is picked")
            hint.setStyleSheet(
                f"color:{THEME['accent_secondary']}; font-weight:400; "
                f"font-size:{THEME['font_size_small']}; padding-bottom:2px;"
            )
            root.addWidget(hint)

        name_row = QHBoxLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(
            "Choice reply name  ·  e.g. GiveRingOfStrength"
            if self.is_followup
            else "Scene name  ·  e.g. Hello · WannaJoin · KalomsRecipe"
        )
        self.name_edit.setStyleSheet(SS["field"])
        name_row.addWidget(lbl("Name"))
        name_row.addWidget(self.name_edit, 1)
        root.addLayout(name_row)

        tabs = QTabWidget()

        # ── Dialog tab: the chat + inline effects + choices, the primary work surface ──
        dialog_tab = QWidget()
        dt = QVBoxLayout(dialog_tab)
        dt.setContentsMargins(10, 10, 10, 10)
        dt.setSpacing(8)

        # Chat and choices live in a vertical splitter so either panel can be
        # dragged bigger or smaller to suit the scene being edited.
        dialog_splitter = QSplitter(Qt.Orientation.Vertical)
        dialog_splitter.setHandleWidth(8)   # a quiet gap, not a draggable bar
        dialog_splitter.setChildrenCollapsible(False)
        dialog_splitter.setStyleSheet(
            f"QSplitter::handle {{ background:{THEME['bg_main']}; }}"
        )

        self.chat = ChatLinesWidget(on_change=self._emit)
        dialog_splitter.addWidget(self.chat)

        choices_panel = QWidget()
        cp = QVBoxLayout(choices_panel)
        cp.setContentsMargins(0, 0, 0, 0)
        cp.setSpacing(6)

        choices_hdr = QHBoxLayout()
        choices_hdr.addWidget(lbl("Choices", 0))
        add_choice_btn = QPushButton("＋  Add choice")
        add_choice_btn.setStyleSheet(SS["add_btn"])
        add_choice_btn.clicked.connect(lambda: self._add_choice())
        choices_hdr.addStretch()
        choices_hdr.addWidget(add_choice_btn)
        cp.addLayout(choices_hdr)

        self.choices_container = QWidget()
        self.choices_container.setStyleSheet(f"background:{THEME['bg_main']};")
        self.choices_layout = QVBoxLayout(self.choices_container)
        self.choices_layout.setContentsMargins(0, 0, 0, 0)
        self.choices_layout.setSpacing(3)
        choices_scroll = QScrollArea()
        choices_scroll.setWidget(self.choices_container)
        choices_scroll.setWidgetResizable(True)
        choices_scroll.setMinimumHeight(60)
        choices_scroll.setStyleSheet(
            f"QScrollArea {{ border:none; background:{THEME['bg_main']}; }}"
        )
        cp.addWidget(choices_scroll, 1)

        dialog_splitter.addWidget(choices_panel)
        dialog_splitter.setStretchFactor(0, 3)
        dialog_splitter.setStretchFactor(1, 1)
        dialog_splitter.setSizes([420, 190])
        dialog_splitter.handle(1).setEnabled(False)     # fixed split: nothing to drag

        dt.addWidget(dialog_splitter, 1)

        tabs.addTab(dialog_tab, "Dialog")

        # ── Advanced tab: scene metadata only — effects now live inline in Dialog ──
        adv_tab = QWidget()
        av = QVBoxLayout(adv_tab)
        av.setContentsMargins(10, 10, 10, 10)
        av.setSpacing(10)

        if not self.is_followup:
            r2 = QHBoxLayout()
            self.desc_edit = QLineEdit()
            self.desc_edit.setPlaceholderText(
                "Player-visible choice text  (blank for auto/important)"
            )
            self.desc_edit.setStyleSheet(SS["field"])
            r2.addWidget(lbl("Desc"))
            r2.addWidget(self.desc_edit, 1)
            av.addLayout(r2)

            r3 = QHBoxLayout()
            self.perm_cb = QCheckBox("Permanent")
            self.perm_cb.setStyleSheet(SS["check"])
            self.imp_cb = QCheckBox("Important (auto)")
            self.imp_cb.setStyleSheet(SS["check"])
            self.trade_cb = QCheckBox("Trade")
            self.trade_cb.setStyleSheet(SS["check"])
            r3.addWidget(self.perm_cb)
            r3.addWidget(self.imp_cb)
            r3.addWidget(self.trade_cb)
            r3.addStretch()
            av.addLayout(r3)

            r4 = QHBoxLayout()
            self.requires_cmb = SceneCombo(lambda: self.scene_names())
            r4.addWidget(lbl("Requires", 70))
            r4.addWidget(self.requires_cmb, 1)
            av.addLayout(r4)

            xh = QHBoxLayout()
            xh.addWidget(lbl("Also if", 70))
            add_cond = QPushButton("＋  Add condition")
            add_cond.setStyleSheet(SS["add_btn"])
            add_cond.clicked.connect(lambda: self._add_condition())
            xh.addStretch()
            xh.addWidget(add_cond)
            av.addLayout(xh)
            self.cond_layout = QVBoxLayout()
            self.cond_layout.setSpacing(4)
            av.addLayout(self.cond_layout)

            # A condition body that is not `if (...) { return 1; }` cannot be split
            # into the fields above; it is shown here and written back as it was read.
            self.raw_cond_note = QLabel("Custom condition, kept exactly as written:")
            self.raw_cond_edit = QPlainTextEdit()
            self.raw_cond_edit.setFixedHeight(80)
            self.raw_cond_edit.setStyleSheet(SS["field"].replace("QLineEdit", "QPlainTextEdit"))
            self.raw_cond_note.hide()
            self.raw_cond_edit.hide()
            av.addWidget(self.raw_cond_note)
            av.addWidget(self.raw_cond_edit)

            self.stop_cb = QCheckBox("AI_StopProcessInfos at end")
            self.stop_cb.setChecked(True)
            self.stop_cb.setStyleSheet(SS["check"])
            sr = QHBoxLayout()
            sr.addWidget(self.stop_cb)
            sr.addStretch()
            av.addLayout(sr)
        else:
            # Follow-up scenes don't have instance metadata — keep placeholders
            # so get_block()/load_block() stay uniform across both kinds.
            self.desc_edit = QLineEdit()
            self.perm_cb = QCheckBox()
            self.imp_cb = QCheckBox()
            self.trade_cb = QCheckBox()
            self.requires_cmb = SceneCombo()
            self.cond_layout = QVBoxLayout()
            self.raw_cond_edit = QPlainTextEdit()
            self.stop_cb = QCheckBox()
            note = QLabel(
                "Whether this reply goes back to the main menu is set on its choice row "
                "(the Back box) in the scene it belongs to.\n"
                "Give/take items, XP, and log entries are added inline in the Dialog tab."
            )
            note.setWordWrap(True)
            note.setStyleSheet(
                f"color:{THEME['text_muted']}; font-size:{THEME['font_size_small']}; font-style:italic;"
            )
            av.addWidget(note)
        av.addStretch()

        tabs.addTab(adv_tab, "Advanced")
        root.addWidget(tabs, 1)

        for w in [self.name_edit, self.desc_edit]:
            w.textChanged.connect(self._emit)
        self.requires_cmb.currentTextChanged.connect(self._emit)
        self.raw_cond_edit.textChanged.connect(self._emit)
        # One text size for the whole panel: the chat bubble's.
        ui.fit_font(dialog_tab, CHAT_PX)
        ui.fit_font(adv_tab, CHAT_PX)
        for w in [self.perm_cb, self.imp_cb, self.trade_cb, self.stop_cb]:
            w.stateChanged.connect(self._emit)

    def scene_names(self):
        """Other scenes this one could require; the page supplies the list."""
        return []

    def _add_condition(self, text=""):
        row = ConditionRow(text, on_remove=self._rm_condition, on_change=self._emit)
        ui.fit_font(row, CHAT_PX)
        self.cond_layout.addWidget(row)
        if not text:
            row.edit.setFocus()
        self._emit()
        return row

    def _rm_condition(self, row):
        row.setParent(None)
        row.deleteLater()
        self._emit()

    def _conditions(self):
        return [self.cond_layout.itemAt(i).widget().edit.text().strip()
                for i in range(self.cond_layout.count())
                if self.cond_layout.itemAt(i).widget() is not None
                and self.cond_layout.itemAt(i).widget().edit.text().strip()]

    def set_requires(self, name):
        """Point the Requires box at `name` without counting it as an edit."""
        self.requires_cmb.blockSignals(True)
        self.requires_cmb.setEditText(name)
        self.requires_cmb.blockSignals(False)

    def requires_text(self):
        return self.requires_cmb.currentText().strip()

    def _emit(self, *_):
        if getattr(self, "_suppress_emit", False):
            return
        if self.on_change:
            self.on_change()

    def _add_choice(self, choice=None, is_loaded=False):
        cw = ChoiceWidget(on_remove=self._rm_choice)
        if choice:
            cw.label.setText(choice.label)
            cw.func.setText(choice.func_name)
            cw.back_cb.setChecked(bool(choice.back))
        cw.label.textChanged.connect(self._emit)
        cw.func.textChanged.connect(self._emit)
        cw.back_cb.stateChanged.connect(self._emit)
        self.choices_layout.addWidget(cw)
        if not is_loaded and self.on_choice_added:
            self.on_choice_added(cw)  # lets MainWindow auto-create the follow-up scene
        self._emit()
        return cw

    def _rm_choice(self, w):
        if self.on_choice_removed:
            self.on_choice_removed(w)
        w.setParent(None)
        w.deleteLater()
        self._emit()

    def _clear_choices(self):
        while self.choices_layout.count():
            item = self.choices_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def get_block(self):
        b = DialogBlock()
        b.name = self.name_edit.text().strip()
        b.is_followup = self.is_followup
        if not self.is_followup:
            b.description = self.desc_edit.text().strip()
            b.permanent = 1 if self.perm_cb.isChecked() else 0
            b.important = 1 if self.imp_cb.isChecked() else 0
            b.is_trade = self.trade_cb.isChecked()
            b.requires = self.requires_text()
            b.extra_conditions = self._conditions()
            b.condition_expr = self.raw_cond_edit.toPlainText().strip()
            b.stop_after = self.stop_cb.isChecked()
        b.entries = self.chat.get_entries()
        for i in range(self.choices_layout.count()):
            w = self.choices_layout.itemAt(i).widget()
            if isinstance(w, ChoiceWidget):
                b.choices.append(w.get_choice())
        return b

    def load_block(self, b):
        self._suppress_emit = True
        self.name_edit.setText(b.name)
        if not self.is_followup:
            self.desc_edit.setText(b.description)
            self.perm_cb.setChecked(bool(b.permanent))
            self.imp_cb.setChecked(bool(b.important))
            self.trade_cb.setChecked(bool(b.is_trade))
            self.set_requires(b.requires)
            while self.cond_layout.count():
                w = self.cond_layout.takeAt(0).widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()
            for text in b.extra_conditions:
                self._add_condition(text)
            self.raw_cond_edit.setPlainText(b.condition_expr)
            self.raw_cond_note.setVisible(bool(b.condition_expr))
            self.raw_cond_edit.setVisible(bool(b.condition_expr))
            self.stop_cb.setChecked(bool(b.stop_after))
        self.chat.load_entries(b.entries)
        self._clear_choices()
        for ch in b.choices:
            self._add_choice(ch, is_loaded=True)
        self._suppress_emit = False

    def get_choice_widgets(self):
        return [
            self.choices_layout.itemAt(i).widget()
            for i in range(self.choices_layout.count())
        ]


class ElidedLabel(QLabel):
    """A one-line label that ends in an ellipsis when its text does not fit, rather
    than being cut off; the full text is the tooltip."""

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setPen(self.palette().windowText().color())
        painter.setFont(self.font())
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        painter.drawText(self.rect(), int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft), text)


class BlockListItem(QFrame):
    def __init__(
        self, idx, name, parent=None, on_select=None, on_remove=None, is_followup=False, depth=0
    ):
        super().__init__(parent)
        self.idx = idx
        self.on_select = on_select
        self.on_remove = on_remove
        self._active = False
        self.is_followup = is_followup
        self.depth = depth
        self.setFixedHeight(32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        lay = QHBoxLayout(self)
        self.left_margin = 14 + (self.depth * 14) if self.is_followup else 10 + (self.depth * 10)
        lay.setContentsMargins(self.left_margin, 4, 4, 4)
        lay.setSpacing(4)
        self.lbl = ElidedLabel(self._label_text(name or f"Scene {idx+1}"))
        self.lbl.setToolTip(self.lbl.text())
        rm = QPushButton("✕")
        rm.setFixedSize(18, 18)
        rm.setStyleSheet(SS["rm_btn"])
        rm.clicked.connect(lambda: on_remove(self.idx) if on_remove else None)
        lay.addWidget(self.lbl, 1)
        lay.addWidget(rm)
        self._update_style()

    def _update_style(self):
        # Same states as the NPC tab's list: quiet text, a hover tint, and an
        # accent tint for the row you are on.
        if self._active:
            bg, color, weight = THEME["accent_soft"], THEME["text_primary"], 600
        else:
            bg = "transparent"
            color = THEME["text_muted"]
            weight = 400
        self.setStyleSheet(
            f"BlockListItem {{ background:{bg}; border:none; "
            f"border-radius:{THEME['radius_sm']}; }}"
            f"BlockListItem:hover {{ background:"
            f"{THEME['accent_soft'] if self._active else THEME['bg_hover']}; }}")
        self.lbl.setStyleSheet(
            f"color:{color}; font-weight:{weight}; background:transparent; "
            f"font-size:{THEME['font_size_scene']};")

    def set_active(self, v):
        self._active = v
        self._update_style()

    def _label_text(self, text):
        if not self.is_followup:
            return text
        return ("↳ " * (self.depth + 1)) + text

    def update_name(self, n):
        self.lbl.setText(self._label_text(n or f"Scene {self.idx+1}"))
        self.lbl.setToolTip(self.lbl.text())

    def needed_width(self):
        """The row width at which its name shows in full, even when selected (bold)."""
        self.lbl.ensurePolished()
        font = QFont(self.lbl.font())
        font.setBold(True)
        text = QFontMetrics(font).horizontalAdvance(self.lbl.text())
        return self.left_margin + text + 8 + 18 + 4 + 4

    def mousePressEvent(self, e):
        if self.on_select:
            self.on_select(self.idx)