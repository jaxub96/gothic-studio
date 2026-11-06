"""
studio.py - Gothic Studio. NPC creator and dialog editor in one window.

    python studio.py

Two tabs, one theme, one link between them: when the NPC tab computes an
instance name, the Dialog tab picks it up as its NPC ID, so you never type
the same identifier twice.
"""

import os
import sys
from pathlib import Path

if "--dev" in sys.argv:       # must be set before project is imported
    os.environ.setdefault("GOTHIC_STUDIO_DEV", "1")

from PyQt6.QtCore import QProcess, QSize, Qt
from PyQt6.QtGui import QColor, QIcon, QKeySequence, QPalette, QShortcut
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMenu, QMessageBox, QStatusBar, QToolButton,
                             QTabWidget)

import config
import firstrun
import project
import theme
import ui
from theme import SS, THEME
from version import VERSION

#: What "100%" means: the app is drawn at 85% of Qt's natural size, because that is
#: the size it was designed to read well at. The Scale menu is relative to this.
BASE_SCALE = 0.85
#: Scales offered in the status bar menu, as percentages of the 100% above
SCALES = (70, 75, 80, 85, 90, 100, 110, 125)
DEFAULT_SCALE = 100


def ui_scale():
    """The factor Qt is really using this run (QT_SCALE_FACTOR, read once at
    start-up, so a change in the menu takes a restart)."""
    try:
        return max(0.4, float(os.environ.get("QT_SCALE_FACTOR") or 1))
    except ValueError:
        return 1.0


def scale_percent():
    """The number the menu shows: the current scale relative to BASE_SCALE."""
    return round(ui_scale() / BASE_SCALE * 100)


# dialog_page and npc_page are imported by _load_pages() instead of here. They
# pull in gamedata and textures, which read project.SCRIPTS at import time, and
# on a fresh machine that folder is not known until firstrun has asked for it.
dialog_page = npc_page = None

# PyInstaller unpacks bundled data under sys._MEIPASS; from source it sits here.
ICON = (Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        / "assets" / "icon.png")


def _load_pages():
    global dialog_page, npc_page
    import dialog_page
    import npc_page


