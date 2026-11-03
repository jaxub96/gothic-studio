# Building Gothic Studio on macOS

For Apple Silicon (M1–M5) and Intel Macs. The app is plain Python + PyQt6 with
no Windows-only code, so it runs on macOS unchanged — but **PyInstaller cannot
cross-compile**. A `.app` has to be built on a Mac. There is no way to produce
one from Windows.

The build takes about five minutes, most of it `pip install`.

---

## The short version

```sh
cd gothic-studio
./build-macos.sh
```

That is the whole thing. The script checks your Python, creates a virtualenv,
installs the dependencies, runs the app once from source to catch problems
early, builds `dist/GothicStudio.app`, and clears the quarantine flag so it
opens without the Gatekeeper dance. Safe to re-run — it reuses the venv and
skips installs that are already done.

You still need your own Gothic II files; the app asks for the folder on first
launch. See [Pointing it at your Gothic II](#pointing-it-at-your-gothic-ii).

The rest of this page is what the script does, step by step, for when
something goes wrong or you want to do it by hand.

---

## Before you start

You need **your own copy of Gothic II**. Gothic Studio ships no game data — it
reads the real `Content/`, `Textures/` and `Meshes/` folders off disk. See
[Pointing it at your Gothic II](#pointing-it-at-your-gothic-ii) below; you can
build first and sort that out afterwards.

---

## 1. Install Python

macOS ships a Python, but it is the system one and PyQt6 does not belong in it.
Install your own:

```sh
# Homebrew — install Homebrew first from https://brew.sh if you have not got it
brew install python@3.12
```

Or download the **macOS 64-bit universal2 installer** from
[python.org/downloads](https://www.python.org/downloads/).

Check what you got:

```sh
python3 --version          # 3.10 or newer
python3 -c "import platform; print(platform.machine())"
```

On an M-series Mac that should print `arm64`. If it prints `x86_64` you are
running under Rosetta — that still works, but the build will be an Intel one
and noticeably slower. Use a native arm64 Python if you can.

## 2. Get the source

```sh
git clone <your-repo-url> gothic-studio
cd gothic-studio
```

Or copy the `gothic-studio/` folder over from Windows. All the `.py`
files need to stay together.

## 3. Create a virtual environment

Keeps PyQt6 out of your system Python, and `run.sh` picks it up automatically.

```sh
python3 -m venv .venv
source .venv/bin/activate
```

Your prompt now starts with `(.venv)`. Every command below assumes it is
active — if you open a new terminal, run `source .venv/bin/activate` again.

## 4. Install the dependencies

```sh
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
```

`requirements.txt` is PyQt6 and numpy. Both ship arm64 wheels, so nothing gets
compiled from source and this should take under a minute.

## 5. Run it from source first

Always check the source runs before freezing it. A frozen build that fails
gives you far less to go on.

```sh
python studio.py --check
```

That prints where it thinks the mod is and what it can see. Then:

```sh
python studio.py
```

The window should open. If it cannot find your Gothic II, it will ask —
see [below](#pointing-it-at-your-gothic-ii).

## 6. Build the .app

```sh
python build_exe.py
```

You get `dist/GothicStudio.app`, around 45 MB. The script prints the path and
the size when it finishes.

## 7. First launch

The bundle is unsigned, so Gatekeeper blocks a plain double-click with
*"GothicStudio.app cannot be opened because the developer cannot be verified."*

**Right-click the app → Open → Open.** Once. macOS remembers.

Or strip the quarantine flag from the terminal:

```sh
xattr -dr com.apple.quarantine /path/to/GothicStudio.app
```

Signing it properly needs a paid Apple Developer account, and is only worth it
if you are handing the build to other people:

```sh
codesign --deep --force --sign "Developer ID Application: Your Name (TEAMID)" GothicStudio.app
xcrun notarytool submit GothicStudio.app --apple-id you@example.com --team-id TEAMID --wait
```

---

## Pointing it at your Gothic II

Gothic Studio contains no game assets — it reads your own installation. It
finds it three ways, in this order:

1. **`GOTHIC_SCRIPTS`** environment variable — a one-off override:
   ```sh
   GOTHIC_SCRIPTS="/Users/you/Gothic II/_work/Data/Scripts" ./run.sh
   ```
2. **The folder you picked in the app.** On first run it asks, and remembers
   the answer in
   `~/Library/Application Support/GothicStudio/config.json`.
   Change it later with **Change mod folder** in the status bar (restart after).
3. **Walking up from the app's own location** looking for
   `Content/Gothic.src`. This only works if `GothicStudio.app` is placed inside
   the mod's tree (e.g. its `tools/` folder); from `dist/` use 1 or 2.

Whichever it used, the status bar at the bottom of the window always shows the
path it is actually reading.

### Which folder to pick

The one containing `Content/Gothic.src` — in a standard MDK install:

```
Gothic II/_work/Data/Scripts        <- pick this
├── Content/
│   ├── Gothic.src
│   ├── Items/
│   └── Story/
└── tools/
```

If you pick `Data/` or `_work/` by mistake, the app spots the `Scripts` folder
underneath and offers it.

### Getting Gothic II onto a Mac

The game is Windows-only, so a native macOS install does not exist. The files
have to come from somewhere:

- **Copy them from a Windows machine or VM.** They are just files. See
  [What to copy](#what-to-copy) — it is less than the full install.
- **A CrossOver / Wine / Whisky prefix.** The install lives under something like
  `~/Library/Application Support/CrossOver/Bottles/Gothic2/drive_c/`. Point
  Gothic Studio straight at the `Scripts` folder in there.
- **A shared folder from Parallels / VMware / UTM.** Works, but reading 291 MB
  of textures across a VM share is slow. A local copy is much better.

### What to copy

The folder you pick is `Scripts`, but the app reads sideways and upward out of
it. Copy this much and everything works:

```
Gothic II/
├── Data/                                  518 MB of these are read
│   ├── Textures.vdf, Textures_Addon.vdf   face and armor previews
│   ├── Meshes.vdf,   Meshes_Addon.vdf     item models
│   └── Anims.vdf,    Anims_Addon.vdf      heads, bodies, skeleton
└── _work/Data/                            ~325 MB
    ├── Textures/_compiled/                your textures, override the archives
    ├── Meshes/_compiled/                  your item meshes
    ├── Anims/_compiled/, Anims/mds_overlay/
    ├── Worlds/                            .zen files: waypoint names
    └── Scripts/                           <- point the app here
        └── Content/                       items, guilds, routines, NPCs
```

`Speech*.vdf` and `Sounds*.vdf` are 1.4 GB that Gothic Studio never opens —
leave them behind. A `.vdf.disabled` suffix is the MDK parking an archive so
loose files win; the app reads both spellings, so copy them as they are.

Any of it may be missing. Without the textures, meshes and archives you still
get every picker and every generated `.d` file — the previews just go blank and
the 3D view stays empty. Without `Data/Worlds` the waypoint list is
empty and you type names by hand. `--check` names whichever part it could not
find.

### Case sensitivity

Gothic's tools are inconsistent about filename case, and macOS's default APFS
volume is case-insensitive, so this rarely bites. But `pathlib.glob` is
case-**sensitive** on macOS regardless of the filesystem, which is why the app
matches filenames through `project.iglob()` rather than `Path.glob()`. If you
keep your mod on a case-sensitive volume, that is what makes it work.

---

## The compile check on macOS

The **Compile check** button shells out to `gdc`, the Daedalus compiler. The
mod's `tools/` folder ships `gdc-windows-x64.exe`, which cannot run on macOS — but an
Apple Silicon build is published, so this is a download, not a build.

Get it from
[dzieje-khorinis/DaedalusCompiler releases](https://github.com/dzieje-khorinis/DaedalusCompiler/releases)
— the same 0.9.5 release ships all six platforms:

| Mac | Asset |
|---|---|
| Apple Silicon (M1–M5) | `gdc-macos-arm64` |
| Intel | `gdc-macos-x64` |

Take `gdc-runtime.d` from the mod's `tools/` folder too — gdc needs both, and
they have to sit in the same directory.

```sh
chmod +x gdc-macos-arm64                           # downloads arrive non-executable
xattr -d com.apple.quarantine gdc-macos-arm64
```

Then either drop it in the mod's `tools/` folder or beside the app, or just
press **Locate gdc** in the status bar and point at it. That button only
appears when gdc is missing, and the setting takes effect immediately.

Without gdc, everything else works — the button reports what it wanted and
offers to locate it. Editing, previewing and generating `.d` files never touch
the compiler.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'PyQt6'`**
The venv is not active. `source .venv/bin/activate`.

**The app opens, then immediately quits**
Run `python studio.py --check` from source. It prints the mod path, the config
file and what it managed to index.

**A built `.app` misbehaves but the source is fine**
PyInstaller missed an import. Build a console version to see the traceback:

```sh
pyinstaller --onefile --paths . --name GothicStudioDebug studio.py
./dist/GothicStudioDebug --check
```

**"is damaged and can't be opened"**
Quarantine, not damage. `xattr -dr com.apple.quarantine GothicStudio.app`.

**Previews are blank and the mod is found**
`Textures/_compiled` is not next to `Scripts/`. `--check` reports what it
indexed — `0` means it looked there and found nothing.

**Wrong architecture / "bad CPU type"**
You built with an x86_64 Python under Rosetta and are running native, or the
reverse. `python3 -c "import platform; print(platform.machine())"` inside the
venv tells you which one you built with.

---

## A note on bundling the game data

The obvious question is whether the assets could just be baked into the `.app`
so nobody has to point at anything. Technically yes; three reasons not to:

- **It breaks the point of the tool.** It reads the mod live, so a script you
  edit shows up in the pickers straight away. Frozen data would mean rebuilding
  the app to see a new NPC.
- **Size and startup.** `Textures/_compiled` alone is 291 MB, and a `--onefile`
  build unpacks everything to a temp folder on *every* launch.
- **They are not ours to ship.** The assets are Piranha Bytes / THQ Nordic's.
  Reading the copy you bought is fine; redistributing it is not.

So: the app stays empty, and points at your install.
