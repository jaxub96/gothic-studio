# Gothic Studio

NPC creator + dialog editor in one app. A merge of `Gothic-2-NPC-Studio`
and `tools/Daedalogue`, with the Gothic 1 data replaced by whatever is actually
in `Content/`.

## Run it

**As an exe** — double-click `dist/GothicStudio.exe` (after building it). Nothing to install.

**From source** — for editing:

```
pip install -r requirements.txt
python studio.py          # or run.bat on Windows, ./run.sh on macOS/Linux
```

**On a Mac** — `cd gothic-studio && ./build-macos.sh` builds
`dist/GothicStudio.app` from scratch. The app is portable (no Windows-only code),
but PyInstaller cannot cross-compile, so it has to run on the Mac itself.
Details and troubleshooting in [BUILDING-MACOS.md](BUILDING-MACOS.md).

## The exe

`dist/GothicStudio.exe` (~34 MB) bundles Python and PyQt6, but **not** the mod:
it reads `Content/` live, the same as the source version, so edits you make to
scripts show up in the pickers straight away.

### Finding the mod

The app holds no game data at all, so it has to be told where a Gothic II
install lives. Three ways, in order of precedence:

1. **`GOTHIC_SCRIPTS`** — environment variable, a one-off override.
2. **The folder you picked** — asked for on first run when nothing else works,
   then remembered. Change it later with **Change mod folder** in the status
   bar; that needs a restart to take effect.
3. **Walking up from its own location** looking for `Content/Gothic.src`. This
   only works if the app is placed inside the mod's tree (e.g. its `tools/`
   folder); from `dist/` of a standalone checkout, use 1 or 2.

The saved folder lives in `%APPDATA%\GothicStudio\config.json` on Windows,
`~/Library/Application Support/GothicStudio/config.json` on macOS, and
`~/.config/GothicStudio/config.json` elsewhere. Delete it to be asked again.

The status bar always shows the path actually in use.

```
GothicStudio.exe --check > check.txt     # where am I, and what can I see?
```

The exe is built `--windowed`, so `--check` has no console to print to —
redirect it to a file. It reports the resolved paths and how many items,
guilds, routines and waypoints it found.

**Rebuild after editing the source:**

```
build-windows.bat         # Windows - sets up the venv too, or double-click it
./build-macos.sh          # macOS/Linux
```

Both are re-runnable and do the same four things: check Python, create or reuse
`.venv`, install what is missing, then run `build_exe.py`. To skip straight to
the build in an environment you have already set up:

```
python build_exe.py
```

Takes ~30s and overwrites `dist/GothicStudio.exe` — or produces
`dist/GothicStudio.app` on macOS, `dist/GothicStudio` on Linux. Build scratch
goes to `build/` and is deleted afterwards.

> The exe is a build artefact; `dist/` and `build/` are git-ignored.

## What changed vs. the two old tools

Both old tools produced `.d` files that **did not compile**. Verified with
the mod's `tools/gdc-windows-x64.exe`:

| Old output | Error | Now emits |
|---|---|---|
| `Mdl_SetNpcVisual(...)` | undeclared | `B_SetNpcVisual(self, MALE, head, face, bodyTex, armor)` |
| `B_Scale(self)` | undeclared | (dropped - `B_SetNpcVisual` scales internally) |
| `TA_Position(...)` | undeclared | a real `TA_*` picked from `gamedata.routines()` |
| `B_GiveXP(n)` | undeclared | `B_GivePlayerXP(n)` |
| `AI_StartState(self, ZS_FOLLOW, ...)` | undeclared | `ZS_Follow_Player` |
| log topics | never declared | `const string TOPIC_X = "...";` written to `Log_Entries/` |

Plus:

- **Encoding.** Files are written **CP1250**, not UTF-8. The old tools wrote
  UTF-8, which puts mojibake in-game (this install is Polish).
- **Output location.** Saves into `Content/Story/NPC/` and
  `Content/Story/Dialoge/` so `Gothic.src` actually picks the files up. Dialog
  files are named `DIA*.d` because line 295 globs `STORY\DIALOGE\DIA*.d` - a
  file not starting with `DIA` is silently never compiled.
