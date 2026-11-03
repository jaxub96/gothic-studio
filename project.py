"""
project.py - where this app sits relative to the mod, and how to write files
the engine can actually read.

Every path and every encoding decision lives here. If you move the tool, this
is the only file you have to fix.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import config


def app_dir():
    """The folder the app itself lives in - the exe's, or this source tree's.

    On macOS a frozen build is GothicStudio.app/Contents/MacOS/GothicStudio, so
    sys.executable is buried three levels inside the bundle. Report the folder
    holding the .app instead: that is where someone would drop a gdc binary
    next to it, and what they mean by "where the app is".
    """
    if getattr(sys, "frozen", False):        # PyInstaller
        here = Path(sys.executable).resolve().parent
        for parent in here.parents:
            if parent.suffix == ".app":
                return parent.parent
        return here
    return Path(__file__).resolve().parent


def is_scripts_root(path):
    """True if `path` is a Data/Scripts folder we can actually work with."""
    try:
        return (Path(path) / "Content" / "Gothic.src").is_file()
    except OSError:
        return False                          # unreadable drive, dead symlink


def _dev_root(start):
    """A scratch mod for --dev: .devmod/, seeded once from devdata/.

    devdata/ is a tiny stand-in for Data/Scripts (a few guilds, items, armors,
    routines, faces) so every picker has something in it without Gothic II.
    """
    dev = start / ".devmod"
    seed = start / "devdata"
    if seed.is_dir() and not is_scripts_root(dev):
        shutil.copytree(seed, dev, dirs_exist_ok=True)
    return dev


def _find_scripts_root():
    """Locate ...\\Data\\Scripts, whether we run from source or as a frozen exe.

    Walks up from wherever we live looking for Content/Gothic.src. Running from
    source that is tools/gothic-studio/ -> Scripts/; as GothicStudio.exe sitting
    in tools/ it is one level up.

    Two things take precedence over that walk, in this order: the
    GOTHIC_SCRIPTS environment variable (a one-off override, handy for
    scripting), and the folder the user picked in the app, which config.py
    remembers. The saved folder is how someone running a downloaded build
    points Gothic Studio at their own Gothic II install.
    """
    override = os.environ.get("GOTHIC_SCRIPTS")
    if override:
        return Path(override).resolve()

    saved = config.get("scripts_root")
    if saved and is_scripts_root(saved):
        return Path(saved).resolve()

    start = app_dir()
    for candidate in (start, *start.parents):
        if is_scripts_root(candidate):
            return candidate
    if os.environ.get("GOTHIC_STUDIO_DEV"):   # dev mode: scratch folder, never the repo
        return _dev_root(start)
    return start                              # nothing found; FOUND stays False


SCRIPTS = _find_scripts_root()

#: True when running on the devdata/ stand-in rather than a real Gothic II mod.
DEV_FIXTURE = bool(os.environ.get("GOTHIC_STUDIO_DEV")) and SCRIPTS.name == ".devmod"
CONTENT = SCRIPTS / "Content"
TOOLS = SCRIPTS / "tools"

#: False when the app cannot see the mod - studio.py asks for the folder instead.
FOUND = is_scripts_root(SCRIPTS)

# ...\Data\Anims\mds_overlay - the real MDS overlay assets, next to Scripts\
ANIMS = SCRIPTS.parent / "Anims"
MDS_OVERLAY = ANIMS / "mds_overlay"

# Where generated files have to land to be picked up by Gothic.src:
#   line 236  STORY\NPC\*.d          <- any name works
#   line 295  STORY\DIALOGE\DIA*.d   <- MUST start with "DIA"
NPC_DIR = CONTENT / "Story" / "NPC"
DIA_DIR = CONTENT / "Story" / "Dialoge"
LOG_DIR = CONTENT / "Story" / "Log_Entries"

# ZenGin reads ANSI, never UTF-8. This install is Polish, so CP1250.
# Writing UTF-8 puts mojibake in the game and in zSpy.
ENCODING = "cp1250"


def _gdc_name():
    """The gdc build for this machine.

    Names match the upstream release assets exactly - "macos", not "darwin".
    All six are published together, so this is a download, not a build.
    """
    arm = platform.machine().lower() in ("arm64", "aarch64")
    if sys.platform == "win32":
        return "gdc-windows-arm64.exe" if arm else "gdc-windows-x64.exe"
    if sys.platform == "darwin":
        return "gdc-macos-arm64" if arm else "gdc-macos-x64"
    return "gdc-linux-arm64" if arm else "gdc-linux-x64"


def _find_tool(name):
    """Look for a helper binary in the mod's tools/, then next to the app.

    When the mod is somewhere else entirely - which it is for anyone running a
    downloaded build against their own Gothic install - that mod's tools/ holds
    nothing of ours, so the copy shipped alongside the app has to count.
    """
    here = app_dir()
    for base in (TOOLS, here, here / "tools", here.parent, here.parent / "tools"):
        candidate = base / name
        if candidate.is_file():
            return candidate
    return TOOLS / name                       # nowhere: report the expected path


GDC_NAME = _gdc_name()


def find_gdc():
    """Where gdc is, right now.

    Resolved on every call rather than cached at import: unlike the mod folder,
    a gdc picked in the app takes effect immediately - nothing has snapshotted
    it. Saved path first, then the usual places.
    """
    saved = config.get("gdc_path")
    if saved and Path(saved).is_file():
        return Path(saved)
    return _find_tool(GDC_NAME)


def find_gdc_runtime():
    """gdc-runtime.d - the declarations gdc needs. Ships next to gdc itself."""
    saved = config.get("gdc_path")
    if saved:
        beside = Path(saved).parent / "gdc-runtime.d"
        if beside.is_file():
            return beside
    return _find_tool("gdc-runtime.d")


GDC = find_gdc()
GOTHIC_SRC = CONTENT / "Gothic.src"
CHECK_DIR = SCRIPTS / ".check"


def _anycase(pattern):
    """Turn "Humans_*.mds" into "[hH][uU]...[mM][dD][sS]" - a glob that ignores case."""
    return "".join(f"[{c.lower()}{c.upper()}]" if c.isascii() and c.isalpha() else c
                   for c in pattern)


def iglob(base, pattern):
    """Path.glob, but case-insensitive. Returns [] if `base` is not a folder.

    Path.glob is case-sensitive on macOS and Linux even when the filesystem is
    not, so "*.TEX" quietly matches nothing against files named ".tex". Which
    case Gothic's compilers and unpackers leave behind is not something we get
    to decide, and on Windows the difference never showed up at all.

    Patterns are ordinary globs - "*", "**", and "/" all work. Character
    classes do not: they would be rewritten along with everything else.
    """
    base = Path(base)
    if not base.is_dir():
        return []
    return list(base.glob(_anycase(pattern)))


def read_script(path):
    """Read a .d the way the engine wrote it."""
    return Path(path).read_text(encoding=ENCODING, errors="replace")


def write_script(path, text):
    """Write a .d the way the engine expects it: CP1250, CRLF."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding=ENCODING, errors="replace", newline="\r\n") as f:
        f.write(text)
    return path


