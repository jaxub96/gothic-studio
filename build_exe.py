"""
build_exe.py - freeze Gothic Studio into a single app.

    pip install pyinstaller
    python build_exe.py

Produces, next to this folder, in tools/:

    Windows   GothicStudio.exe
    macOS     GothicStudio.app        (plus a bare unix binary, harmless)
    Linux     GothicStudio

The result is standalone - Python, PyQt6 and numpy are inside it - but NOT
self-contained: it holds no Gothic data at all. At startup it looks for the
mod, in this order: the GOTHIC_SCRIPTS environment variable, the folder the
user last picked in the app, then by walking up from its own location looking
for Content/Gothic.src. That last one is why the build lands in tools/, one
level below Scripts/: dropped there, it just works. Anywhere else, the app
asks for the folder on first run and remembers the answer.

PyInstaller cannot cross-compile. A macOS build has to be produced on a Mac -
see BUILDING-MACOS.md. Build artefacts land in build/ and can be deleted.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DIST = HERE / "dist"
BUILD = HERE / "build"
ASSETS = HERE / "assets"

NAME = "GothicStudio"
BUNDLE_ID = "org.gothicstudio.app"

MACOS = sys.platform == "darwin"
WINDOWS = sys.platform == "win32"

# Qt ships a lot we never touch. Dropping these keeps the build near 45 MB
# instead of 90 MB and shortens the onefile unpack on startup.
EXCLUDE = [
    "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebChannel",
    "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuick3D", "PyQt6.QtMultimedia",
    "PyQt6.QtBluetooth", "PyQt6.QtNetwork", "PyQt6.QtSql", "PyQt6.QtTest",
    "PyQt6.QtDBus", "PyQt6.QtOpenGL", "PyQt6.QtPositioning", "PyQt6.QtCharts",
    "PyQt6.QtSerialPort", "PyQt6.QtSensors", "PyQt6.QtPdf", "PyQt6.QtSvg",
    "tkinter", "unittest", "pydoc", "email", "http", "xml", "pdb",
    "PIL", "setuptools", "pip",     # numpy is NOT excluded: it accelerates the 3D view
]


def artifact():
    """What this platform's build is actually called, once it exists."""
    if WINDOWS:
        return DIST / f"{NAME}.exe"
    if MACOS:
        return DIST / f"{NAME}.app"       # --windowed gives a bundle, not a file
    return DIST / NAME


def _size_mb(path):
    if path.is_file():
        return path.stat().st_size / 1024 / 1024
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / 1024 / 1024


def _mtime(path):
    """Newest mtime inside `path`. A .app is a directory, so stat() alone lies."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_mtime
    return max([path.stat().st_mtime]
               + [f.stat().st_mtime for f in path.rglob("*") if f.is_file()])


def _stamp_version(app):
    """Put the release number in the .app's Info.plist (Finder's Get Info shows it)."""
    import plistlib
    from version import VERSION
    plist = app / "Contents" / "Info.plist"
    try:
        info = plistlib.loads(plist.read_bytes())
        info["CFBundleShortVersionString"] = VERSION
        info["CFBundleVersion"] = VERSION
        plist.write_bytes(plistlib.dumps(info))
    except (OSError, ValueError) as exc:
        print(f"warning: could not stamp the version into Info.plist ({exc})")


def main():
    out = artifact()
    before = _mtime(out)

    # Windows will not let PyInstaller overwrite a running exe. It reports the
    # PermissionError but still exits 0, so without this check a failed build
    # looks like a good one and you keep testing the old binary. POSIX has no
    # such rule - there, an overwrite during a run is fine.
    if WINDOWS and out.exists():
        try:
            with open(out, "ab"):
                pass
        except PermissionError:
            print(f"ERROR: {out.name} is running. Close it and build again.")
            return 1

    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--onefile",
        "--windowed",                 # no console/terminal behind the GUI
        "--name", NAME,
        "--distpath", str(DIST),      # dist/GothicStudio[.exe|.app]
        "--workpath", str(BUILD),
        "--specpath", str(BUILD),
        # npc_tabs is imported by name, but keep these explicit so a future
        # refactor to dynamic imports does not silently drop a tab.
        "--hidden-import", "npc_tabs.general_tab",
        "--hidden-import", "npc_tabs.stats_tab",
        "--hidden-import", "npc_tabs.skills_tab",
        "--hidden-import", "npc_tabs.visual_tab",
        "--hidden-import", "npc_tabs.inventory_tab",
        "--paths", str(HERE),
        # the PNG is what the running app shows in its title bar and taskbar
        "--add-data", f"{ASSETS / 'icon.png'}{os.pathsep}assets",
    ]
    if WINDOWS:
        args += ["--icon", str(ASSETS / "icon.ico")]
    if MACOS:
        # Without an identifier macOS treats every rebuild as a different app
        # and re-asks for any permission the user has already granted.
        args += ["--osx-bundle-identifier", BUNDLE_ID,
                 "--icon", str(ASSETS / "icon.icns")]
    for module in EXCLUDE:
        args += ["--exclude-module", module]
    args.append(str(HERE / "studio.py"))

    # flush: our stdout is block-buffered when piped to a file, PyInstaller's
    # is not, so without this the banner lands after its output in any log.
    print(f"building for {sys.platform} / {platform.machine()}...", flush=True)
    result = subprocess.run(args, cwd=HERE)
    if result.returncode != 0:
        return result.returncode

    if not out.exists() or _mtime(out) <= before:
        print(f"ERROR: {out.name} was not replaced - the build did not succeed.")
        return 1

    print(f"\n{out}  ({_size_mb(out):.1f} MB)")
    if MACOS:
        # The bare unix binary sits next to the bundle and confuses people into
        # double-clicking it, which opens a Terminal window. The .app is the
        # one to ship.
        stray = DIST / NAME
        if stray.is_file():
            stray.unlink()
        _stamp_version(out)
        print("Unsigned: first launch needs right-click > Open, or\n"
              f"  xattr -dr com.apple.quarantine '{out}'")

    shutil.rmtree(BUILD, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
