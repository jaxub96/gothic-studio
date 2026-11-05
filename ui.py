"""
ui.py - the standard component set. Build screens out of these, not raw Qt.

Before this existed every module wrote its own inline stylesheet, and the app
drifted: 11 different QLabel styles, 5 different button styles, 5 font sizes,
4 button heights. Anything reached for twice belongs here instead.

Rules
  1. No module outside this one writes a stylesheet. If you need a new look,
     add a component or a variant here.
  2. Every control is built by a function that takes its value and its
     callback, so wiring looks the same everywhere.
  3. Text over glyphs. A button says what it does; an icon needs a tooltip and
     a tooltip is not discoverable.

Layout vocabulary
  section(...)      a titled group of fields
  field(...)        label above a control, with an optional hint below
  row()             plain container with the standard gap

Controls
  code_view   read-only script panel, Ctrl+wheel / Ctrl +/-/0 zooms
  text_input  dropdown  search_dropdown  search_input
  slider  spin  checkbox  radio_row  tree  listbox

Buttons
  button(text, on_click, variant=...)  variants: primary, default, subtle, danger
"""

import weakref

from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QCompleter, QFrame,
                             QTabWidget,
                             QHBoxLayout, QLabel, QLineEdit, QListWidget,
                             QPushButton, QRadioButton, QScrollArea, QSlider,
                             QSpinBox, QStackedWidget,
                             QTextEdit, QTimeEdit, QTreeWidget, QVBoxLayout,
                             QWidget)

import theme
from theme import THEME

# --- one scale for everything ------------------------------------------------
GAP = 8                 # between related controls
SPACING = 16            # between fields
SECTION_SPACING = 22    # between sections
PADDING = 16            # inside a panel
BUTTON_H = 42           # every normal button
COMPACT_H = 32          # toolbar buttons
LABEL_W = 224           # label column - fits the longest label at this size
NUMBER_W = 128          # numeric entry fields
POPUP_ITEMS = 12        # rows a dropdown shows before it scrolls

FONT_LABEL = THEME["font_size_small"]
FONT_HINT = THEME["font_size_tiny"]
FONT_VALUE = THEME["font_size_small"]


# --- text --------------------------------------------------------------------

def heading(text):
    """A section title."""
    w = QLabel(text[:1].upper() + text[1:].lower() if text.isupper() else text)
    w.setStyleSheet(
        f"color:{THEME['text_secondary']}; font-size:{FONT_LABEL}; font-weight:600; "
        f"background:transparent; font-family:{THEME['font_ui']};")
    return w


def label(text):
    """The name of a control."""
    w = QLabel(text)
    w.setStyleSheet(
        f"color:{THEME['text_secondary']}; font-size:{FONT_LABEL}; "
        f"font-weight:400; background:transparent;")
    return w


def hint(text):
    """A quiet line of explanation under a control."""
    w = QLabel(text)
    w.setWordWrap(True)
    w.setStyleSheet(
        f"color:{THEME['text_muted']}; font-size:{FONT_HINT}; "
        f"background:transparent;")
    return w


def value_label(text="", width=88):
    """The live number beside a slider."""
    w = QLabel(text)
    w.setFixedWidth(width)
    w.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    w.setStyleSheet(
        f"color:{THEME['text_primary']}; font-size:{FONT_VALUE}; "
        f"font-weight:400; background:transparent;")
    return w


def divider():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{THEME['bg_border']}; border:none;")
    return line


# --- containers ---------------------------------------------------------------


def row(spacing=GAP):
    lay = QHBoxLayout()
    lay.setSpacing(spacing)
    lay.setContentsMargins(0, 0, 0, 0)
    return lay


def section(layout, title):
    """Start a titled group. Returns nothing; just adds the header."""
    if layout.count():
        layout.addSpacing(SECTION_SPACING)
    layout.addWidget(heading(title))
    layout.addWidget(divider())
    layout.addSpacing(GAP)


def _is_fixed_width(widget):
    return widget.minimumWidth() and widget.minimumWidth() == widget.maximumWidth()


