"""
theme.py — All visual design lives here: colors, fonts, sizes, and the derived
Qt stylesheets built from them. Nothing else in the app should contain a
hard-coded color, font name, or size.
"""

import re
from PyQt6.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat

THEME = {
"bg_main":          "#ffffff",
"bg_panel":         "#f4f4f2",
"bg_bar":           "#f4f4f2",
"bg_border":        "#1a1a1a",
"bg_input":         "#ffffff",
"bg_input_border":  "#1a1a1a",
"bg_hover":         "#e7e7e2",
"bg_choice":        "#2b2b27",
"bg_choice_input":  "#34342f",
"bg_code":          "#f4f4f2",
"text_primary":     "#1a1a1a",
"text_secondary":   "#33332f",
"text_muted":        "#6b6b66",

"accent_primary":   "#e8431c",
"accent_hover":     "#c93512",
"accent_secondary": "#3f5f52",

# Dialogue
"bubble_npc_bg":    "#f4f4f2",
"bubble_npc_text":  "#1a1a1a",

"bubble_hero_bg":   "#ffe9e2",
"bubble_hero_text": "#1a1a1a",
    "syn_keyword":      "#c13f1d",
    "syn_type":         "#5a4fa0",
    "syn_function":     "#2f6f58",
    "syn_string":       "#a0701f",
    "syn_comment":      "#9a9a8e",
    "syn_number":       "#3b6aa0",
    "font_display":     "Consolas, Cascadia Code, monospace",   # new key
    "font_ui":          "Segoe UI, Helvetica Neue, Arial, sans-serif",   # unchanged — body stays legible
    "font_code":        "Consolas, Cascadia Code, monospace",
    "font_size_ui":     "21px",
    "font_size_small":  "18px",
    "font_size_tiny":   "15px",
    "font_size_title":  "22px",
    "font_size_placeholder": "21px",
    "font_size_code":   8,           # pt, used for QFont object

    # ── Geometry ──────────────────────────────────────────────────────────────
    "radius_sm":        "0px",
    "radius_md":        "0px",
    "radius_lg":        "0px",
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
        f"  border-radius:0; background:{t['bg_input']}; }}"
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
            background: {t['bg_panel']}; width: 8px; border-radius: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {t['bg_border']}; border-radius: 0;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
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
            font-weight: 600;
        }}
        QTabBar::tab:hover {{ color: {t['text_primary']}; }}
        QTabBar::tab:selected {{
            background: {t['bg_panel']};
            color: {t['text_primary']};
            border-bottom: 1px solid {t['bg_panel']};
            font-weight: 700;
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

THEME.setdefault("accent_gold", "#b9801f")
