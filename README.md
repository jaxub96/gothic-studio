# Gothic Studio

NPC creator + dialog editor in one app, reading whatever is actually in your
Gothic II `Content/`. Your mod's own scripts (guilds, constants, items, sample
NPCs, dialogs, a quest) live in [`mod/`](mod/README.md); `python mod/install.py`
installs them into the mod Gothic Studio is using.

## Run it

- **From source, like an app** (main way) - run `make-shortcut.bat` (Windows) or
  `./make-shortcut.sh` (macOS) once. It sets up `.venv` and puts a **Gothic
  Studio** shortcut with the app icon on the Desktop (and Start menu / `~/Applications`).
  No console window; edits to the `.py` files apply on the next launch. Re-run
  it if you move the folder. `run.bat` / `./run.sh` do the same with errors visible.
- **In a terminal:** `pip install -r requirements.txt`, then `python studio.py`
  (`--dev` needs no Gothic II; it copies `devdata/` to `.devmod/`).
- **As an exe / app:** `build-windows.bat` or `./build-macos.sh` produces
  `dist/GothicStudio.exe` / `.app` (~30s; add `--onedir` to `python build_exe.py`
  for a faster-starting folder). `dist/` and `build/` are git-ignored. Mac
  details: [BUILDING-MACOS.md](BUILDING-MACOS.md).

## Finding the mod

The app holds no game data, so it needs to know where Gothic II lives, in order:

1. `GOTHIC_SCRIPTS` environment variable.
2. The folder you pick on first run (change it with **Change mod folder** in the
   status bar; restart needed). Saved in `config.json` under `%APPDATA%\GothicStudio`,
   `~/Library/Application Support/GothicStudio` or `~/.config/GothicStudio`.
   Delete it to be asked again.
3. Walking up from the app looking for `Content/Gothic.src`.

`GothicStudio.exe --check > check.txt` reports the resolved paths and what was
found. Dark mode is a status-bar toggle, saved in `config.json`.

## Layout

| File | Role |
|---|---|
| `studio.py` | The window; start here. |
| `project.py`, `gamedata.py` | Paths/encoding; scrapes `Content/` for real identifiers. |
| `npc_*.py`, `npc_tabs/` | NPC model, `.d` generation, and one file per form tab. |
| `dialog_*.py` | Dialog model/codegen/parser, tab and chat-bubble widgets. |
| `startup_gen.py`, `teach_gen.py` | `Wld_InsertNpc` lines in `Startup.d`; teaching dialogs. |
| `textures.py`, `mesh.py`, `render3d.py`, `model_view.py` | Gothic texture/mesh readers and the software 3D preview. |
| `ui.py`, `theme.py` | The component set and all colours/fonts. |
| `selftest.py` | Headless end-to-end check, then compiles with gdc. |

## UI rules

`ui.py` is the only module that writes a stylesheet; screens are built from its
components (`section`, `field`, `button`, `dropdown`, `number`, ...). Add a
variant there rather than styling elsewhere. Pick the control that fits the
data: `number` for exact values, `choice`/`toggle_row` for few named states,
`search_dropdown` for long lists, a slider only for continuous values judged by eye.

## What Save to mod writes

| Where | File | When |
|---|---|---|
| `Story/NPC/` | the NPC `.d` | always |
| `Story/Dialoge/` | `DIA_<npc>_Teach.d` | talents ticked |
| `Story/Startup.d` | one `Wld_InsertNpc` line | *Put this NPC into the world* ticked |

The Dialog tab's **Save** writes `Story/Dialoge/DIA_<npc>.d` (and log topics to
`Story/Log_Entries/`). Files are CP1250; dialog files must be named `DIA*.d`
or `Gothic.src` never compiles them. **Validate** checks identifiers instantly;
**Compile check** runs `gdc` over the mod (~3s).

## Known limits

- The dialog `.d` parser is regex-based: it round-trips this tool's files and
  simple vanilla ones, not arbitrary Daedalus.
- `B_SetAttributesToChapter` overwrites `level` (engine behaviour).
- Waypoints come from `.zen` files in `Data/Worlds`; without them the field is free text.
