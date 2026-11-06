"""
theme.py — All visual design lives here: colors, fonts, sizes, and the derived
Qt stylesheets built from them. Nothing else in the app should contain a
hard-coded color, font name, or size.
"""

import re
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat

import config

# ── Colour palettes ───────────────────────────────────────────────────────────
# Same keys in both; THEME below picks one. Both are deliberately low-contrast:
# surfaces step by a few percent, rules are soft greys rather than black, and
# text is a dark/light grey rather than pure black/white, so a long session of
# form-filling is easy on the eyes. Contrast is spent on the one accent.
#
#   bg_border          hairlines between areas (dividers, tab edges)
#   bg_border_strong   things you grab or must find: scroll handles, check boxes
#   accent_soft        a quiet accent tint for "you are here" (selected side tab)
#   text_on_accent     text that sits on a solid accent fill

LIGHT = {                       # stone: cool grey-green paper, rust accent
    "bg_main":          "#f4f5f2",
    "bg_panel":         "#eceee9",
    "bg_bar":           "#eceee9",
    "bg_border":        "#d5d8d1",
    "bg_border_strong": "#a7aca3",
    "bg_input":         "#fbfbf9",
    "bg_input_border":  "#c6cac2",
    "bg_hover":         "#e2e5df",
    "bg_choice":        "#2b2b27",
    "bg_choice_input":  "#34342f",
    "bg_code":          "#eceee9",
    "text_primary":     "#2c302c",
    "text_secondary":   "#464b45",
    "text_muted":       "#767c74",
    "text_on_accent":   "#ffffff",

    "accent_primary":   "#bd5532",
    "accent_hover":     "#a5472a",
    "accent_soft":      "#f0ddd4",
    "accent_secondary": "#4f7062",
    "accent_gold":      "#a77a2e",

    # Dialogue
    "bubble_npc_bg":    "#e5e8e2",
    "bubble_npc_text":  "#2c302c",
    "bubble_hero_bg":   "#f3e1d8",
    "bubble_hero_text": "#2c302c",

    "syn_keyword":      "#ad4a2b",
    "syn_type":         "#5d5a92",
    "syn_function":     "#3b6c5a",
    "syn_string":       "#8f6d2e",
    "syn_comment":      "#959a92",
    "syn_number":       "#47698d",
}

DARK = {                        # slate: blue-grey charcoal, not black
    "bg_main":          "#25282b",
    "bg_panel":         "#2c3033",
    "bg_bar":           "#2c3033",
    "bg_border":        "#3b4044",
    "bg_border_strong": "#5b6166",
    "bg_input":         "#212427",
    "bg_input_border":  "#464c51",
    "bg_hover":         "#343a3e",
    "bg_choice":        "#2b2b27",
    "bg_choice_input":  "#34342f",
    "bg_code":          "#292d30",
    "text_primary":     "#cfd1cb",
    "text_secondary":   "#b5b8b2",
    "text_muted":       "#8d918b",
    "text_on_accent":   "#ffffff",

    "accent_primary":   "#c7653f",
    "accent_hover":     "#b25735",
    "accent_soft":      "#46352e",
    "accent_secondary": "#5f8777",
    "accent_gold":      "#a9853f",

    # Dialogue
    "bubble_npc_bg":    "#33383b",
    "bubble_npc_text":  "#cfd1cb",
    "bubble_hero_bg":   "#47342c",
    "bubble_hero_text": "#e8dcd5",

    "syn_keyword":      "#de8a67",
    "syn_type":         "#a8a3d8",
    "syn_function":     "#7fb69e",
    "syn_string":       "#cdab69",
    "syn_comment":      "#737975",
    "syn_number":       "#86a8cc",
}

PALETTES = {"light": LIGHT, "dark": DARK}

MODE = config.get("theme", "light")
if MODE not in PALETTES:
    MODE = "light"

# Every widget bakes its stylesheet from THEME when it is built. Switching the
# palette updates THEME and the shared sheet dicts in place, tells listeners
# (ui.py rebuilds its SS), and the window is then rebuilt - see studio.py.
_listeners = []


def on_change(fn):
    """Call fn() whenever THEME changes (palette switch or font resolution)."""
    _listeners.append(fn)


def _changed():
    SS.clear()
    SS.update(_build_ss())
    for fn in _listeners:
        fn()


def set_mode(mode):
    """Remember the palette for next launch. Returns True if it was saved."""
    return mode in PALETTES and config.save("theme", mode)


def apply(mode):
    """Switch THEME to another palette now. Widgets built after this use it."""
    global MODE
    if mode not in PALETTES:
        return
    MODE = mode
    THEME.update(PALETTES[mode])
    _changed()


# The font keys list preferences, Windows fonts first. Handing Qt a family
# that is not installed makes it build an alias table on every start (the
# "Populating font family aliases" warning), so once a QApplication exists
# each list is narrowed to the first family this machine really has.
_FONT_LISTS = {
    "font_ui":      ("Segoe UI", "Helvetica Neue", "Inter", "Noto Sans",
                     "DejaVu Sans", "Arial"),
    "font_code":    ("Consolas", "Cascadia Code", "Cascadia Mono", "Menlo",
                     "SF Mono", "DejaVu Sans Mono", "Liberation Mono",
                     "Noto Sans Mono", "Courier New"),
}
_fonts_resolved = False


