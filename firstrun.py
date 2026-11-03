"""
firstrun.py - "where is your Gothic II?", asked once and remembered.

Gothic Studio ships no game data. It reads the real Content/, Textures/ and
Meshes/ folders off disk, which means it has to be told where a legally owned
Gothic II install lives. Anyone running the app from inside a mod's Scripts/
folder never sees this: project.py finds the mod by walking up. Everyone else
gets asked here, once, and config.py keeps the answer.

Import order matters. gamedata.py and textures.py snapshot project.SCRIPTS at
import time, so the folder has to be settled before either of them loads -
studio.py calls into this module first, then imports its pages.
"""

import importlib
import os
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFileDialog, QMessageBox

import config
import project

WANTED = "Content/Gothic.src"

EXPLAIN = (
    "Gothic Studio needs your Gothic II files.\n\n"
    "It does not ship any game data - it reads your own installation, so "
    "everything you see comes from the copy of the game you bought.\n\n"
    "Pick the mod's <b>Scripts</b> folder: the one containing "
    "<code>Content/Gothic.src</code>. In a standard MDK install that is\n\n"
    "<code>Gothic II/_work/Data/Scripts</code>")


def _looks_like_data(path):
    """A Data/ or _work/ folder is the classic near-miss - nudge, do not reject."""
    path = Path(path)
    if (path / "Scripts" / "Content" / "Gothic.src").is_file():
        return path / "Scripts"
    if (path / "Data" / "Scripts" / "Content" / "Gothic.src").is_file():
        return path / "Data" / "Scripts"
    return None


def choose(parent=None, start=None):
    """Ask for the Scripts folder until we get a real one. None if cancelled."""
    start = str(start or Path.home())
    while True:
        picked = QFileDialog.getExistingDirectory(
            parent, "Select the mod's Scripts folder (containing Content/Gothic.src)",
            start)
        if not picked:
            return None

        if project.is_scripts_root(picked):
            return Path(picked)

        # Landed one or two levels high: offer the right folder rather than
        # making them navigate again.
        nearby = _looks_like_data(picked)
        if nearby:
            ask = QMessageBox.question(
                parent, "Is this the one?",
                f"{picked}\n\nis not the Scripts folder, but\n\n{nearby}\n\n"
                "underneath it is. Use that?")
            if ask == QMessageBox.StandardButton.Yes:
                return nearby

        QMessageBox.warning(
            parent, "Not a Scripts folder",
            f"{picked}\n\ndoes not contain {WANTED}.\n\n"
            "Pick the folder that does - usually Gothic II/_work/Data/Scripts.")
        start = picked


def remember(path):
    """Save the folder and make project.py see it. True if the save stuck."""
    ok = config.save("scripts_root", str(path))
    importlib.reload(project)                 # SCRIPTS, CONTENT, FOUND, ... all rebind
    return ok


def ensure(parent=None):
    """Called at startup when project.FOUND is False.

    True once a mod folder is in place - the caller may then import the pages.
    False if the user cancelled, in which case there is nothing to show them.
    """
    box = QMessageBox(parent)
    box.setWindowTitle("Locate Gothic II")
    box.setTextFormat(Qt.TextFormat.RichText)
    box.setText(EXPLAIN)
    box.setStandardButtons(QMessageBox.StandardButton.Open
                           | QMessageBox.StandardButton.Cancel)
    box.button(QMessageBox.StandardButton.Open).setText("Choose folder...")
    if box.exec() != QMessageBox.StandardButton.Open:
        return False

    picked = choose(parent)
    if picked is None:
        return False

    if not remember(picked):
        QMessageBox.warning(
            parent, "Could not save",
            f"Using {picked} for this session, but the choice could not be "
            f"written to\n\n{config.CONFIG_FILE}\n\nYou will be asked again "
            "next time.")
        # Fall back to the env var so this session still works.
        os.environ["GOTHIC_SCRIPTS"] = str(picked)
        importlib.reload(project)
    return project.FOUND


def choose_gdc(parent=None):
    """Point at a gdc binary. True if one was picked and saved.

    Unlike the mod folder this takes effect at once - project.find_gdc() reads
    the setting on every compile, so there is nothing to restart.
    """
    start = project.find_gdc()
    start = str(start.parent if start.parent.is_dir() else Path.home())

    picked, _ = QFileDialog.getOpenFileName(
        parent, f"Select {project.GDC_NAME}", start,
        f"gdc ({project.GDC_NAME});;All files (*)")
    if not picked:
        return False

    picked = Path(picked)
    runtime = picked.parent / "gdc-runtime.d"
    if not runtime.is_file():
        ask = QMessageBox.question(
            parent, "No gdc-runtime.d beside it",
            f"{picked.name} has no gdc-runtime.d next to it.\n\n"
            "The compile check needs both, and they normally ship together. "
            "Use this one anyway?")
        if ask != QMessageBox.StandardButton.Yes:
            return False

    if not config.save("gdc_path", str(picked)):
        QMessageBox.warning(parent, "Could not save",
                            f"Failed to write {config.CONFIG_FILE}.")
        return False
    return True


def change(parent=None):
    """The 'Change mod folder' button. Needs a restart to take effect.

    gamedata.py and textures.py cache the old paths behind lru_cache and read
    project.SCRIPTS at import time, so swapping mods in a live window would
    show a convincing mix of both. Saving and restarting is the honest option.
    """
    picked = choose(parent, start=project.SCRIPTS)
    if picked is None:
        return False
    if picked == project.SCRIPTS:
        return False

    if not config.save("scripts_root", str(picked)):
        QMessageBox.warning(parent, "Could not save",
                            f"Failed to write {config.CONFIG_FILE}.")
        return False

    QMessageBox.information(
        parent, "Mod folder saved",
        f"Gothic Studio will use\n\n{picked}\n\nRestart it to load that mod.")
    return True