def compile_check():
    """Run gdc over the whole mod.

    Returns (ok, lines). `lines` holds only the error lines, already trimmed
    to 'file:line:col: error: ...' - the same thing tools/lint-gdc-output.ps1
    prints, minus the PowerShell.
    """
    gdc, runtime = find_gdc(), find_gdc_runtime()
    if not gdc.is_file():
        return False, [f"gdc not found: {gdc}",
                       f"Put a {GDC_NAME} build beside the app, or use "
                       f"Locate gdc to point at one."]
    if not runtime.is_file():
        return False, [f"gdc-runtime.d not found: {runtime}",
                       "It ships alongside gdc - keep the two in one folder."]

    CHECK_DIR.mkdir(exist_ok=True)
    proc = subprocess.run(
        [str(gdc), str(GOTHIC_SRC),
         "--runtime", str(runtime),
         "--output-dat", str(CHECK_DIR / "Gothic.dat")],
        capture_output=True, text=True, errors="replace",
        # gdc drops an "output" folder in its working directory. Run it from
        # Scripts\ like the VS Code task does, so it does not litter elsewhere.
        cwd=str(SCRIPTS),
    )
    out = (proc.stdout or "") + (proc.stderr or "")

    errors = [ln.strip() for ln in out.splitlines() if ": error:" in ln]
    ok = "Compilation completed successfully" in out
    if not ok and not errors:
        errors = [ln.strip() for ln in out.splitlines() if ln.strip()][-5:]
    return ok, errors