def resolve_fonts():
    """Pick installed font families. Needs a QApplication; safe to call twice."""
    global _fonts_resolved
    if _fonts_resolved:
        return
    _fonts_resolved = True
    from PyQt6.QtGui import QFontDatabase
    have = set(QFontDatabase.families())
    fallback = {
        "font_ui": QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont),
        "font_code": QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont),
    }
    for key, wanted in _FONT_LISTS.items():
        THEME[key] = next((f for f in wanted if f in have), fallback[key].family())
    THEME["font_display"] = THEME["font_code"]
    _changed()


THEME = {
    **PALETTES[MODE],

    # Narrowed to one installed family each by resolve_fonts().
    "font_display":     "Consolas",
    "font_ui":          "Segoe UI",
    "font_code":        "Consolas",
    "font_size_ui":     "21px",
    "font_size_small":  "18px",
    "font_size_tiny":   "15px",
    "font_size_button": "16px",
    "font_size_chat":   "16px",   # bubble text and the line input
    "font_size_scene":  "14px",   # scene list rows and the NPC tab list: one size for both
    "font_size_title":  "22px",
    "font_size_placeholder": "21px",
    "font_size_code":   9,           # pt, used for QFont object

    # ── Geometry ──────────────────────────────────────────────────────────────
    "radius_sm":        "4px",
    "radius_md":        "6px",
    "radius_lg":        "8px",
    "border_width":     "1px",
    "topbar_height":    56,
    "sidebar_width":    212,
    "splitter_sizes":   [212, 620, 500],
    "window_size":      (1040, 660),

    # ── Spacing ───────────────────────────────────────────────────────────────
    "label_col_width":  "44px",
}


# ── Derived stylesheet fragments (built once from THEME, used everywhere) ─────

def _ss_field():
    t = THEME
    return (
        f"QLineEdit {{ background:{t['bg_input']}; color:{t['text_primary']}; "
        f"  border:{t['border_width']} solid {t['bg_input_border']}; "
        f"  border-radius:{t['radius_sm']}; padding:5px 8px; "
        f"  selection-background-color:{t['accent_primary']}; "
        f"  font-family:{t['font_ui']}; }}"
        f"QLineEdit:focus {{ border:{t['border_width']} solid {t['accent_primary']}; }}"
        f"QLineEdit::placeholder {{ color:{t['text_muted']}; }}"
        
    )

def _ss_field_readonly():
    t = THEME
    return (
        f"QLineEdit {{ background:{t['bg_panel']}; color:{t['text_muted']}; "
        f"  border:{t['border_width']} solid {t['bg_input_border']}; "
        f"  border-radius:{t['radius_sm']}; padding:5px 8px; "
        f"  font-family:{t['font_ui']}; font-style:italic; }}"
    )

def _ss_spin():
    t = THEME
    return (
        f"QSpinBox {{ background:{t['bg_input']}; color:{t['text_primary']}; "
        f"  border:{t['border_width']} solid {t['bg_input_border']}; "
        f"  border-radius:{t['radius_sm']}; padding:2px 4px; }}"
        f"QSpinBox:focus {{ border:{t['border_width']} solid {t['accent_primary']}; }}"
    )

def _ss_combo():
    t = THEME
    return (
        f"QComboBox {{ background:{t['bg_input']}; color:{t['text_primary']}; "
        f"  border:{t['border_width']} solid {t['bg_input_border']}; "
        f"  border-radius:{t['radius_sm']}; padding:3px 6px; }}"
        f"QComboBox::drop-down {{ border:none; }}"
        f"QComboBox QAbstractItemView {{ background:{t['bg_panel']}; color:{t['text_primary']}; "
        f"  selection-background-color:{t['accent_primary']}; "
        f"  selection-color:{t['text_on_accent']}; }}"
    )

def _ss_check():
    t = THEME
    return (
        f"QCheckBox {{ color:{t['text_secondary']}; spacing:6px; }}"
        f"QCheckBox::indicator {{ width:13px; height:13px; "
        f"  border:{t['border_width']} solid {t['bg_border']}; "
        f"  border-radius:3px; background:{t['bg_input']}; }}"
        f"QCheckBox::indicator:checked {{ background:{t['accent_primary']}; "
        f"  border-color:{t['accent_primary']}; }}"
    )

def _ss_group():
    t = THEME
    return (
        f"QGroupBox {{ color:{t['accent_secondary']}; font-weight:400; font-size:{t['font_size_small']}; "
        f"  letter-spacing:0.3px; border:{t['border_width']} solid {t['bg_border']}; "
        f"  border-radius:{t['radius_lg']}; margin-top:10px; padding-top:6px; "
        f"  background:{t['bg_panel']}; font-family:{t['font_ui']}; }}"
        f"QGroupBox::title {{ subcontrol-origin:margin; left:10px; "
        f"  background:{t['bg_panel']}; padding:0 4px; }}"
    )

