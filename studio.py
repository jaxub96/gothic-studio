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

from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, QStatusBar,
                             QTabWidget)

import firstrun
import project
import ui
from theme import SS, THEME

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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gothic Studio")
        self._size_and_centre()
        self.setStyleSheet(SS["global"])

        self.npc = npc_page.build()
        self.dialog = dialog_page.build()

        tabs = QTabWidget()
        tabs.addTab(self.npc, "NPC")
        tabs.addTab(self.dialog, "Dialog")
        self.setCentralWidget(tabs)
        # The NPC page's side list sits right under the NPC / Dialog tabs; size
        # it to the tab bar so its right rule continues the Dialog tab's edge.
        # Tab widths come from font metrics, so a constant would drift.
        tabs.tabBar().ensurePolished()
        self.npc.tabs.set_list_width(tabs.tabBar().sizeHint().width())

        # The one connection that makes this a single app rather than two.
        self.npc.instance_changed.connect(self.dialog.set_npc_id)
        self.npc.name_changed.connect(self.dialog.set_npc_name)
        self.npc.saved.connect(self.dialog.on_npc_saved)
        self.npc.saved.connect(lambda p: self.statusBar().showMessage(f'Saved {p}', 6000))

        self._status_bar()

    def _size_and_centre(self):
        """Open at a modest size (never bigger than 90% of the screen), centred."""
        want_w, want_h = THEME["window_size"]
        area = self.screen().availableGeometry()
        self.resize(min(want_w, int(area.width() * 0.9)),
                    min(want_h, int(area.height() * 0.9)))
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

        bar.addWidget(self.path_label, 1)
        bar.addPermanentWidget(self.gdc_btn)
        bar.addPermanentWidget(self.folder_btn)
        bar.addPermanentWidget(self.compile_btn)
        self.setStatusBar(bar)

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


def main():
    if "--check" in sys.argv:
        return diagnose()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # On macOS this would replace the Dock icon with the bare G; the bundle's
    # .icns already has the right one there.
    if sys.platform != "darwin":
        app.setWindowIcon(QIcon(str(ICON)))

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(THEME["bg_main"]))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(THEME["text_primary"]))
    pal.setColor(QPalette.ColorRole.Base, QColor(THEME["bg_input"]))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(THEME["bg_panel"]))
    pal.setColor(QPalette.ColorRole.Text, QColor(THEME["text_primary"]))
    pal.setColor(QPalette.ColorRole.Button, QColor(THEME["bg_bar"]))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(THEME["text_secondary"]))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(THEME["accent_primary"]))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(THEME["bg_main"]))
    app.setPalette(pal)

    if not DEV and not project.FOUND and not firstrun.ensure():
        return                                # asked, declined; nothing to show

    _load_pages()
    win = Studio()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    sys.exit(main() or 0)
