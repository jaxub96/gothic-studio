# The mod's script package

Your mod's own scripts: guilds, shared constants, items, quest topics, and
three sample NPCs with dialogs. Everything here is **new files** that sit on
top of a vanilla Gothic II (NotR) script tree. Nothing vanilla is replaced.

The sample content is a small harbour-town setting modelled on Gothic II:
values, layouts and naming follow vanilla, so what you copy from here
behaves like the original game.

## Install

```bash
python mod/install.py
```

That installs into the mod Gothic Studio is using. To pick a folder yourself,
pass it: `python mod/install.py "C:\...\Data\Scripts"`. Add `--dry-run` to see
what would change without changing anything. Then run **Compile check** in
Gothic Studio.

You can run it as often as you like. What it does:

1. Copies `mod/Content/**` into `Scripts/Content/` as CP1250 with CRLF line
   endings, which is what the engine reads. If a file is already there and
   differs, it is **kept** and reported. `--force` overwrites it.
2. Adds four lines to `Content/Gothic.src`. Vanilla already picks up
   `Story/NPC`, `Story/Dialoge/DIA*` and `Story/Log_Entries`, but not `Mod/`:

   ```
   _INTERN\CONSTANTS.D
   MOD\MOD_GUILDS.D             <- added
   MOD\MOD_CONSTANTS.D          <- added
   ...
   MOD\ITEMS\*.D                <- added
   MOD\MOD_GUILD_ATTITUDES.D    <- added
   STORY\NPC\*.D
   ```

3. Adds `B_Mod_InitGuildAttitudes ();` after every `B_InitGuildAttitudes ();`
   in `Story/Startup.d`.

The first time it changes `Gothic.src` or `Startup.d`, it saves the original
as a `.bak` file next to it.

**Choose one place to edit.** If you edit these files here and reinstall, use
`--force` so your changes overwrite the old copies. If you edit them inside the
mod instead (in Gothic Studio, for example), stop reinstalling, or the installer
will keep reporting that the files differ.

## What is where

| File | What it holds |
|---|---|
| `Content/Mod/Mod_Guilds.d` | **Your guilds.** Each one gives a name of your own to one of the engine's guild slots. Read this first. |
| `Content/Mod/Mod_Guild_Attitudes.d` | Who attacks whom: `B_Mod_InitGuildAttitudes()` |
| `Content/Mod/Mod_Constants.d` | NPC id range, XP rewards, guild entry requirements, prices, teaching costs, reputation and quest-state vars |
| `Content/Mod/Items/Mod_Items.d` | One example of each item kind (weapon, armor, food, potion, quest item), with the balance numbers as constants at the top |
| `Content/Story/Log_Entries/LOG_Constants_Mod.d` | Quest titles in the journal (`TOPIC_Mod_*`) |
| `Content/Story/NPC/*_9xxx_*.d` | Brannoc (City Watch sergeant), Ysolde (a hunter), Varn (a corsair trader) |
| `Content/Story/Dialoge/DIA_*_9xxx_*.d` | Their dialogs |
| `install.py` | The installer |

### The sample quest, end to end

1. **Brannoc** greets you (`Hello`, important) and gives you *The Lost Orders*
   (`MIS_Mod_LostOrders = LOG_RUNNING`).
2. **Ysolde** has an extra dialog option while that quest is running. She found
   the dead courier, and `Pay` hands over `ItMi_Mod_SealedOrders` for
   `MOD_INFORMANT_FEE` gold.
3. Bring the orders back to **Brannoc** (`OrdersDone`) for gold,
   `XP_Mod_QuestMedium` and `Mod_Rep_Watch + 5`.
4. Once you are level `MOD_WATCH_MIN_LEVEL` and the quest is done, `Join` makes
   you `GIL_WATCH` and gives you `ITAR_Mod_Watch_L`. Asking any earlier gets
   `JoinNotYet`.

**Varn** shows the simplest trader: one introduction scene and a `trade = 1`
scene.

## Guilds: how they work in Gothic II

The engine has **16 human guild slots** (0 to 15). Vanilla already uses all of
them, and vanilla scripts refer to them by name throughout (crime, guild
armors, attitudes, and so on). So a mod doesn't add guilds. It **takes over a
slot**:

```daedalus
const int GIL_WATCH = GIL_MIL;   // City Watch - the harbour town's guards; joinable
```

Your scripts use `GIL_WATCH`. Vanilla's code keeps using `GIL_MIL`, and both
mean slot 2, so everything still compiles and the vanilla behaviour for that
slot still applies.

- **To rename a guild:** change the alias and the comment. Gothic Studio's guild
  picker shows the text after `//` up to ` - ` (here, "City Watch"), and new
  NPCs are named after the alias (`WATCH_9001_...`).
- **What the player sees** on the status screen comes from `TXT_GUILDS` in
  vanilla's `Text.d`. Rename the guild there too.
- **To free a slot:** pick a vanilla guild your mod doesn't use and alias it to
  something new. Search the vanilla scripts for the old name to see which
  behaviour still comes with that slot.
- **Attitudes:** add lines to `B_Mod_InitGuildAttitudes()`. Use
  `B_Mod_SetMutualAttitude` when the feeling goes both ways.

## Writing new content

- **New NPC.** Create it in Gothic Studio, or copy a sample. Keep ids between
  `MOD_NPC_ID_FIRST` and `MOD_NPC_ID_LAST` (9000 to 9999) so they never clash
  with vanilla's. Name the file `<GUILD>_<id>_<Name>.d`.
- **New dialog.** The file name must start with `DIA`. Vanilla's `Gothic.src`
  only picks up `STORY\DIALOGE\DIA*.D`. Gothic Studio opens the samples and
  writes new dialogs in the same shape.
- **New quest.** Add a `TOPIC_Mod_*` to `LOG_Constants_Mod.d` and a `MIS_Mod_*`
  var to `Mod_Constants.d`. Then follow the Brannoc/Ysolde pattern: set the
  var when the quest starts, check it in other NPCs' conditions, and set it to
  `LOG_SUCCESS` at the end.
- **New item.** Copy the closest one in `Mod_Items.d`, put its numbers in
  constants at the top, and give it a vanilla visual or a new one. Armors named
  `ITAR_<tag>_<weight>` are grouped by tag in the studio's armor tree.
- **New XP reward or price.** Add a constant to `Mod_Constants.d`. Gothic
  Studio offers every `XP_*` constant it finds.

## Things to check against your install

- **Waypoints** in the routines (`NW_CITY_ENTRANCE_01`, ...) are Khorinis
  (NewWorld) names. Gothic Studio's **Validate** checks them against your
  worlds, and the Routine tab lets you pick real ones.
- The NPCs aren't placed in any world yet. Tick *Put this NPC into the world*
  on the Routine tab, or add `Wld_InsertNpc` lines to `Startup.d`.
- Item **visuals** are borrowed from vanilla. If one shows up as nothing in the
  game, copy the `visual` line from the vanilla item it imitates.
- Text is plain ASCII, so it is safe in any code page. Once you add Polish
  characters, edit the installed (CP1250) copies, or keep these files in
  CP1250 too.