def field(layout, text, widget, help_text=None):
    """A labelled control.

    Every label sits in the same left column and every control starts at the
    same x, so a form reads as one grid instead of a ragged edge. Controls that
    set their own width (numbers, short lists) keep it; the rest fill the row.
    """
    line = row()
    name = label(text)
    name.setFixedWidth(LABEL_W)
    name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    line.addWidget(name)
    if _is_fixed_width(widget):
        line.addWidget(widget)
        line.addStretch()
    else:
        line.addWidget(widget, 1)
    layout.addLayout(line)
    if help_text:
        layout.addWidget(hint(help_text))
    layout.addSpacing(SPACING)
    return widget


#: field_row used to mean "label beside" as opposed to "label above". Now that
#: every field is label-beside, it is the same thing.
field_row = field


def field_group(layout, items, help_text=None):
    """Several short fields on one line, e.g. Name / ID / Level.

    Each label sits directly left of its own control, so the row stays legible
    without forcing three separate rows for three small values.
    """
    line = row(SPACING)
    for text, widget, stretch in items:
        line.addWidget(label(text))          # natural width; clipping it looks broken
        line.addWidget(widget, stretch)
    if not any(stretch for _, _, stretch in items):
        line.addStretch()
    layout.addLayout(line)
    if help_text:
        note = row()
        note.addWidget(hint(help_text), 1)
        layout.addLayout(note)
    layout.addSpacing(SPACING)


# --- inputs -------------------------------------------------------------------

def _input_css(widget_name):
    return (
        f"{widget_name} {{ background:{THEME['bg_input']}; "
        f"  color:{THEME['text_primary']}; "
        f"  border:{THEME['border_width']} solid {THEME['bg_input_border']}; "
        f"  border-radius:{THEME['radius_sm']}; padding:5px 8px; "
        f"  font-family:{THEME['font_ui']}; font-size:{FONT_LABEL}; "
        f"  selection-background-color:{THEME['accent_primary']}; }}"
        f"{widget_name}:focus {{ border:{THEME['border_width']} solid "
        f"  {THEME['accent_primary']}; }}"
        f"{widget_name}:disabled {{ color:{THEME['text_muted']}; "
        f"  background:{THEME['bg_panel']}; }}")


def text_input(value="", placeholder="", on_change=None, validator=None):
    w = QLineEdit(value)
    w.setPlaceholderText(placeholder)
    w.setMinimumHeight(BUTTON_H)
    w.setStyleSheet(_input_css("QLineEdit"))
    if validator:
        w.setValidator(validator)
    if on_change:
        w.textChanged.connect(on_change)
    return w


def _attach_completer(widget, items):
    completer = QCompleter([str(i) for i in items], widget)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    widget.setCompleter(completer)
    return completer


def search_input(items, value="", placeholder="", on_change=None):
    """Free text with type-anywhere completion - for very long lists."""
    w = text_input(value, placeholder or f"Search {len(items)}...", on_change)
    if items:
        _attach_completer(w, items)
    return w


def _combo_css():
    return (
        _input_css("QComboBox")
        # combobox-popup:0 is the switch that stops Qt showing the list as a
        # menu centred on the current item - which draws it straight over the
        # field as soon as the selection is not the first entry. With it off
        # the list drops below the field and scrolls, and setMaxVisibleItems
        # starts working.
        + "QComboBox { combobox-popup: 0; }"
        # A combo with no arrow reads as a text field. Qt can draw the marker
        # from borders alone, so no image asset is needed.
        + f"QComboBox::drop-down {{ subcontrol-origin:padding; "
        f"  subcontrol-position:center right; width:26px; border:none; "
        f"  border-left:{THEME['border_width']} solid {THEME['bg_input_border']}; "
        f"  background:{THEME['bg_panel']}; "
        f"  border-top-right-radius:{THEME['radius_sm']}; "
        f"  border-bottom-right-radius:{THEME['radius_sm']}; }}"
        f"QComboBox::down-arrow {{ width:0; height:0; "
        f"  border-left:5px solid transparent; "
        f"  border-right:5px solid transparent; "
        f"  border-top:6px solid {THEME['text_secondary']}; }}"
        f"QComboBox::down-arrow:hover {{ "
        f"  border-top:6px solid {THEME['accent_primary']}; }}"
        f"QComboBox:hover {{ border-color:{THEME['accent_primary']}; }}"
        f"QComboBox QAbstractItemView {{ background:{THEME['bg_panel']}; "
        f"  color:{THEME['text_primary']}; "
        f"  selection-background-color:{THEME['accent_primary']}; "
        f"  selection-color:{THEME['text_on_accent']}; outline:none; "
        f"  border:{THEME['border_width']} solid {THEME['bg_border']}; }}"
        f"QComboBox QAbstractItemView::item {{ min-height:{BUTTON_H - 12}px; "
        f"  padding:2px 8px; }}"
        f"QComboBox QAbstractScrollArea QScrollBar:vertical {{ "
        f"  background:{THEME['bg_panel']}; width:12px; border:none; }}"
        f"QComboBox QAbstractScrollArea QScrollBar::handle:vertical {{ "
        f"  background:{THEME['bg_border_strong']}; border-radius:4px; min-height:24px; }}")