- **No hardcoded game data.** Guilds, items, armors, heads, faces, tactics,
  routines, waypoints and NPC ids are all read out of `Content/` at startup.
  The old `data/*.py` tables were Gothic 1: 512 of their 523 item ids did not
  exist here.
- **EXIT block.** Only emitted if this NPC does not already have one somewhere
  else, otherwise you get `redefinition of DIA_<NPC>_EXIT`.
- **The link.** The NPC tab's instance name feeds the Dialog tab's NPC ID, so
  you type the identifier once.

## Files

| File | What it is |
|---|---|
| `studio.py` | The window. Two tabs + the Compile-check button. Start here. |
| `build_exe.py` | PyInstaller wrapper that produces `dist/GothicStudio.exe`. |
| `selftest.py` | Headless end-to-end check: drives every widget, then compiles with gdc. |
| `project.py` | **Every path and the encoding.** Change this if you move the tool. |
| `gamedata.py` | Scrapes `Content/` for real identifiers. `python gamedata.py` prints what it found. |
| `labels.py` | Readable names for constants (`GIL_MIL` -> "Militia"). Presentation only. |
| `textures.py` | Reads Gothic's ZTEX/DXT textures and the `.vdf` archives. `python textures.py` self-checks. |
| `texture_view.py` | Turns those into the preview panels. |
| `mesh.py` | Reads compiled meshes (.MRM/.MMB/.MDM) and the skeleton (.MDH). `python mesh.py` self-checks. |
| `render3d.py` | Software rasteriser for the character preview - no OpenGL. |
| `model_view.py` | The draggable 3D panel on the NPC page. |
| `fastpath.py` | Optional numpy acceleration. Absent numpy, everything still works. |
| `benchmark.py` | Proves whether numpy actually helps, stage by stage. |
| `theme.py` | All colours, fonts, sizes. Nothing else hardcodes a colour. |
| `npc_model.py` | The `Npc` object - one flat list of fields. |
| `npc_gen.py` | `Npc` -> `.d` text, plus `validate()`. |
| `npc_page.py` | The NPC tab. |
| `npc_tabs/*.py` | One file per form tab. Each exposes `build(parent, npc, handlers)`. |
| `npc_handlers.py` | The 2-method glue between widgets and the model. |
| `ui.py` | **The component set.** Every button, field, label and layout comes from here. |
| `dialog_gen.py` | Dialog data model, code generation, and the `.d` parser. |
| `dialog_page.py` | The Dialog tab. |
| `dialog_widgets.py` | The chat-bubble editor widgets. |

## UI components

`ui.py` is the only module that writes a stylesheet. Everything else builds
screens out of it, so the app looks the same everywhere and a theme change is
one edit.

```python
import ui

ui.section(layout, "Combat")                       # titled group + divider
ui.field(layout, "Fight tactic", ui.dropdown(...)) # label above control
ui.field(layout, "Level", ui.slider(1, 100, ...))  # slider shows its value
ui.field_row(layout, "Starts at", ui.spin(...))    # label beside control
layout.addWidget(ui.checkbox("Immortal", ...))
layout.addWidget(ui.radio_row("1H weapon", LEVELS, ...))
row.addWidget(ui.button("Save to mod", self._save, ui.PRIMARY))
```

| | |
|---|---|
| **Text** | `heading` `label` `hint` `value_label` `panel_header` `placeholder` |
| **Inputs** | `text_input` `dropdown` `search_dropdown` `search_input` `number` `choice` `checkbox` `radio_row` `toggle_row` `slider` |
| **Lists** | `listbox` `tree` |
| **Buttons** | `button(text, on_click, variant)` - `PRIMARY` `DEFAULT` `SUBTLE` `DANGER`; `icon_button` |
| **Layout** | `row` `column` `section` `field` `field_group` `divider` `toolbar` |
| **Page frame** | `SidePanel` (preview tabs + status + actions), `page(work, side)` |

**Dropdowns drop downwards.** `combobox-popup: 0` is set on every combo. Without
it Qt shows the list as a menu centred on the current item, so as soon as the
selection is not the first entry the list is drawn straight over the field.
With it off the list appears below and scrolls at `POPUP_ITEMS` rows.

