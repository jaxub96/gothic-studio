"""
build_exe.py - freeze Gothic Studio into a single app.

    pip install pyinstaller
    python build_exe.py            # one file:   dist/GothicStudio.exe
    python build_exe.py --onedir   # one folder: dist/GothicStudio/GothicStudio.exe

Produces, in dist/:

    Windows   GothicStudio.exe
    macOS     GothicStudio.app

The single file is the easy one to hand around, but it unpacks itself into a
temp folder on every launch. The --onedir build skips that and starts
noticeably faster; ship the whole folder (zip it) and run the exe inside.

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

# Qt ships a lot we never touch. Dropping these modules roughly halves the build
# and shortens the onefile unpack on startup.
EXCLUDE = [
    "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebChannel",
    "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtQuick3D", "PyQt6.QtMultimedia",
    "PyQt6.QtBluetooth", "PyQt6.QtNetwork", "PyQt6.QtSql", "PyQt6.QtTest",
    "PyQt6.QtDBus", "PyQt6.QtOpenGL", "PyQt6.QtPositioning", "PyQt6.QtCharts",
    "PyQt6.QtSerialPort", "PyQt6.QtSensors", "PyQt6.QtPdf", "PyQt6.QtSvg",
    "tkinter", "unittest", "pydoc", "email", "http", "xml", "pdb",
    "PIL", "setuptools", "pip",     # numpy is NOT excluded: it accelerates the 3D view
]

# Files PyInstaller's Qt hooks collect whatever the excludes above say, which the
# app never loads. Matched as substrings of the bundled path, lowercased with
# forward slashes. Every one of these is also unpacked to a temp folder on each
# launch of a --onefile build, so dropping them speeds up startup as well.
TRIM = [
    "/opengl32sw.dll",              # ~20 MB software OpenGL; render3d.py draws without OpenGL
    "/d3dcompiler_", "/libegl.dll", "/libglesv2.dll",    # ANGLE, same reason
    "/qt6/translations/",           # Qt's own UI strings; the app never installs a QTranslator
    "/plugins/imageformats/",       # only icon.png goes through Qt, and PNG is built in
    "/plugins/iconengines/",        # SVG icons; the app draws its icons itself (ui.py)
    "/plugins/styles/",             # native styles; main() switches to the built-in Fusion
    "/plugins/generic/", "/plugins/tls/", "/plugins/networkinformation/",
    "/qt6svg.dll", "/qt6network.dll",   # only the plugins above link these
]

# Inserted into the generated .spec between Analysis() and PYZ(): the only point
# where collected files can be dropped (--exclude-module only knows modules).
SPEC_FILTER = '''
_TRIM = {trim!r}
def _keep(entry):
    path = "/" + entry[0].replace("\\\\", "/").lower()
    return not any(t in path for t in _TRIM)
_before = len(a.binaries) + len(a.datas)
a.binaries = [e for e in a.binaries if _keep(e)]
a.datas = [e for e in a.datas if _keep(e)]
print(f"trimmed {{_before - len(a.binaries) - len(a.datas)}} unused Qt files", flush=True)

'''


def artifact(onedir=False):
    """What this platform's build is actually called, once it exists."""
    if MACOS:
        return DIST / f"{NAME}.app"       # --windowed gives a bundle, not a file
    exe = f"{NAME}.exe" if WINDOWS else NAME
    return DIST / NAME / exe if onedir else DIST / exe


def _size_mb(path):
    if path.is_file():
        return path.stat().st_size / 1024 / 1024
    # skip symlinks: a bundle links some files under a second name
    return sum(f.stat().st_size for f in path.rglob("*")
               if f.is_file() and not f.is_symlink()) / 1024 / 1024


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
    onedir = "--onedir" in sys.argv[1:]
    out = artifact(onedir)
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

    # Step 1: write the .spec. These options are the whole build description.
    spec_args = [
        "--onedir" if onedir else "--onefile",
        "--windowed",                 # no console/terminal behind the GUI
        "--name", NAME,
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
        spec_args += ["--icon", str(ASSETS / "icon.ico")]
    if MACOS:
        # Without an identifier macOS treats every rebuild as a different app
        # and re-asks for any permission the user has already granted.
        spec_args += ["--osx-bundle-identifier", BUNDLE_ID,
                      "--icon", str(ASSETS / "icon.icns")]
    for module in EXCLUDE:
        spec_args += ["--exclude-module", module]
    spec_args.append(str(HERE / "studio.py"))

    # flush: our stdout is block-buffered when piped to a file, PyInstaller's
    # is not, so without this the banner lands after its output in any log.
    kind = "folder (--onedir)" if onedir else "single file"
    print(f"building a {kind} for {sys.platform} / {platform.machine()}...", flush=True)
    BUILD.mkdir(exist_ok=True)
    result = subprocess.run([sys.executable, "-m", "PyInstaller.utils.cliutils.makespec",
                             *spec_args], cwd=HERE)
    if result.returncode != 0:
        return result.returncode

    # Step 2: drop the Qt files the app never loads (see TRIM).
    spec = BUILD / f"{NAME}.spec"
    text = spec.read_text(encoding="utf-8")
    if "\npyz = PYZ(" not in text:
        print("ERROR: unexpected .spec layout from PyInstaller; cannot trim it.")
        return 1
    text = text.replace("\npyz = PYZ(", SPEC_FILTER.format(trim=TRIM) + "pyz = PYZ(", 1)
    spec.write_text(text, encoding="utf-8")

    # Step 3: build from it.
    result = subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                             "--distpath", str(DIST),       # dist/GothicStudio[.exe|.app]
                             "--workpath", str(BUILD), str(spec)], cwd=HERE)
    if result.returncode != 0:
        return result.returncode

    if not out.exists() or _mtime(out) <= before:
        print(f"ERROR: {out.name} was not replaced - the build did not succeed.")
        return 1

    shipped = out.parent if onedir and not MACOS else out    # the folder is what ships
    print(f"\n{out}  ({_size_mb(shipped):.1f} MB)")
    if MACOS:
        # The bare unix binary sits next to the bundle and confuses people into
        # double-clicking it, which opens a Terminal window. The .app is the
        # one to ship.
        stray = DIST / NAME
        if stray.is_file():
            stray.unlink()
        elif stray.is_dir():
            shutil.rmtree(stray)
        _stamp_version(out)
        print("Unsigned: first launch needs right-click > Open, or\n"
              f"  xattr -dr com.apple.quarantine '{out}'")

    shutil.rmtree(BUILD, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
