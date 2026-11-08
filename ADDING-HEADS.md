# Adding a new head

How to make a new head model available in the appearance creator and Gothic
Studio. Replace `HUM_HEAD_X` with your head's name.

`make_head.py` in the `Gothic-Mod` folder already does these steps for you, so
you only need them to add a head by hand.

## Appearance creator

1. Open `Gothic II/_work/Data/Scripts/Content/Story/Appearance/MOD_Appearance.d`.
   Keep the file's cp1250 encoding when you save it.
2. Add one to the head count:
   ```
   const int MOD_APPEARANCE_HEAD_COUNT		= 15;
   ```
3. In `MOD_Appearance_GetHeadMesh`, add a row after the last head, using the old
   count as its number:
   ```
   if (idx == 14)	{ return "HUM_HEAD_X";	};
   ```
4. Run `gothic build`.

## Gothic Studio

1. Open `gothic-studio/labels.py`.
2. In the `HEAD` table, add this line above `"HUM_HEAD_BABE"`, with the name you
   want shown:
   ```python
   "HUM_HEAD_X": "Your name",
   ```
3. Restart Studio. A built `.app` or `.exe` needs a rebuild instead.
4. Check that the head has been compiled, because Studio can't preview it until
   then. Select it once in the appearance creator in game, which creates
   `_work/Data/Anims/_compiled/HUM_HEAD_X.MMB`.

Studio finds the head by reading your scripts, so it only appears in the dropdown
once it's in `MOD_Appearance.d` or another script, and has its label.