**One alignment grid.** `field()` puts every label in the same left column
(`LABEL_W`) and every control at the same x, so a form reads as a grid rather
than a ragged edge. Controls that set their own width keep it; the rest fill
the row. Use `field_group()` when several short values belong on one line -
Name / ID / Level are one thought, not three rows.

**Pick the control that matches the data.** This is the rule that gets broken
quietly, so it is worth spelling out:

| The value is | Use | Not |
|---|---|---|
| an exact number you look up (attributes, level, id) | `number` | a slider - you cannot hit 123 by dragging |
| a handful of named states (chapter, magic circle) | `choice` | a slider over 0-6 |
| two or three exclusive options (gender, talent rank) | `toggle_row` / `radio_row` | a dropdown that hides half the choice |
| one of a long list (faces, routines, waypoints) | `search_dropdown` / `search_input` | a plain dropdown you must scroll |
| a genuinely continuous thing judged by eye (build) | `slider` | |

Exactly one slider survives in the app - the fatness dial on the Visual tab,
where you drag and watch the model change. Everything else that was a slider
is now a number or a list.

Three rules:

1. **No stylesheets outside `ui.py`.** Need a new look? Add a variant there.
2. **One control, one call.** Each takes its value and its callback, so wiring
   reads the same everywhere.
3. **Words, not just glyphs.** A tooltip is not discoverable; every button
   carries a label.

Both pages are the same shape: what you edit on the left, `SidePanel` on the
right with preview tabs, a status line, and Validate / Save as / Save to mod in
the same corner. Use `ui.page(work_area, side_panel)` and they stay that way.

Before this existed the app had 11 different `QLabel` styles, 5 button styles,
5 font sizes and 4 button heights. It now has one definition per role, and
containers are separated by tone and spacing rather than outlines.

## Adding things

**A new field on the NPC** - add it to `npc_model.py`, emit it in
`npc_gen.build_npc()`, add a widget in the relevant `npc_tabs/*_tab.py`. Three
edits, all obvious.

**A new dialog effect** (give item, set routine, ...) - add a branch in
`dialog_gen._entry_lines()` and a matching regex near `_LINE_RE` if you want it
to parse back. The UI row is in `dialog_widgets.EffectInsertRow`.

**A new picker list** - add a function to `gamedata.py`. Copy any existing one;
they are all 3 lines.

## Performance

The 3D preview is pure Python by default and uses numpy where numpy actually
wins. `python benchmark.py` measures both paths in separate processes and
checks they produce an identical image:

```
stage                      pure python       numpy    speed-up
--------------------------------------------------------------
decode 512x512 DXT              83.3ms       7.7ms       10.8x
decode 256x128 DXT               9.9ms       1.1ms        8.7x
render 160x230                  24.2ms      23.6ms        1.0x   (pure path chosen)
render 320x460                  63.1ms      59.4ms        1.1x
render 640x920                 215.5ms      84.5ms        2.5x
cold frame (both)              157.9ms      70.0ms        2.3x

identical output: yes
```

So the app does both:

* **texture decoding always uses numpy** when installed - it is bulk per-pixel
  work and ~10x faster;
* **rasterising switches on frame size.** numpy pays its per-call overhead
  ~1300 times a frame, so its cost is nearly flat while pure Python grows
  linearly. They cross at about 125k pixels
  (`render3d.RASTER_NUMPY_MIN_PIXELS`). Dragging deliberately renders small
  frames, which is exactly where pure Python is faster.

Re-run the benchmark if you touch the renderer; the threshold is measured, not
guessed.

## Validate and Compile check

- **Validate** (on both tabs) - checks every identifier against `gamedata`.
  Instant, catches typos before you save.
- **Compile check** (status bar) - runs `gdc` over the whole mod, same as the
  VS Code "compile check" task. Takes ~3 seconds.

## Known limits

- The dialog `.d` parser is regex-based. It round-trips files this tool wrote
  and simple vanilla ones; it is not a general Daedalus parser.
- `B_SetAttributesToChapter` (Stats tab) overwrites `level`. That is the
  engine's behaviour, not a bug here - the checkbox says so.
- Waypoints come from `.check/worldnames.json`. If that file is missing the
  waypoint field is a free-text box instead of a searchable list.