class Dropdown(QComboBox):
    """A QComboBox that keeps keyboard focus after you pick from its list.

    Picking an item fires on_change, which redraws the previews; on some
    platforms that leaves focus somewhere else, so the arrow keys stop
    stepping through the choices. Taking focus back once the list has closed
    makes click-then-arrow work everywhere.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Size from a short minimum, not the longest entry: one long label
        # ("Militia - upright, martial  ·  HUMANS_MILITIA.MDS") would otherwise
        # set the width of the whole page and, through it, the window.
        self.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(14)

    def hidePopup(self):
        super().hidePopup()
        QTimer.singleShot(0, self._refocus)

    def _refocus(self):
        if self.isVisible() and self.isEnabled():
            self.setFocus(Qt.FocusReason.PopupFocusReason)


def dropdown(items, value=None, on_change=None):
    w = Dropdown()
    w.addItems([str(i) for i in items])
    w.setMinimumHeight(BUTTON_H)
    w.setMaxVisibleItems(POPUP_ITEMS)
    w.setStyleSheet(_combo_css())
    if value is not None and str(value) in [str(i) for i in items]:
        w.setCurrentText(str(value))
    if on_change:
        w.currentTextChanged.connect(on_change)
    return w


def search_dropdown(items, value=None, on_change=None):
    """A dropdown you can type into - for lists too long to scroll."""
    w = dropdown(items, value, on_change)
    w.setEditable(True)
    w.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    w.lineEdit().setPlaceholderText(f"type to search {len(items)}")
    _attach_completer(w, items)
    if value is not None:
        w.setCurrentText(str(value))
    return w


def slider(lo, hi, value, on_change, fmt=str, width=88):
    """A slider with its value shown. Returns the composite widget.

    `.slider` and `.readout` are exposed for the rare caller that needs them.
    """
    holder = QWidget()
    line = QHBoxLayout(holder)
    line.setContentsMargins(0, 0, 0, 0)
    line.setSpacing(GAP)

    bar = QSlider(Qt.Orientation.Horizontal)
    bar.setMinimum(lo)
    bar.setMaximum(hi)
    bar.setValue(value)
    bar.setStyleSheet(
        f"QSlider::groove:horizontal {{ background:{THEME['bg_input_border']}; "
        f"  height:4px; border-radius:2px; }}"
        f"QSlider::sub-page:horizontal {{ background:{THEME['accent_primary']}; "
        f"  height:4px; border-radius:2px; }}"
        f"QSlider::handle:horizontal {{ background:{THEME['accent_primary']}; "
        f"  width:14px; height:14px; margin:-5px 0; border-radius:7px; }}"
        f"QSlider::handle:horizontal:disabled {{ "
        f"  background:{THEME['bg_border']}; }}")

    out = value_label(fmt(value), width)
    bar.valueChanged.connect(lambda v: out.setText(fmt(v)))
    bar.valueChanged.connect(on_change)

    line.addWidget(bar, 1)
    line.addWidget(out)
    holder.slider = bar
    holder.readout = out
    return holder


def time_input(hour, minute, on_change, width=NUMBER_W):
    """A clock time, HH:MM. on_change gets (hour, minute)."""
    w = QTimeEdit(QTime(int(hour) % 24, int(minute) % 60))
    w.setDisplayFormat("HH:mm")
    w.setFixedWidth(width)
    w.setMinimumHeight(BUTTON_H)
    w.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
    w.setStyleSheet(
        _input_css("QTimeEdit")
        + "QTimeEdit::up-button, QTimeEdit::down-button "
          "{ subcontrol-origin:border; width:0; }")
    w.timeChanged.connect(lambda t: on_change(t.hour(), t.minute()))
    return w


def card():
    """A softly framed group inside a page, e.g. one routine entry.

    Returns (frame, its QVBoxLayout).
    """
    frame = QFrame()
    frame.setObjectName("card")
    frame.setStyleSheet(
        f"QFrame#card {{ background:{THEME['bg_panel']}; "
        f"  border:{THEME['border_width']} solid {THEME['bg_border']}; "
        f"  border-radius:{THEME['radius_md']}; }}")
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(PADDING, GAP + 4, PADDING, 0)
    lay.setSpacing(0)
    return frame, lay


def spin(lo, hi, value, on_change, suffix="", width=110):
    """Kept as the old name for `number` - there is one numeric control."""
    return number(lo, hi, value, on_change, suffix, width)


def checkbox(text, checked=False, on_change=None, tooltip="", compact=False):
    w = QCheckBox("  " + text)
    w.setChecked(checked)
    if tooltip:
        w.setToolTip(tooltip)
    w.setMinimumHeight(COMPACT_H if compact else BUTTON_H)
    w.setStyleSheet(
        f"QCheckBox {{ color:{THEME['text_secondary']}; "
        f"  font-size:{FONT_LABEL}; spacing:4px; background:transparent; }}"
        f"QCheckBox::indicator {{ width:14px; height:14px; "
        f"  border:{THEME['border_width']} solid {THEME['bg_border_strong']}; "
        f"  border-radius:3px; background:{THEME['bg_input']}; }}"
        f"QCheckBox::indicator:checked {{ background:{THEME['accent_primary']}; "
        f"  border-color:{THEME['accent_primary']}; }}"
        f"QCheckBox:disabled {{ color:{THEME['text_muted']}; }}")
    if on_change:
        w.stateChanged.connect(lambda s: on_change(bool(s)))
    return w


def radio_row(text, options, value, on_change):
    """A labelled row of mutually exclusive choices.

    `options` is [(label, value), ...]. Returns the row widget.
    """
    from PyQt6.QtWidgets import QButtonGroup

    holder = QWidget()
    holder.setStyleSheet("background:transparent;")
    holder.setMinimumHeight(BUTTON_H)
    line = QHBoxLayout(holder)
    line.setContentsMargins(0, 0, 0, 0)
    line.setSpacing(GAP)

    name = label(text)
    name.setFixedWidth(LABEL_W)
    line.addWidget(name)

    group = QButtonGroup(holder)
    css = (f"QRadioButton {{ color:{THEME['text_secondary']}; "
           f"  font-size:{FONT_LABEL}; spacing:4px; background:transparent; }}"
           f"QRadioButton::indicator {{ width:12px; height:12px; "
           f"  border:{THEME['border_width']} solid {THEME['bg_border_strong']}; "
           f"  border-radius:6px; background:{THEME['bg_input']}; }}"
           f"QRadioButton::indicator:checked {{ "
           f"  background:{THEME['accent_primary']}; "
           f"  border-color:{THEME['accent_primary']}; }}")
    for text_i, value_i in options:
        btn = QRadioButton(text_i)
        btn.setStyleSheet(css)
        btn.setChecked(value_i == value)
        btn.toggled.connect(
            lambda checked, v=value_i: checked and on_change(v))
        group.addButton(btn)
        line.addWidget(btn)
    line.addStretch()
    holder.group = group
    return holder


# --- lists --------------------------------------------------------------------

def _list_css(widget_name):
    return (
        f"{widget_name} {{ background:{THEME['bg_input']}; "
        f"  color:{THEME['text_primary']}; "
        f"  border:none; border-radius:{THEME['radius_md']}; "
        f"  font-family:{THEME['font_ui']}; font-size:{FONT_LABEL}; }}"
        f"{widget_name}::item {{ padding:5px 6px; }}"
        f"{widget_name}::item:selected {{ background:{THEME['accent_primary']}; "
        f"  color:{THEME['text_on_accent']}; }}"
        f"{widget_name}::item:hover {{ background:{THEME['bg_bar']}; }}"
        f"QScrollBar:vertical {{ background:{THEME['bg_panel']}; width:8px; "
        f"  border:none; }}"
        f"QScrollBar::handle:vertical {{ background:{THEME['bg_border_strong']}; "
        f"  border-radius:4px; }}"
        f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ "
        f"  height:0; }}")


def listbox(on_select=None):
    w = QListWidget()
    w.setStyleSheet(_list_css("QListWidget"))
    if on_select:
        w.currentRowChanged.connect(on_select)
    return w


def tree(on_select=None):
    w = QTreeWidget()
    w.setHeaderHidden(True)
    w.setStyleSheet(_list_css("QTreeWidget"))
    if on_select:
        w.itemSelectionChanged.connect(on_select)
    return w


def bold_font():
    return QFont(THEME["font_ui"].split(",")[0].strip(), 9, QFont.Weight.Bold)


# --- buttons ------------------------------------------------------------------

PRIMARY, DEFAULT, SUBTLE, DANGER = "primary", "default", "subtle", "danger"

_VARIANTS = {
    PRIMARY: ("accent_primary", "text_on_accent", "accent_hover"),
    DEFAULT: ("bg_panel", "text_primary", "bg_hover"),
    SUBTLE: ("bg_main", "text_muted", "bg_hover"),
    DANGER: ("accent_gold", "text_on_accent", "accent_hover"),
}


def _button_css(variant, height):
    bg, fg, hover = _VARIANTS.get(variant, _VARIANTS[DEFAULT])
    solid = variant in (PRIMARY, DANGER)
    edge = THEME[bg] if solid else THEME['bg_input_border']
    return (
        f"QPushButton {{ background:{THEME[bg]}; color:{THEME[fg]}; "
        f"  border:{THEME['border_width']} solid {edge}; "
        f"  border-radius:{THEME['radius_sm']}; padding:0 12px; "
        f"  font-family:{THEME['font_ui']}; font-size:{FONT_LABEL}; "
        f"  font-weight:400; min-height:{height}px; }}"
        f"QPushButton:hover {{ background:{THEME[hover]}; "
        f"  border-color:{THEME[hover] if solid else THEME['bg_border_strong']}; "
        f"  color:{THEME[fg] if solid else THEME['text_primary']}; }}"
        f"QPushButton:disabled {{ color:{THEME['text_muted']}; "
        f"  background:{THEME['bg_panel']}; }}")


def button(text, on_click=None, variant=DEFAULT, tooltip="", compact=False):
    b = QPushButton(text)
    height = COMPACT_H if compact else BUTTON_H
    b.setStyleSheet(_button_css(variant, height))
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if tooltip:
        b.setToolTip(tooltip)
    if on_click:
        b.clicked.connect(lambda _=False: on_click())
    return b


# --- legacy style keys --------------------------------------------------------
# The chat editor was written against theme.SS. Re-exporting the same keys from
# here means it picks up the standard look with a one-line import change,
# instead of a 900-line rewrite - and there is then exactly one definition of
# what a text field looks like.

def _small_button_css(color_key, height=COMPACT_H):
    return (
        f"QPushButton {{ background:{THEME['bg_bar']}; color:{THEME[color_key]}; "
        f"  border:{THEME['border_width']} solid {THEME['bg_border']}; "
        f"  border-radius:{THEME['radius_sm']}; padding:0 10px; "
        f"  font-size:{FONT_LABEL}; font-weight:400; min-height:{height}px; }}"
        f"QPushButton:hover {{ background:{THEME['bg_hover']}; "
        f"  color:{THEME['text_primary']}; }}")


def _build_ss():
    return {
        "field": _input_css("QLineEdit"),
        "field_readonly": (
            f"QLineEdit {{ background:{THEME['bg_panel']}; color:{THEME['text_muted']}; "
            f"  border:{THEME['border_width']} solid {THEME['bg_input_border']}; "
            f"  border-radius:{THEME['radius_sm']}; padding:5px 8px; "
            f"  font-family:{THEME['font_ui']}; font-size:{FONT_LABEL}; "
            f"  font-style:italic; }}"),
        "combo": _combo_css(),
        "spin": _input_css("QSpinBox"),
        "check": (
            f"QCheckBox {{ color:{THEME['text_secondary']}; font-size:{FONT_LABEL}; "
            f"  spacing:4px; background:transparent; }}"
            f"QCheckBox::indicator {{ width:14px; height:14px; "
            f"  border:{THEME['border_width']} solid {THEME['bg_border_strong']}; "
            f"  border-radius:3px; background:{THEME['bg_input']}; }}"
            f"QCheckBox::indicator:checked {{ background:{THEME['accent_primary']}; "
            f"  border-color:{THEME['accent_primary']}; }}"),
        "add_btn": _small_button_css("accent_primary"),
        "rm_btn": (
            f"QPushButton {{ background:transparent; color:{THEME['text_muted']}; "
            f"  border:none; font-size:{FONT_LABEL}; }}"
            f"QPushButton:hover {{ color:{THEME['accent_primary']}; }}"),
    }


# Rebuilt in place when the theme changes, so `from ui import SS` stays live.
SS = _build_ss()


def _rebuild_ss():
    SS.clear()
    SS.update(_build_ss())


theme.on_change(_rebuild_ss)


def placeholder(text):
    """What an empty pane says."""
    w = QLabel(text)
    w.setAlignment(Qt.AlignmentFlag.AlignCenter)
    w.setStyleSheet(
        f"color:{THEME['text_muted']}; font-size:{THEME['font_size_placeholder']}; "
        f"font-family:{THEME['font_ui']}; font-style:italic; background:transparent;")
    return w


def image_frame(height, text=""):
    """A bordered box that holds a picture, or says why it cannot."""
    w = QLabel(text)
    w.setFixedHeight(height)
    w.setMinimumWidth(96)
    w.setAlignment(Qt.AlignmentFlag.AlignCenter)
    w.setStyleSheet(
        f"background:{THEME['bg_code']}; border:none; "
        f"border-radius:{THEME['radius_md']}; color:{THEME['text_muted']}; "
        f"font-size:{FONT_HINT}; font-style:italic;")
    return w


# --- the shared page frame ----------------------------------------------------

class _PageScroll(QScrollArea):
    """Scrolls a page vertically only, and asks for the page's full width so
    nothing is clipped at the right edge; height is what is free to scroll."""

    def _width(self):
        page_ = self.widget()
        bar = self.verticalScrollBar().sizeHint().width()
        return (page_.minimumSizeHint().width() if page_ else 0) + bar

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        hint.setWidth(max(hint.width(), self._width()))
        return hint

    def sizeHint(self):
        hint = super().sizeHint()
        hint.setWidth(max(hint.width(), self._width()))
        return hint


class SideTabs(QWidget):
    """Tabs down the left edge: a hard-ruled list beside a stack of pages.

    Offers the few QTabWidget methods the pages use.
    """

    currentChanged = pyqtSignal(int)
    LIST_WIDTH = 168

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._list = QListWidget()
        self._list.setFixedWidth(self.LIST_WIDTH)
        self._list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._list.setStyleSheet(
            f"QListWidget {{ background:{THEME['bg_panel']}; border:none; "
            f"  border-right:{THEME['border_width']} solid {THEME['bg_border']}; "
            f"  outline:none; padding:10px 8px; "
            f"  font-family:{THEME['font_ui']}; font-size:{FONT_LABEL}; "
            f"  font-weight:400; }}"
            f"QListWidget::item {{ padding:8px 10px; margin-bottom:2px; "
            f"  color:{THEME['text_muted']}; border-radius:{THEME['radius_sm']}; }}"
            f"QListWidget::item:hover {{ color:{THEME['text_primary']}; "
            f"  background:{THEME['bg_hover']}; }}"
            # A quiet accent tint, not an inverted block: it says "you are
            # here" without being the loudest thing on screen.
            f"QListWidget::item:selected {{ background:{THEME['accent_soft']}; "
            f"  color:{THEME['text_primary']}; }}")
        self._stack = QStackedWidget()
        lay.addWidget(self._list)
        lay.addWidget(self._stack, 1)
        self._list.currentRowChanged.connect(self._on_row)

    def _on_row(self, index):
        if index >= 0:
            self._stack.setCurrentIndex(index)
            self.currentChanged.emit(index)

    def set_list_width(self, width):
        """Resize the tab list, e.g. so its right rule meets another edge."""
        self._list.setFixedWidth(width)

    def clear(self):
        """Drop every tab and its page, so the pages can be rebuilt."""
        self._list.clear()
        while self._stack.count():
            page_ = self._stack.widget(0)
            self._stack.removeWidget(page_)
            page_.deleteLater()

    def addTab(self, widget, title):
        # Each page scrolls on its own, so a page that grows (another routine,
        # a long inventory) adds a scroll bar instead of stretching the window.
        scroll = _PageScroll()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")
        scroll.setWidget(widget)
        self._list.addItem(title)
        self._stack.addWidget(scroll)
        if self._list.currentRow() < 0:
            self._list.setCurrentRow(0)

    def count(self):
        return self._stack.count()

    def widget(self, index):
        """The page itself, not the scroll area around it."""
        scroll = self._stack.widget(index)
        return scroll.widget() if scroll is not None else None

    def tabText(self, index):
        return self._list.item(index).text()

    def currentIndex(self):
        return self._stack.currentIndex()

    def setCurrentIndex(self, index):
        self._list.setCurrentRow(index)


class SidePanel(QWidget):
    """The right-hand side of a page: preview tabs, a status line, actions.

    Both the NPC page and the Dialog page use this, so the two halves of the
    app have the same shape - previews in the same place, Validate and Save in
    the same corner, the status line saying the same kind of thing.
    """

    def __init__(self, on_validate, on_save, on_save_as, save_tip="", on_open=None,
                 parent=None):
        super().__init__(parent)
        col = QVBoxLayout(self)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(GAP)

        self.tabs = QTabWidget()
        col.addWidget(self.tabs, 1)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(f"background:{THEME['bg_border']}; border:none;")
        col.addWidget(rule)

        self.status = hint("")
        col.addWidget(self.status)

        actions = row()
        actions.addWidget(button("Validate", on_validate, DEFAULT,
                                 "Check every identifier against Content/"))
        actions.addWidget(button("Save as...", on_save_as, DEFAULT,
                                 "Save somewhere other than the mod"))
        if on_open:
            actions.addWidget(button("Open...", on_open, DEFAULT,
                                     "Load a saved .d file back into the editor"))
        actions.addStretch()
        actions.addWidget(button("Save to mod", on_save, PRIMARY, save_tip))
        col.addLayout(actions)

    def add_tab(self, widget, title):
        self.tabs.addTab(widget, title)
        return widget

    def current_tab(self):
        return self.tabs.currentIndex()

    def say(self, text):
        self.status.setText(text)


def page(work_area, side_panel, work_stretch=3, side_stretch=2, left=PADDING):
    """A whole page: what you edit on the left, what you get on the right."""
    holder = QWidget()
    lay = QHBoxLayout(holder)
    lay.setContentsMargins(left, 0, PADDING, PADDING)
    lay.setSpacing(PADDING)
    lay.addWidget(work_area, work_stretch)
    lay.addWidget(side_panel, side_stretch)
    return holder


def report_omissions(parent, title, notes, limit=25):
    """Tell the user what an Open could not carry into the editor, if anything."""
    if not notes:
        return
    from PyQt6.QtWidgets import QMessageBox

    shown = chr(10).join("- " + n for n in notes[:limit])
    more = f"{chr(10)}...and {len(notes) - limit} more" if len(notes) > limit else ""
    QMessageBox.information(
        parent, title,
        f"Opened. {len(notes)} thing(s) in the file have no place in the editor "
        f"and will not be written back:{chr(10)}{chr(10)}{shown}{more}")


def code_view_css(size=None):
    """The read-only script preview."""
    size = size or THEME["font_size_code"]
    return (f"QTextEdit {{ background:{THEME['bg_code']}; "
            f"  color:{THEME['text_primary']}; border:none; "
            f"  font-family:{THEME['font_code']}; "
            f"  font-size:{size}pt; "
            f"  border-radius:{THEME['radius_md']}; padding:12px; }}")


class CodeView(QTextEdit):
    """Read-only script panel that zooms with Ctrl+wheel and Ctrl +/-/0.

    Every panel shares one text size, so zooming the NPC script also zooms the
    dialog script - you set the size you can read once. The size lives in the
    stylesheet (which beats setFont), so QTextEdit's own zoomIn has no effect
    and zooming re-applies the stylesheet instead.
    """
    MIN_SIZE, MAX_SIZE = 6, 36
    _size = THEME["font_size_code"]
    _views = weakref.WeakSet()

    def __init__(self, font=None):
        super().__init__()
        self.setReadOnly(True)
        # Code wrapped mid-statement is unreadable; scroll sideways instead.
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        if font is not None:
            self.setFont(font)
        CodeView._views.add(self)
        self.setStyleSheet(code_view_css(CodeView._size))

    @classmethod
    def set_size(cls, size):
        size = max(cls.MIN_SIZE, min(cls.MAX_SIZE, size))
        if size == cls._size:
            return
        cls._size = size
        for view in list(cls._views):
            view.setStyleSheet(code_view_css(size))

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            step = event.angleDelta().y()
            if step:
                CodeView.set_size(CodeView._size + (1 if step > 0 else -1))
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            key = event.key()
            # Ctrl+= is Ctrl++ without Shift on most layouts
            if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                CodeView.set_size(CodeView._size + 1)
                return
            if key == Qt.Key.Key_Minus:
                CodeView.set_size(CodeView._size - 1)
                return
            if key == Qt.Key.Key_0:
                CodeView.set_size(THEME["font_size_code"])
                return
        super().keyPressEvent(event)


def code_view(font=None):
    """A read-only script panel; see CodeView."""
    return CodeView(font)


# --- pick the control that matches the data ----------------------------------
# A slider says "somewhere in this range, roughly". Use it only for values that
# really are continuous and judged by eye - a fatness dial. Anything you would
# type a number for gets a number field; anything with a handful of named
# states gets a choice list.

def number(lo, hi, value, on_change, suffix="", width=NUMBER_W, steppers=False):
    """A precise integer you type. Not a slider.

    No stepper arrows by default: nudging one at a time is useless for a value
    like 4000 hitpoints, and the arrows only crowd the field. Pass
    steppers=True where clicking up and down genuinely helps.
    """
    w = QSpinBox()
    w.setRange(lo, hi)
    w.setValue(int(value))
    w.setSuffix(suffix)
    w.setFixedWidth(width)
    w.setMinimumHeight(BUTTON_H)
    w.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    w.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows if steppers
                       else QSpinBox.ButtonSymbols.NoButtons)
    if not steppers:
        # Any stylesheet on a QSpinBox without buttons collapses its text area
        # to one pixel unless the hidden buttons are pinned to zero width.
        w.setStyleSheet(
            _input_css("QSpinBox")
            + "QSpinBox::up-button, QSpinBox::down-button "
              "{ subcontrol-origin:border; width:0; }")
        w.valueChanged.connect(on_change)
        return w
    w.setStyleSheet(
        _input_css("QSpinBox")
        + f"QSpinBox::up-button, QSpinBox::down-button {{ width:20px; "
        f"  background:{THEME['bg_panel']}; "
        f"  border-left:{THEME['border_width']} solid {THEME['bg_input_border']}; }}"
        f"QSpinBox::up-button:hover, QSpinBox::down-button:hover {{ "
        f"  background:{THEME['accent_primary']}; }}"
        f"QSpinBox::up-arrow {{ width:0; height:0; "
        f"  border-left:4px solid transparent; border-right:4px solid transparent; "
        f"  border-bottom:5px solid {THEME['text_secondary']}; }}"
        f"QSpinBox::down-arrow {{ width:0; height:0; "
        f"  border-left:4px solid transparent; border-right:4px solid transparent; "
        f"  border-top:5px solid {THEME['text_secondary']}; }}")
    w.valueChanged.connect(on_change)
    return w


def choice(options, value, on_change, width=220):
    """A short list of named states, e.g. chapters or magic circles.

    `options` is [(label, value), ...]. The caller never has to parse the
    label back out - the callback gets the value.
    """
    labels_ = [text for text, _ in options]
    values = [v for _, v in options]
    w = dropdown(labels_)
    if width:
        w.setFixedWidth(width)
    if value in values:
        w.setCurrentIndex(values.index(value))
    w.currentIndexChanged.connect(
        lambda i: on_change(values[i]) if 0 <= i < len(values) else None)
    return w


def toggle_row(text, options, value, on_change):
    """Two or three exclusive states, shown at once. Beats a two-item dropdown,
    which hides half the choice behind a click."""
    return radio_row(text, options, value, on_change)
