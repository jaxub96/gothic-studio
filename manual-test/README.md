# Manual round-trip test

Checks that opening a hand-written dialog file in Studio and saving it again changes nothing
that matters. Run from source (`./run.sh`); nothing here touches your mod.

## 1. The sample file

1. Copy `DIA_VLK_900_Sample.d` somewhere outside the mod (for example your Desktop).
2. Dialog tab → side panel → **Open**, pick the copy.
3. A notes dialog should appear. It must say **`dia_sample_legacy` is kept exactly as written**
   (and nothing else about scenes). That scene is odd on purpose.
4. Check the editor:
   - Scenes **Hallo** and **Quest**; Hallo has three replies (Help, Steal, Back).
   - In Hallo: a variable bubble (`Sample_Flag = TRUE`), a call bubble (`B_Sample_Helper`).
   - In Help: a give-item bubble (gold ×50) and an XP bubble.
   - In Quest: a log bubble, a routine bubble, two call bubbles (spawn, other routine) and the
     if/else shown as plain text.
   - Quest requires **Hallo**.
5. Side panel → **Save as** to another file outside the mod (for example `Saved.d`).
6. In a terminal in the Studio folder:

       .venv/bin/python manual-test/compare.py ~/Desktop/DIA_VLK_900_Sample.d ~/Desktop/Saved.d

   Expected: every definition is "the same in meaning"; the only extra is the three `_exit`
   definitions the Studio adds when a file has none. Anything under DIFFER or MISSING is a bug.
7. Open `Saved.d` in a text editor and look for these by eye:
   - `AI_Output (self, hero, ...)` in `Help` is still **hero** (not changed to other).
   - `B_GiveInvItems (self, other, ItMi_Gold, 50)` right after `CreateInvItems`.
   - The Quest condition lists the flag, then `Npc_KnowsInfo`, then `Kapitel`, in that order.
   - `Info_ClearChoices (DIA_Sample_Pickpocket)` is still there (a shared menu is not renamed).
   - The `Steal` reply only *adds* a choice (no `Info_ClearChoices` before `Info_AddChoice`).
   - `DIA_Sample_Legacy_Run` is still `func int` and untouched.
   - Function names `DIA_Sample_Hallo_Cond` / `_Run` are unchanged (not `..._Condition` / `..._Info`).

## 2. Editing

1. Open the sample again. Rename scene **Hallo** to **Greeting**.
2. In Quest add: Give Item (any item), Set Variable (`Sample_Done` = `TRUE`), Script Call
   (`B_Attack`, args `self, other, AR_NONE, 1`).
3. Save as `Edited.d`, run `compare.py` against the original.
   Expected DIFFER only: the renamed scene's definitions (they now carry the new name, and
   Quest's condition follows it) and Quest's body. Everything else is the same.
4. In `Edited.d` the new item line must say **other**, never hero.

## 3. Your real files

For each of your own dialog files you care about (Remus, Lares, anything big):

1. **Open** it in Studio, **Save as** to the Desktop (not into the mod).
2. Run `compare.py` original saved.
3. DIFFER/MISSING should be empty. If a scene could not be reproduced, Studio said so in the
   notes dialog on open and kept it as written - those never show up as DIFFER.

Send me any file where DIFFER or MISSING is not empty.