def _ss_add_btn():
    t = THEME
    return (
        f"QPushButton {{ background:{t['bg_bar']}; color:{t['text_secondary']}; "
        f"  border:{t['border_width']} solid {t['bg_border']}; "
        f"  border-radius:{t['radius_sm']}; padding:5px 12px; "
        f"  font-size:{t['font_size_small']}; font-weight:400; }}"
        f"QPushButton:hover {{ background:{t['bg_input_border']}; color:{t['text_primary']}; }}"
    )

def _ss_rm_btn():
    t = THEME
    return (
        f"QPushButton {{ background:transparent; color:{t['text_muted']}; border:none; }}"
        f"QPushButton:hover {{ color:{t['accent_hover']}; }}"
    )

def _ss_global():
    t = THEME
    return f"""
        QMainWindow, QWidget {{
            background: {t['bg_main']};
            color: {t['text_primary']};
            font-family: {t['font_ui']};
            font-size: {t['font_size_ui']};
        }}
        QLabel {{ color: {t['text_secondary']}; }}
        QScrollBar:vertical {{
            background: {t['bg_panel']}; width: 8px; border-radius: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t['bg_border_strong']}; border-radius: 4px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{
            background: {t['bg_panel']}; height: 8px; border-radius: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {t['bg_border_strong']}; border-radius: 4px; min-width: 24px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        QSplitter::handle {{ background: {t['bg_main']}; width: 10px; }}
        QTabWidget::pane {{
            border: none;
            border-top: {t['border_width']} solid {t['bg_border']};
            background: {t['bg_main']};
            top: -1px;
        }}
        QTabBar {{ background: {t['bg_main']}; }}
        QTabBar::tab {{
            background: {t['bg_hover']};
            color: {t['text_muted']};
            padding: 8px 18px 8px 18px;
            border: none;
            border-bottom: 1px solid {t['bg_border']};
            border-right: {t['border_width']} solid {t['bg_border']};
            font-family: {t['font_ui']};
            font-size: {t['font_size_small']};
            font-weight: 400;
        }}
        QTabBar::tab:hover {{ color: {t['text_primary']}; }}
        QTabBar::tab:selected {{
            background: {t['bg_panel']};
            color: {t['text_primary']};
            border-bottom: 1px solid {t['bg_panel']};
            font-weight: 400;
        }}
        QMessageBox {{ background: {t['bg_main']}; }}
    """

def _build_ss():
    return {
        "field":          _ss_field(),
        "field_readonly": _ss_field_readonly(),
        "spin":           _ss_spin(),
        "combo":          _ss_combo(),
        "check":          _ss_check(),
        "group":          _ss_group(),
        "add_btn":        _ss_add_btn(),
        "rm_btn":         _ss_rm_btn(),
        "global":         _ss_global(),
    }


# Built at import, rebuilt in place by _changed(), so `from theme import SS`
# keeps seeing the current sheets.
SS = _build_ss()


# ── Syntax Highlighter ────────────────────────────────────────────────────────
class DaedalusHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        t = THEME
        self.rules = []

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:   f.setFontWeight(QFont.Weight.Bold)
            if italic: f.setFontItalic(True)
            return f

        kw = fmt(t["syn_keyword"])
        for w in ["instance", "func", "void", "int", "var", "return", "if", "else",
                  "INSTANCE", "FUNC", "VOID", "INT", "VAR"]:
            self.rules.append((re.compile(r'\b' + w + r'\b'), kw))

        tp = fmt(t["syn_type"])
        for w in ["C_INFO", "TRUE", "FALSE", "LOG_MISSION", "LOG_NOTE",
                  "LOG_RUNNING", "LOG_SUCCESS", "DIALOG_ENDE"]:
            self.rules.append((re.compile(r'\b' + w + r'\b'), tp))

        fn = fmt(t["syn_function"])
        for w in ["AI_Output", "AI_StopProcessInfos", "B_GiveXP", "B_GiveInvItems",
                  "CreateInvItems", "CreateInvItem", "Npc_RemoveInvItems",
                  "Log_CreateTopic", "Log_SetTopicStatus", "B_LogEntry",
                  "Info_ClearChoices", "Info_AddChoice", "Npc_KnowsInfo",
                  "Npc_GetTrueGuild", "Npc_IsInState"]:
            self.rules.append((re.compile(r'\b' + w + r'\b'), fn))

        self.rules.append((re.compile(r'"[^"]*"'),  fmt(t["syn_string"])))
        self.rules.append((re.compile(r'//[^\n]*'),  fmt(t["syn_comment"], italic=True)))
        self.rules.append((re.compile(r'\b\d+\b'),   fmt(t["syn_number"])))

    def highlightBlock(self, text):
        for pat, fmt in self.rules:
            for m in pat.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


def mono_font():
    f = QFont(THEME["font_code"].split(",")[0].strip(), THEME["font_size_code"])
    f.setStyleHint(QFont.StyleHint.Monospace)
    return f

