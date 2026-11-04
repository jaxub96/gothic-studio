"""
selftest.py - build the whole app headless, drive every widget, and compile
the generated .d files with the real gdc.

    python selftest.py

Writes temp files into Content/ (.devmod/ with no mod) and deletes them again.
Without a Gothic II install it runs only the checks that need no game data. Exits non-zero
if anything fails, so it works as a pre-commit check too.
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("GOTHIC_STUDIO_DEV", "1")   # no mod: write into .devmod/
os.environ.setdefault("GOTHIC_STUDIO_DEV", "1")   # no mod: write into .devmod/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (QApplication, QComboBox, QLineEdit,
                             QRadioButton, QSlider, QTreeWidget)

import dialog_gen
import gamedata
import labels
import npc_gen
import project
import studio

fails = []
HAVE_MOD = project.FOUND and not project.DEV_FIXTURE


def check(condition, message):
    if not condition:
        fails.append(message)
    print(("  ok   " if condition else "  FAIL ") + message)


def main():
    # Keep the reference: if the QApplication is garbage-collected the whole
    # process dies with no traceback and exit code 127.
    app = QApplication([])  # noqa: F841
    studio._load_pages()
    win = studio.Studio()
    if not HAVE_MOD:
        print("no Gothic II found: running the mod-independent checks only")
    npc = win.npc.npc
    print("built Studio window")

    # ---------------------------------------------------------- game data
    print("\ngamedata (scraped from Content/):")
    for fn in (gamedata.items, gamedata.armors, gamedata.guilds, gamedata.npctypes,
               gamedata.tactics, gamedata.routines, gamedata.heads,
               gamedata.overlays, gamedata.npc_instances, gamedata.waypoints):
        print(f"  {fn.__name__:16} {len(fn())}")
    if HAVE_MOD:
        check(len(gamedata.items()) > 100, "item list is populated")
        check("GIL_STT" not in gamedata.guilds(), "no Gothic 1 guilds leaked in")
        check(all(not t.endswith(".d") for t in gamedata.tactics()),
              "fight tactics carry no .d suffix")
        check("TA_Position" not in gamedata.routines(),
              "TA_Position (which does not exist) is not offered")
        check(not gamedata.unknown("item", "ItMw_1H_Mil_Sword"),
              "vanilla items in Items/_base are offered")
        check(len(gamedata.armors()) > 20, "vanilla armors in Items/_base are offered")
        check(gamedata.unknown("item", "ItMw_2H_Axe_L_03"),
              "items inside a /* */ comment block are not offered")
        check(len(gamedata.info_instances()) > 50, "dialog instances are found for Npc_KnowsInfo")

    import daedalus_read
    src = 'a; // c "x"\n/* old\ninstance X (C_Item) */\nname = "http://y /* z";\n'
    out = daedalus_read.strip_comments(src)
    check(out.count("\n") == src.count("\n") and "C_Item" not in out and '"http://y /* z"' in out,
          "comment skipping keeps strings and line numbers, drops /* */ and // text")

    # ---------------------------------------------------------- NPC widgets
    print("\ndriving every NPC widget:")
    tabs = win.npc.tabs
    for i in range(tabs.count()):
        page = tabs.widget(i)
        for c in page.findChildren(QComboBox):
            if c.count() > 1:
                c.setCurrentIndex(c.count() - 1)
        for s in page.findChildren(QSlider):
            s.setValue((s.minimum() + s.maximum()) // 2)
        for r in page.findChildren(QRadioButton):
            if r.text() == "Master":
                r.setChecked(True)
    check(not str(npc.fight).endswith(".d"), "fight_tactic has no .d suffix")
    check((npc.t1h, npc.t2h, npc.bow, npc.cbow) == (2, 2, 2, 2),
          "talent radios reach the model")

    if HAVE_MOD:
        inv = tabs.widget([tabs.tabText(i) for i in range(tabs.count())].index("Inventory"))
        armor = [c for c in inv.findChildren(QComboBox) if c.findText("(no armor)") >= 0][0]
        armor.setCurrentIndex(1)
        check(str(npc.armor).upper().startswith("ITAR_"), "armor dropdown yields an ITAR_ id")

        search = [w for w in inv.findChildren(QLineEdit)
                  if (w.placeholderText() or "").startswith("Search")][0]
        first_item = next(iter(gamedata.items()))
        search.setText(first_item)
        search.returnPressed.emit()
        check(bool(npc.inv_items), "item search adds to the inventory")

    npc.name, npc.id = "Selftest", "877"
    if HAVE_MOD:
        npc.waypoint = gamedata.waypoints()[0] if gamedata.waypoints() else ""
        win.npc.refresh()
        problems = npc_gen.validate(npc)
        check(not problems, f"NPC validates clean ({problems})")

    if HAVE_MOD:
        # ---------------------------------------------------------- previews
        print("\ntexture previews:")
        import texture_view
        import textures

        face_values = gamedata.face_values()
        missing = [n for n, v in face_values.items() if not textures.face_texture(v)]
        check(not missing, f"every face constant resolves to a texture "
                           f"({len(face_values) - len(missing)}/{len(face_values)})")

        decoded = textures.decode(textures.face_texture(0))
        check(decoded is not None and decoded[0] > 0 and len(decoded[2]) == decoded[0] * decoded[1] * 3,
              "a face texture decodes to a full RGB buffer")

        pm = texture_view.pixmap(textures.face_texture(4), texture_view.FACE_CROP, 128)
        check(pm is not None and not pm.isNull() and pm.height() == 128,
              "the face preview produces a real pixmap")

        body_missing = [n for n, v in gamedata.body_texture_values().items()
                        if not textures.body_texture(v)]
        check(len(body_missing) < len(gamedata.body_texture_values()),
              f"body textures resolve ({len(gamedata.body_texture_values()) - len(body_missing)}"
              f"/{len(gamedata.body_texture_values())})")

        hit, total = textures.coverage()
        check(hit >= total * 0.85,
              f"armor previews resolve for most armors ({hit}/{total})")
        check(textures.armor_texture("ITAR_PAL_H") is not None,
              "armor resolves through mesh -> material -> texture (ITAR_PAL_H)")
        check(textures.decode(textures.armor_texture("ITAR_PAL_H")) is not None,
              "the resolved armor texture decodes")

        # ---------------------------------------------------------- 3D preview
        print("\n3D character preview:")
        import mesh
        import render3d

        bones = mesh.skeleton()
        check("BIP01 HEAD" in bones and len(bones) > 20,
              f"skeleton parses ({len(bones)} bones)")

        body = mesh.load("HUM_BODY_NAKED0.MDM")
        check(body is not None and 150 < (body.bounds()[1][1] - body.bounds()[0][1]) < 200,
              "body mesh loads at human scale "
              f"({body.bounds()[1][1] - body.bounds()[0][1]:.0f} units tall)" if body else "no body")

        head = mesh.head_mesh("HUM_HEAD_PONY")
        check(head is not None and head.triangles, "head mesh loads")

        bad = 0
        for m in (body, head):
            if m:
                bad += sum(1 for t in m.triangles for w in t if w[0] >= len(m.positions))
        check(bad == 0, "every triangle indexes a real vertex")

        models = render3d.character(npc)
        check(len(models) >= 2, f"character assembles body + head ({len(models)} parts)")
        check(all(m.texture for m in models), "every part found its texture")

        # The head must sit INSIDE the shoulders, not hover above them. This is the
        # regression guard for two real bugs: a vertical shift derived from the neck
        # instead of the feet, and reading only the first mesh in an armor file so
        # the neck skin went missing.
        placement = mesh.head_placement()
        head_underside = min(
            mesh.transform_point(placement, p)[1] for p in head.positions
            if abs(p[0]) < 30 and abs(p[2]) < 30)
        detached = []
        for armor in ("-1", "ITAR_PAL_H", "ITAR_KDF_H", "ITAR_MIL_M", "ITAR_Bau_L",
                      "ITAR_NOV_L", "ITAR_Diego", "ITAR_KDW_H"):
            parts = mesh.body_meshes(None if armor == "-1" else armor)
            collar = max((p[1] for part in parts for p in part.positions
                          if abs(p[0]) < 6 and abs(p[2]) < 6), default=-1e9)
            if collar < head_underside:
                detached.append(f"{armor} ({collar:.0f} < {head_underside:.0f})")
        check(not detached, f"head meets the neck on every armor{'' if not detached else ': ' + ', '.join(detached)}")

        # ...and every body must share the naked body's frame, front to back too.
        # Armor files store positions that are NOT in that frame (they sit up to
        # ~15 units behind), so mesh.py skins them from their bone weights; if
        # that regresses, the head floats in front of the collar from the side.
        def frame(parts):
            ps = [p for part in parts for p in part.positions]
            return (min(p[1] for p in ps), (min(p[2] for p in ps) + max(p[2] for p in ps)) / 2)

        floor0, mid0 = frame(mesh.body_meshes(None))
        drifted = []
        for armor in gamedata.armors():
            parts = mesh.body_meshes(armor)
            if not parts:
                continue
            floor, mid = frame(parts)
            if abs(floor - floor0) > 4 or abs(mid - mid0) > 8:
                drifted.append(f"{armor} (floor {floor - floor0:+.1f}, depth {mid - mid0:+.1f})")
        check(not drifted, "every armor sits in the naked body's frame"
              + ("" if not drifted else ": " + ", ".join(drifted[:5])))

        head_bone = mesh.skeleton()["BIP01 HEAD"]
        check(tuple(placement) == tuple(head_bone),
              "head is placed by the head bone alone, with no fitted offset")

        multi = mesh.load_all("ARMOR_KDF_H.MDM")
        check(len(multi) > 1, f"multi-part armor files are fully read ({len(multi)} meshes)")
        check(any(sub.is_skin for part in multi for sub in part.submeshes),
              "armor skin submesh is found (this is what fills the neck)")

        import time as _time
        BG = (0, 0, 0)
        t0 = _time.time()
        img = render3d.render(models, 200, 300, background=BG)
        elapsed = _time.time() - t0
        check(img is not None and len(img[2]) == 200 * 300 * 3,
              f"renders a full frame in {elapsed:.2f}s")
        if img:
            # A blank render would be entirely background; confirm we drew something.
            px = img[2]
            painted = sum(1 for i in range(0, len(px) - 3, 3 * 37)
                          if px[i:i + 3] != bytes(BG))
            check(painted > 50, f"the frame contains geometry ({painted} sampled pixels)")

        check(win.npc.model_view.canvas.pixmap() is not None,
              "the 3D panel is wired into the NPC page")

    # ---------------------------------------------------------- labels
    print("\nreadable labels:")
    check(labels.raw(labels.pretty(labels.GUILD, "GIL_MIL")) == "GIL_MIL",
          "label round-trips back to the raw constant")
    check(labels.pretty(labels.GUILD, "GIL_MIL").startswith("Militia"),
          "guild shows a readable name")
    check(labels.pretty(labels.GUILD, "GIL_MADEUP") == "GIL_MADEUP",
          "an unknown constant falls back to showing itself")

    # ---------------------------------------------------------- the link
    if HAVE_MOD:
        check(win.dialog.npc_id_edit.currentText() == npc_gen.instance_name(npc),
              "NPC tab feeds its instance name to the Dialog tab")
    npc.name = "Linked"
    win.npc.refresh()
    check(win.dialog.npc_name_edit.text() == "Linked",
          "NPC tab feeds its display name to the Dialog tab")

    # Female faces and skins have no script constant: they are written as their
    # number and read back, and switching gender swaps every dependent list.
    saved = (npc.face, npc.body_tex, npc.gender, npc.head, npc.voice, npc.overlay)
    npc.gender = "FEMALE"
    win.npc.refresh()
    check(npc.head in gamedata.heads_for("FEMALE") and npc.face in gamedata.faces_for("FEMALE")
          and npc.body_tex in gamedata.body_textures_for("FEMALE"),
          f"switching to female picks a female head, face and skin "
          f"({npc.head}, {npc.face}, {npc.body_tex})")
    check(npc.overlay == gamedata.FEMALE_WALK and int(npc.voice) in gamedata.FEMALE_VOICES,
          f"...the female walk and a female voice ({npc.overlay}, voice {npc.voice})")
    text = npc_gen.build_npc(npc)
    face_n, body_n = gamedata.face_code(npc.face), gamedata.body_code(npc.body_tex)
    check(f", {face_n}, {body_n}, " in text and "Babe_" not in text.split("B_SetNpcVisual")[1].split(";")[0],
          f"female face and skin are emitted as numbers ({npc.face} -> {face_n}, {npc.body_tex} -> {body_n})")
    back = npc_gen.parse_npc(text)
    check(back.face == npc.face and back.body_tex == npc.body_tex,
          "female face and skin are read back from the numbers")
    npc.gender = "MALE"
    npc.armor = "ITAR_VLK_M"
    win.npc.refresh()
    npc.gender = "FEMALE"
    win.npc.refresh()
    check(npc.armor == "-1", "a male armor is dropped when switching to female")
    npc.armor = "ITAR_VlkBabe_M"
    npc.gender = "MALE"
    win.npc.refresh()
    check(npc.armor == "-1", "a female armor is dropped when switching back to male")
    check(all(gamedata.is_female_armor(a) for g in gamedata.armors_by_guild("FEMALE").values() for a, _ in g)
          and not any(gamedata.is_female_armor(a) for g in gamedata.armors_by_guild("MALE").values() for a, _ in g),
          "armor lists are split by gender")
    check(npc.head in gamedata.heads_for("MALE") and npc.overlay != gamedata.FEMALE_WALK
          and int(npc.voice) not in gamedata.FEMALE_VOICES,
          "switching back to male restores male head, walk and voice")
    check("HUMANS_FLEE.MDS" not in gamedata.overlays() and "HUMANS_SWIM.MDS" not in gamedata.overlays(),
          "walk styles exclude flee/sprint/swim/torch/skeleton sets")
    npc.face, npc.body_tex, npc.gender, npc.head, npc.voice, npc.overlay = saved
    win.npc.refresh()

    # ---------------------------------------------------------- routines
    print("\nday/night routine:")
    npc.split_routine = False
    one = npc_gen.routine_lines(npc)
    npc.split_routine = True
    npc.routine = "TA_Smith_Anvil"
    npc.night_routine = "TA_Sleep"
    npc.night_waypoint = "WP_INTRO_FALL3"
    two = npc_gen.routine_lines(npc)
    check(len(one) == 1 and len(two) == 2,
          "one shift by default, two when a night routine is set")
    check("TA_Smith_Anvil" in two[0] and "TA_Sleep" in two[1],
          "day and night routines are emitted separately")
    npc.split_routine = False
    npc.routine = "TA_Stand_WP"

    # ---------------------------------------------------------- Dialog page
    print("\ndialog generation:")
    dlg = win.dialog
    dlg.npc_name_edit.setText("Arideus")
    dlg.npc_id_edit.setCurrentText("GRD_001_ARIDEUS")
    b, ed = dlg._add_block()
    b.name = "SELFTEST"
    b.entries = [
        dialog_gen.DialogLine("self", "Witaj."),
        dialog_gen.DialogLine("other", "Hej."),
        dialog_gen.EffectEntry("give_item", item="ItMi_Gold", count=5),
        dialog_gen.EffectEntry("give_xp", xp="100"),
        dialog_gen.EffectEntry("log", log_topic="TOPIC_ZZSELFTEST",
                               log_status="LOG_RUNNING", log_entry="Wpis."),
        dialog_gen.EffectEntry("follow"),
    ]
    ed.load_block(b)

    before = len(dlg.blocks)
    ed._add_choice()
    check(len(dlg.blocks) == before + 1, "a choice spawns a follow-up scene")

    text = dlg._dia_text()
    check("B_GivePlayerXP" in text and "B_GiveXP(" not in text,
          "emits B_GivePlayerXP, not B_GiveXP")
    check("ZS_Follow_Player" in text and "ZS_FOLLOW," not in text,
          "emits ZS_Follow_Player, not ZS_FOLLOW")
    if HAVE_MOD:
        check("DIA_GRD_001_ARIDEUS_EXIT" not in text,
              "suppresses a duplicate EXIT block")

    # a condition may name a sibling scene by its short name; the export must use the instance
    b2, ed2 = dlg._add_block()
    b2.name = "SELFTEST2"
    b2.condition_expr = "if (Npc_KnowsInfo (other, SELFTEST)) { return TRUE; };"
    b2.entries = [dialog_gen.DialogLine("self", "Dalej.")]
    ed2.load_block(b2)
    text = dlg._dia_text()
    check("Npc_KnowsInfo (other, DIA_GRD_001_ARIDEUS_SELFTEST)" in text,
          "a sibling scene name in a condition exports as its DIA_ instance")
    check(not any("condition names" in p for p in dlg._problems()),
          "a sibling scene name in a condition validates")
    b2.condition_expr = "if (Npc_KnowsInfo (other, NoSuchScene)) { return TRUE; };"
    ed2.load_block(b2)
    check(any("NoSuchScene" in p for p in dlg._problems()),
          "an unknown dialog name in a condition is reported")
    b2.condition_expr = "if (Npc_KnowsInfo (other, SELFTEST)) { return TRUE; };"
    ed2.load_block(b2)
    text = dlg._dia_text()

    # ---------------------------------------------------------- round-trip
    existing = project.DIA_DIR / "DIA_GRD_001_Arideus.d"
    if existing.exists():
        _, nid, blocks = dialog_gen.parse_dia_file(project.read_script(existing))
        spoken = sum(len(bl.lines()) for bl in blocks)
        xp = [e for bl in blocks for e in bl.entries
              if getattr(e, "kind", "") == "give_xp"]
        check(spoken > 0, f"round-trips the mod's own dialog file ({spoken} lines)")
        check(bool(xp), "parses B_GivePlayerXP back into an XP effect")

    # ---------------------------------------------------------- compile
    if HAVE_MOD:
        print("\ncompiling with gdc:")
        npc_path = project.NPC_DIR / "ZZ_SELFTEST.d"
        dia_path = project.DIA_DIR / "DIA_ZZSELFTEST.d"
        log_path = project.LOG_DIR / "LOG_Constants_ZZSELFTEST.d"
        consts = dialog_gen.generate_constants_file(
            "GRD_001_ARIDEUS", dlg._collect_blocks(), tuple(gamedata.log_topics()))
        try:
            project.write_script(npc_path, npc_gen.build_npc(npc))
            project.write_script(dia_path, text)
            if consts:
                project.write_script(log_path, consts)

            raw = npc_path.read_bytes()
            check(b"\xef\xbb\xbf" not in raw[:3], "no UTF-8 BOM")

            ok, errors = project.compile_check()
            check(ok, "the whole mod compiles with the generated files in place")
            for e in errors[:12]:
                print("     ", e)
        finally:
            for p in (npc_path, dia_path, log_path):
                p.unlink(missing_ok=True)
            print("  temp files removed")

    # CP1250 round-trip on a Polish string
    npc_path = project.NPC_DIR / "ZZ_SELFTEST.d"
    project.write_script(npc_path, 'name = "Cześć";')
    raw = npc_path.read_bytes()
    npc_path.unlink()
    check(b"\x9c\xe6" in raw, f"writes CP1250, not UTF-8 ({raw!r})")

    print("\n" + ("SELFTEST PASSED" if not fails else "SELFTEST FAILED:"))
    for f in fails:
        print("  -", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