class Studio(QMainWindow):
    def __init__(self, npc=None):
        super().__init__()
        theme.resolve_fonts()             # no-op after the first call
        self.setWindowTitle(f"Gothic Studio {VERSION}")
        self.setMinimumSize(int(980 / ui_scale()), int(520 / ui_scale()))
        self._size_and_centre()
        self.setStyleSheet(SS["global"])

        self.npc = npc_page.build(npc)
        self.dialog = dialog_page.build()

        self.tabs = tabs = QTabWidget()
        tabs.addTab(self.npc, "NPC")
        tabs.addTab(self.dialog, "Dialog")
        self.setCentralWidget(tabs)
        self._side_toggle(tabs)
        # Picks up NPC files that changed outside the app, so no Reload button.
        tabs.currentChanged.connect(
            lambda i: self.dialog.refresh_npc_ids() if i == 1 else None)
        # The NPC page's side list sits right under the NPC / Dialog tabs; size
        # it to the tab bar so its right rule continues the Dialog tab's edge.
        # Tab widths come from font metrics, so a constant would drift.
        tabs.tabBar().ensurePolished()
        self.npc.tabs.set_list_width(tabs.tabBar().sizeHint().width())
        self.dialog.set_scene_width(tabs.tabBar().sizeHint().width())

        # The one connection that makes this a single app rather than two.
        self.npc.instance_changed.connect(self.dialog.set_npc_id)
        self.npc.name_changed.connect(self.dialog.set_npc_name)
        self.npc.saved.connect(self.dialog.on_npc_saved)
        self.npc.saved.connect(lambda p: self.statusBar().showMessage(f'Saved {p}', 6000))

        self._status_bar()

    def closeEvent(self, event):
        # Unsaved dialog scenes exist only in this window; ask before they go.
        if getattr(self, "_swapping", False) or self.dialog.confirm_close():
            event.accept()
        else:
            event.ignore()

    def _side_toggle(self, tabs):
        """A button at the right end of the tab row that hides the script panel on
        both tabs, giving the editor the whole width. Remembered between runs."""
        self.side_btn = QToolButton()
        self.side_btn.setCheckable(True)
        self.side_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.side_btn.setIconSize(QSize(18, 18))
        self.side_btn.setAutoRaise(True)
        self.side_btn.setStyleSheet(
            f"QToolButton {{ border:none; border-radius:{THEME['radius_sm']}; "
            f"  padding:4px 8px; margin:3px 8px; }}"
            f"QToolButton:hover {{ background:{THEME['bg_hover']}; }}")
        self.side_btn.toggled.connect(self._show_side_panels)
        tabs.setCornerWidget(self.side_btn, Qt.Corner.TopRightCorner)
        self.side_btn.setChecked(bool(config.get("side_panel", True)))
        self._show_side_panels(self.side_btn.isChecked())   # also when unchanged
        QShortcut(QKeySequence("Ctrl+\\"), self,
                  lambda: self.side_btn.setChecked(not self.side_btn.isChecked()))

    def _show_side_panels(self, shown):
        for page in (self.npc, self.dialog):
            page.side.setVisible(shown)
        self.side_btn.setIcon(ui.side_panel_icon(shown))
        self.side_btn.setToolTip(
            "Hide the script panel  (Ctrl+\\)" if shown else "Show the script panel  (Ctrl+\\)")
        config.save("side_panel", bool(shown))

    def _size_and_centre(self):
        """Open at a modest size (never more than 75% of the screen), centred."""
        # The size is for a 100% UI. At a smaller scale the same screen area holds
        # more, so the window opens that much bigger in its own units.
        scale = ui_scale()
        want_w, want_h = (int(v / scale) for v in THEME["window_size"])
        area = self.screen().availableGeometry()
        self.resize(min(want_w, int(area.width() * 0.75)),
                    min(want_h, int(area.height() * 0.75)))
        frame = self.frameGeometry()
        frame.moveCenter(area.center())
        self.move(frame.topLeft())

    def _status_bar(self):
        bar = QStatusBar()
        bar.setStyleSheet(
            f"QStatusBar {{ background:{THEME['bg_bar']}; color:{THEME['text_muted']}; "
            f"font-size:{THEME['font_size_small']}; }}")

        self.compile_btn = ui.button(
            "Compile check", self._compile_check, ui.DEFAULT,
            "Build the whole mod with gdc and list any errors", compact=True)

        self.path_label = ui.hint(
            f"  mod: {project.CONTENT}    encoding: {project.ENCODING}")
        self.folder_btn = ui.button(
            "Change mod folder", self._change_folder, ui.DEFAULT,
            "Point Gothic Studio at a different Gothic II install", compact=True)

        # Only worth showing when there is nothing to compile with. Found gdc
        # is the normal case and needs no button.
        self.gdc_btn = ui.button(
            "Locate gdc", self._locate_gdc, ui.DEFAULT,
            f"Point at a {project.GDC_NAME} binary", compact=True)
        self.gdc_btn.setVisible(not project.find_gdc().is_file())

        self.theme_btn = ui.button(
            self._theme_label(), self._toggle_theme, ui.DEFAULT,
            "Switch between the light and dark look (applies on restart)",
            compact=True)

        self.scale_btn = ui.button(
            f"Scale {scale_percent()}%", None, ui.DEFAULT,
            "Make everything smaller or larger (takes a restart)", compact=True)
        menu = QMenu(self.scale_btn)
        current = scale_percent()
        for pct in SCALES:
            act = menu.addAction(f"{pct}%")
            act.setCheckable(True)
            act.setChecked(pct == current)
            act.triggered.connect(lambda _=False, v=pct: self._set_scale(v))
        self.scale_btn.setMenu(menu)

        bar.addWidget(self.path_label, 1)
        bar.addPermanentWidget(self.gdc_btn)
        bar.addPermanentWidget(self.scale_btn)
        bar.addPermanentWidget(self.theme_btn)
        bar.addPermanentWidget(self.folder_btn)
        bar.addPermanentWidget(self.compile_btn)
        self.setStatusBar(bar)

    def _set_scale(self, pct):
        """Remember the scale, then offer to restart: Qt applies it only at start-up."""
        if pct == scale_percent():
            return
        config.save("ui_scale", pct)
        answer = QMessageBox.question(
            self, "Scale", f"Scale set to {pct}%. Restart Gothic Studio now to apply it?\n"
            "Your open work is kept if you save it first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes)
        if answer == QMessageBox.StandardButton.Yes:
            self._restart()
        else:
            self.statusBar().showMessage(f"Scale {pct}% - applies the next time you start", 8000)

    def _restart(self):
        if not self.dialog.confirm_close():
            return
        frozen = getattr(sys, "frozen", False)
        args = sys.argv[1:] if frozen else sys.argv
        self._swapping = True                 # already asked about unsaved work
        QProcess.startDetached(sys.executable, args)
        QApplication.quit()

    @staticmethod
    def _theme_label():
        """Names the look you would switch *to*, like a light switch."""
        return "Light mode" if theme.MODE == "dark" else "Dark mode"

    def _toggle_theme(self):
        """Switch palettes now.

        Every widget bakes its colours into a stylesheet when it is built, so
        the window is rebuilt with the new palette and the work in progress -
        the NPC, the dialog scenes, which tabs are open - is carried across.
        """
        mode = "light" if theme.MODE == "dark" else "dark"
        saved = theme.set_mode(mode)
        theme.apply(mode)
        apply_palette(QApplication.instance())

        state = self._snapshot()
        new = Studio(npc=self.npc.npc)
        new._restore(state)
        new.setGeometry(self.geometry())
        new.setWindowState(self.windowState())
        new.show()
        _windows.append(new)
        self._swapping = True                 # its work lives on in `new`: no unsaved prompt
        self.close()
        if self in _windows:
            _windows.remove(self)
        self.deleteLater()
        new.statusBar().showMessage(
            f"{mode.capitalize()} mode" if saved
            else f"{mode.capitalize()} mode (could not save the setting)", 5000)

    def _snapshot(self):
        d = self.dialog
        return {
            "main_tab": self.tabs.currentIndex(),
            "npc_tab": self.npc.tabs.currentIndex(),
            "npc_side": self.npc.side.current_tab(),
            "dlg_side": d.side.current_tab(),
            "blocks": d._collect_blocks(),
            "npc_name": d._npc_name(),
            "npc_id": d._npc_id(),
            "block": d.current_block_idx,
            "file": d.current_file_path,
            "saved_text": d._saved_text,
            "touched": (d._npc_id_touched, d._npc_name_touched),
            "status": d.side.status.text(),
            "npc_status": self.npc.side.status.text(),
        }

    def _restore(self, s):
        d = self.dialog
        if s["blocks"] or s["npc_name"] or s["npc_id"]:
            d._load_project(s["npc_name"], s["npc_id"], s["blocks"])
            if 0 <= s["block"] < len(d.blocks):
                d._select_block(s["block"])
        d.current_file_path = s["file"]
        d._saved_text = s["saved_text"]       # what was saved stays saved, what was not stays not
        d._npc_id_touched, d._npc_name_touched = s["touched"]
        d.side.say(s["status"])
        d.side.tabs.setCurrentIndex(s["dlg_side"])
        self.npc.tabs.setCurrentIndex(max(s["npc_tab"], 0))
        self.npc.side.tabs.setCurrentIndex(s["npc_side"])
        self.npc.side.say(s["npc_status"])
        self.tabs.setCurrentIndex(s["main_tab"])

    def _locate_gdc(self):
        if firstrun.choose_gdc(self):
            self.gdc_btn.setVisible(False)
            self.statusBar().showMessage(f"Using {project.find_gdc()}", 8000)

    def _change_folder(self):
        if firstrun.change(self):
            self.statusBar().showMessage(
                "Mod folder saved - restart Gothic Studio to load it", 10000)

    def _compile_check(self):
        """Run gdc over the whole mod, exactly like the VS Code 'compile check' task."""
        self.compile_btn.setEnabled(False)
        self.compile_btn.setText("Compiling...")
        QApplication.processEvents()
        try:
            ok, errors = project.compile_check()
        finally:
            self.compile_btn.setEnabled(True)
            self.compile_btn.setText("Compile check")

        # Missing gdc is a setup problem, not a script problem - offer the fix
        # instead of just reporting it.
        if not ok and not project.find_gdc().is_file():
            box = QMessageBox(self)
            box.setWindowTitle("Compile check")
            box.setText("\n".join(errors))
            box.setStandardButtons(QMessageBox.StandardButton.Open
                                   | QMessageBox.StandardButton.Cancel)
            box.button(QMessageBox.StandardButton.Open).setText("Locate gdc...")
            if box.exec() == QMessageBox.StandardButton.Open:
                self._locate_gdc()
            return

        if ok:
            # Success is the common case - say so in the status bar rather than
            # making you dismiss a box before you can carry on.
            self.statusBar().showMessage("Compile check: OK", 6000)
        else:
            shown = "\n".join(errors[:25])
            more = f"\n\n...and {len(errors) - 25} more" if len(errors) > 25 else ""
            QMessageBox.critical(self, "Compile check", shown + more)


def diagnose():
    """`GothicStudio.exe --check > out.txt` - where am I, and can I see the mod?

    The exe is built --windowed so there is no console; redirect to a file.
    """
    import config
    import gamedata
    print(f"frozen      : {getattr(sys, 'frozen', False)}")
    print(f"platform    : {sys.platform}")
    print(f"running from: {Path(sys.executable if getattr(sys, 'frozen', False) else __file__).parent}")
    print(f"scripts root: {project.SCRIPTS}")
    print(f"mod found   : {project.FOUND}")
    print(f"encoding    : {project.ENCODING}")
    print(f"gdc present : {project.GDC.is_file()}  ({project.GDC_NAME})")
    print(f"config file : {config.CONFIG_FILE}"
          f"{'' if config.CONFIG_FILE.is_file() else '  (none yet)'}")
    print(f"saved root  : {config.get('scripts_root') or '-'}")
    if not project.FOUND:
        print("\nNo Content/Gothic.src here or above, and no folder saved. "
              "Start the app and pick your Gothic II Scripts folder, put the "
              "app inside a mod's Scripts folder, or set GOTHIC_SCRIPTS.")
        return 1
    for fn in (gamedata.items, gamedata.armors, gamedata.guilds, gamedata.tactics,
               gamedata.routines, gamedata.heads, gamedata.overlays,
               gamedata.npc_instances, gamedata.waypoints):
        print(f"  {fn.__name__:16} {len(fn())}")

    import textures
    print(f"\ntextures    : {textures.TEXTURE_DIR}")
    print(f"  indexed        {len(textures._index())}")
    faces = gamedata.face_values()
    face_hits = sum(1 for v in faces.values() if textures.face_texture(v))
    print(f"  face previews  {face_hits}/{len(faces)}")
    armor_hits, armor_total = textures.coverage()
    print(f"  armor previews {armor_hits}/{armor_total}")
    if not face_hits:
        print("  (no previews: Textures\\_compiled not found next to Scripts\\)")

    import fastpath
    import mesh
    import render3d
    print(f"\nnumpy       : "
          f"{'yes - accelerated' if fastpath.HAVE_NUMPY else 'no - pure python'}")
    if fastpath.HAVE_NUMPY:
        print(f"  raster switches to numpy above "
              f"{render3d.RASTER_NUMPY_MIN_PIXELS:,} px")

    print(f"\nmeshes      : {len(textures._mesh_index())} indexed")
    print(f"  skeleton       {len(mesh.skeleton())} bones")
    heads = gamedata.heads()
    print(f"  head meshes    {sum(1 for h in heads if mesh.head_mesh(h))}/{len(heads)}")
    worn = sum(1 for a in gamedata.armors()
               if (m := mesh.body_mesh(a)) and m.name != "HUM_BODY_NAKED0.MDM")
    print(f"  armor meshes   {worn}/{len(gamedata.armors())}")
    return 0


DEV = "--dev" in sys.argv   # skip the Gothic II prompt; run without a mod

#: Keeps the live window referenced; a theme switch replaces it.
_windows = []


def apply_palette(app):
    """Point Qt's own palette (dialogs, menus, frame) at the current THEME."""
    # Let the native window frame (title bar) match, where Qt can (6.8+).
    hints = app.styleHints()
    if hasattr(hints, "setColorScheme"):
        hints.setColorScheme(Qt.ColorScheme.Dark if theme.MODE == "dark"
                             else Qt.ColorScheme.Light)

    pal = QPalette()
    for role, key in (("Window", "bg_main"), ("WindowText", "text_primary"),
                      ("Base", "bg_input"), ("AlternateBase", "bg_panel"),
                      ("Text", "text_primary"), ("Button", "bg_bar"),
                      ("ButtonText", "text_secondary"),
                      ("Highlight", "accent_primary"),
                      ("HighlightedText", "text_on_accent"),
                      ("ToolTipBase", "bg_panel"), ("ToolTipText", "text_primary"),
                      ("PlaceholderText", "text_muted")):
        pal.setColor(getattr(QPalette.ColorRole, role), QColor(THEME[key]))
    app.setPalette(pal)


def main():
    if "--check" in sys.argv:
        return diagnose()

    # PyQt aborts the whole process when an exception escapes a Qt event handler
    # (that is how a stray error in a wheel event once killed the app and any
    # unsaved work). Report it on stderr and carry on instead.
    def _report(kind, value, tb):
        import traceback
        sys.stderr.write("".join(traceback.format_exception(kind, value, tb)))
    sys.excepthook = _report

    # Scale the whole UI (text, buttons, spacing alike): 100% in the menu is BASE_SCALE
    # of Qt's natural size. Qt reads this once, before the application object exists.
    # An explicit QT_SCALE_FACTOR still wins.
    if "QT_SCALE_FACTOR" not in os.environ:
        try:
            pct = float(config.get("ui_scale", DEFAULT_SCALE))
        except (TypeError, ValueError):
            pct = DEFAULT_SCALE
        os.environ["QT_SCALE_FACTOR"] = f"{BASE_SCALE * max(40.0, min(200.0, pct)) / 100:.4f}"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # On macOS this would replace the Dock icon with the bare G; the bundle's
    # .icns already has the right one there.
    if sys.platform != "darwin":
        app.setWindowIcon(QIcon(str(ICON)))

    theme.resolve_fonts()
    apply_palette(app)

    if not DEV and not project.FOUND and not firstrun.ensure():
        return                                # asked, declined; nothing to show

    _load_pages()
    win = Studio()
    _windows.append(win)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    sys.exit(main() or 0)
