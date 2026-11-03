"""
theme.py — All visual design lives here: colors, fonts, sizes, and the derived
Qt stylesheets built from them. Nothing else in the app should contain a
hard-coded color, font name, or size.
"""

import re
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat

THEME = {
"bg_main":          "#f1e9d8",   # aged parchment
"bg_panel":         "#e8ddc4",   # darker parchment
"bg_bar":           "#ddcfa8",   # worn leather
"bg_border":        "#b8a374",   # brass/leather line — was a flat gray, now has warmth
"bg_input":         "#f1e9d8",   # same as main bg, but with border
"bg_input_border":  "#b8a374",   # brass/leather line —
"bg_choice":        "#372E29",
"bg_choice_input":  "#302925",
"bg_code":          "#e8ddc4",   # same as panel bg, but with border
"text_primary":     "#2e2418",   # iron-gall ink
"text_secondary":   "#5a4a35",
"text_muted":        "#8c7a5c",

"accent_primary":   "#8a3a2a",   # oxblood wax-seal red — replaces the teal
"accent_hover":     "#6e2d20",
"accent_secondary": "#4d5c3f",   # moss/forest green — replaces the sage

# Dialogue
"bubble_npc_bg":    "#342F2B",
"bubble_npc_text":  "#D2C5B1",

"bubble_hero_bg":   "#47332C",
"bubble_hero_text": "#E2D2BF",

    # Syntax highlighting (code preview only)
    "syn_keyword":      "#8a7a68",
    "syn_type":         "#7a7a9a",
    "syn_function":     "#5f8a72",
    "syn_string":       "#a68a5a",
    "syn_comment":      "#b0a894",
    "syn_number":       "#6a86a0",

 # ── Typography ────────────────────────────────────────────────────────────
    "font_display":     "Cinzel, Trajan Pro, Georgia, serif",   # new key
    "font_ui":          "Segoe UI, Helvetica Neue, Arial, sans-serif",   # unchanged — body stays legible
    "font_code":        "Cascadia Code, Consolas, monospace",
    "font_size_ui":     "21px",
    "font_size_small":  "18px",
    "font_size_tiny":   "15px",
    "font_size_title":  "22px",
    "font_size_placeholder": "21px",
    "font_size_code":   13,          # pt, used for QFont object

    # ── Geometry ──────────────────────────────────────────────────────────────
    "radius_sm":        "1px",
    "radius_md":        "3px",
    "radius_lg":        "5px",
    "border_width":     "1px",
    "topbar_height":    56,
    "sidebar_width":    212,
    "splitter_sizes":   [212, 620, 500],
    "window_size":      (1460, 940),

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
        f"  selection-color:{t['bg_main']}; }}"
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
        f"QGroupBox {{ color:{t['accent_secondary']}; font-weight:600; font-size:{t['font_size_small']}; "
        f"  letter-spacing:0.3px; border:{t['border_width']} solid {t['bg_border']}; "
        f"  border-radius:{t['radius_lg']}; margin-top:10px; padding-top:6px; "
        f"  background:{t['bg_panel']}; font-family:{t['font_ui']}; }}"
        f"QGroupBox::title {{ subcontrol-origin:margin; left:10px; "
        f"  background:{t['bg_panel']}; padding:0 4px; }}"
        f"border: 2px double {THEME['bg_border']};"
        
    )

def _ss_add_btn():
    t = THEME
    return (
        f"QPushButton {{ background:{t['bg_bar']}; color:{t['text_secondary']}; "
        f"  border:{t['border_width']} solid {t['bg_border']}; "
        f"  border-radius:{t['radius_sm']}; padding:5px 12px; "
        f"  font-size:{t['font_size_small']}; font-weight:600; }}"
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
            background: {t['bg_panel']}; width: 8px; border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {t['bg_border']}; border-radius: 4px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QSplitter::handle {{ background: {t['bg_main']}; width: 10px; }}
        QTabWidget::pane {{
            border: none;
            border-top: {t['border_width']} solid {t['bg_border']};
            background: {t['bg_main']};
            top: -1px;
        }}
        QTabBar::tab {{
            background: transparent;
            color: {t['text_muted']};
            padding: 8px 16px;
            border: none;
            margin-right: 4px;
            font-family: {t['font_ui']};
            font-size: {t['font_size_small']};
            font-weight: 600;
        }}
        QTabBar::tab:hover {{ color: {t['text_secondary']}; }}
        QTabBar::tab:selected {{
            color: {t['accent_primary']};
            font-weight: 700;
            border-bottom: 2px solid {t['accent_primary']};
        }}
        QMessageBox {{ background: {t['bg_main']}; }}
    """

# Build all sheets once at import time
SS = {
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

        kw = fmt(t["syn_keyword"], bold=True)
        for w in ["instance", "func", "void", "int", "var", "return", "if", "else",
                  "INSTANCE", "FUNC", "VOID", "INT", "VAR"]:
            self.rules.append((re.compile(r'\b' + w + r'\b'), kw))

        tp = fmt(t["syn_type"], bold=True)
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

THEME.setdefault("accent_gold", "#a07820")
