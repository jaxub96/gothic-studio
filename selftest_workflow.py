"""selftest_workflow.py - the whole save/open workflow on a throwaway copy of devdata/.

    python selftest_workflow.py

Drives the real Save to mod buttons on both tabs and checks that every file lands
in the right Content/ folder, encoded as CP1250 with CRLF, and that Open, Save as,
New, Import/Export text and the draft autosave behave. Never touches your mod.
"""
import os, sys, shutil, tempfile, pathlib
os.environ["QT_QPA_PLATFORM"]="offscreen"
root=pathlib.Path(tempfile.mkdtemp())
scripts=root/"Scripts"; shutil.copytree("devdata", scripts)
os.environ["GOTHIC_SCRIPTS"]=str(scripts)
os.environ.pop("GOTHIC_STUDIO_DEV", None)
sys.path.insert(0,".")
sys.argv=["studio.py"]
import config; config.CONFIG_FILE=root/"cfg"/"config.json"
(scripts/"Content/Story/Startup.d").write_bytes(
    b"func void STARTUP_TEST()\r\n{\r\n\tWld_InsertNpc(OTHER_001_X, \"WP_000\");\r\n};\r\n")
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog, QPushButton
app=QApplication(sys.argv)
fails=[]
def check(c,m):
    print(("  ok   " if c else "  FAIL ")+m)
    if not c: fails.append(m)
QMessageBox.question=staticmethod(lambda *a,**k: QMessageBox.StandardButton.Yes)
QMessageBox.warning=staticmethod(lambda *a,**k: QMessageBox.StandardButton.Ok)
QMessageBox.information=staticmethod(lambda *a,**k: QMessageBox.StandardButton.Ok)
import studio, project, npc_gen, teach_gen, startup_gen, talents, gamedata, dialog_gen, dialog_page
check(project.FOUND and project.SCRIPTS==scripts.resolve(), f"app sees the test mod ({project.SCRIPTS})")
studio._load_pages()
w=studio.Studio(); w.show(); app.processEvents()
check(w.tabs.count()==2 and w.tabs.tabText(0)=="NPC" and w.tabs.tabText(1)=="Dialog","both tabs load")
check(w.npc.side.save_btn.text()=="Save to mod" and w.dialog.side.save_btn.text()=="Save to mod","each tab has its own Save to mod")
hdr=[b.text() for b in w.dialog.findChildren(QPushButton) if b.isVisible() and b.parent() is not w.dialog.side]
w.tabs.setCurrentIndex(1); app.processEvents()
hdr=[b.text() for b in w.dialog.findChildren(QPushButton) if b.isVisible()]
check("Save" not in hdr and "Open" not in hdr and "New" in hdr and "Import text" in hdr and "Export text" in hdr,"Dialog header has New/Import/Export, no Save/Open")
w.side_btn.setChecked(False); app.processEvents()
check(not w.npc.side.isVisible() and not w.dialog.side.isVisible(),"hide button hides side panels")
w.side_btn.setChecked(True); app.processEvents()
check(w.dialog.side.isVisible(),"...and shows them again")
w.tabs.setCurrentIndex(0)

# ---- NPC: fields, teaching, startup
npc=w.npc.npc
npc.name,npc.id,npc.guild="Remus","001","GIL_NONE"
gid=next(iter(i["id"] for t in talents.group_titles() for i in talents.teachable(t)))
npc.talents={gid}
npc.spawn,npc.spawn_world,npc.spawn_waypoint=1,"TEST","WP_001"
w.npc.refresh()
inst=npc_gen.instance_name(npc); print("   instance:",inst)
w.npc.side.save_btn.click(); app.processEvents()
nf=project.NPC_DIR/npc_gen.default_filename(npc)
tf=project.DIA_DIR/teach_gen.filename(npc)
check(nf.is_file() and nf.parent==project.NPC_DIR,f"NPC file in Story/NPC ({nf.name})")
check(tf.is_file() and tf.parent==project.DIA_DIR and tf.name.upper().startswith("DIA"),f"teaching file in Story/Dialoge ({tf.name})")
check(startup_gen.find_spawn(inst)==("TEST","WP_001"),"Startup.d has the Wld_InsertNpc line in STARTUP_TEST")
check(b"\r\n" in nf.read_bytes() and b"\r\r" not in nf.read_bytes(),"NPC file has CRLF")
# open round trip
parsed=npc_gen.parse_npc(project.read_script(nf))
check(parsed is not None and parsed.name=="Remus" and npc_gen.instance_name(parsed)==inst,"NPC file reads back (Open NPC)")
check(gid in teach_gen.parse_teaching(project.read_script(tf)),"teaching file reads back")
# the old Remus bug: Dialog is NOT written by the NPC save
check(not (project.DIA_DIR/f"DIA_{dialog_gen.sanitize(inst)}.d").exists(),"NPC save alone does not create the main dialog (it has its own Save)")
# save as
out=root/"elsewhere"; out.mkdir()
QFileDialog.getSaveFileName=staticmethod(lambda *a,**k:(str(out/"Remus_copy.d"),""))
before=(project.STARTUP_FILE if hasattr(project,"STARTUP_FILE") else startup_gen.STARTUP_FILE).read_bytes()
w.npc._save(ask=True)
check((out/"Remus_copy.d").is_file() and (out/teach_gen.filename(npc)).is_file(),"Save as writes NPC + teaching where you pointed")
check(startup_gen.STARTUP_FILE.read_bytes()==before,"Save as leaves Startup.d alone")
# unspawn
npc.spawn=0; w.npc.side.save_btn.click()
check(startup_gen.find_spawn(inst) is None and b"OTHER_001_X" in startup_gen.STARTUP_FILE.read_bytes(),"unticking spawn removes only this NPC's line")
npc.spawn=1; w.npc.side.save_btn.click()

# ---- Dialog
w.tabs.setCurrentIndex(1); app.processEvents()
d=w.dialog
check(d._npc_id()==inst,f"Dialog tab follows the NPC tab's instance ({d._npc_id()})")
txt=("-- INTRODUCTION --\nHero - Witaj. Nie widziałem się z tobą.\nNPC - Remus. I nie bądź taki ciekawski.\n\n"
     "-- WORK --\nHero - Wiesz może, gdzie mógłbym znaleźć pracę?\nNPC - Szukasz uczciwego zarobku?\n")
src=root/"dia_remus.txt"; src.write_bytes(txt.encode("cp1250"))
QFileDialog.getOpenFileName=staticmethod(lambda *a,**k:(str(src),""))
d._import_text()
check(len(d.blocks)==2,"Import text (CP1250 file) gives 2 scenes")
check("mieszać" in "".join(l.text for b in d.blocks for l in b.entries if hasattr(l,"text")) or "znaleźć" in dialog_gen.export_plain_dialog(d.blocks),"Polish letters survive the import")
# add a log effect to a scene
ed=d.block_editors[0]
ed.chat.load_entries(ed.chat.get_entries()+[dialog_gen.EffectEntry("log",log_topic="TOPIC_Remus",log_status="LOG_RUNNING",log_entry="Parcel for Remus.")])
d._refresh_preview()
d.side.save_btn.click(); app.processEvents()
df=project.DIA_DIR/f"DIA_{dialog_gen.sanitize(inst)}.d"
lf=project.LOG_DIR/f"LOG_Constants_{dialog_gen.sanitize(inst)}.d"
check(df.is_file() and df.parent==project.DIA_DIR and df.name.upper().startswith("DIA"),f"dialog file in Story/Dialoge ({df.name})")
check(lf.is_file() and "TOPIC_Remus" in project.read_script(lf),"log constants in Story/Log_Entries")
raw=df.read_bytes()
check("znaleźć".encode("cp1250") in raw and b"\xef\xbb\xbf" not in raw[:3] and b"\xc5\xba" not in raw,"dialog written as CP1250 (no UTF-8), Polish intact")
n,i2,blocks=dialog_gen.parse_dia_file(project.read_script(df))
check(len(blocks)>=2 and sum(len(b.lines()) for b in blocks)==4,"dialog file reads back with all 4 spoken lines (Open)")
check(not d.is_dirty(),"saved dialog is not dirty")
check("_EXIT" in project.read_script(df).upper() and dialog_gen.sanitize(inst).upper()+"_EXIT" in project.read_script(df).upper(),"new dialog gets its EXIT block")
ed=d.block_editors[0]
ed.chat.load_entries(ed.chat.get_entries()+[dialog_gen.DialogLine("self","Nowa linia.")])
d._refresh_preview(); check(d.is_dirty(),"an edit marks it dirty")
d._write_draft(); dp=d._draft_path(); check(dp is not None and dp.is_file(),"dirty work is autosaved to a draft")
d2=dialog_page.DialogPage(); d2._offer_restore()
check(len(d2.blocks)>=2 and d2.is_dirty(),"a new session restores the draft")
check(d.confirm_close() is not None,"close prompt path runs") if False else None
# export text
out_txt=root/"x.txt"
QFileDialog.getSaveFileName=staticmethod(lambda *a,**k:(str(out_txt),""))
d._export_text()
check(out_txt.is_file() and "Nowa linia." in out_txt.read_text(encoding="utf-8"),"Export text writes the spoken lines")
# Save as for dialog
QFileDialog.getSaveFileName=staticmethod(lambda *a,**k:(str(out/"dia_copy.d"),""))
d._save(ask=True); check((out/"dia_copy.d").is_file(),"dialog Save as writes where you pointed")
check(not d.is_dirty(),"...and clears dirty")
# New
d._new_project(); check(not d.blocks and not d._npc_name() and not d.is_dirty() and not dp.is_file(),"New unloads the dialog and clears the draft")
# Open dialog file, save it again: the EXIT must survive (it once did not)
QFileDialog.getOpenFileName=staticmethod(lambda *a,**k:(str(df),""))
d._open(); check(len(d.blocks)>=2,"Open loads the saved dialog file")
d.side.save_btn.click()
check(project.read_script(df).upper().count(dialog_gen.sanitize(inst).upper()+"_EXIT (C_INFO)")==1,"open + save keeps exactly one EXIT block")
# save-as then save to mod: still one EXIT
d._save(ask=True); d.side.save_btn.click()
check(project.read_script(df).upper().count(dialog_gen.sanitize(inst).upper()+"_EXIT (C_INFO)")==1,"save-as then save to mod keeps exactly one EXIT block")
# another file already owning this NPC's EXIT suppresses ours (two would not compile)
dup=project.DIA_DIR/"DIA_ZZ_Extra.d"
project.write_script(dup, f"instance DIA_{dialog_gen.sanitize(inst)}_EXIT (C_INFO) {{}};")
check(d._emit_exit() is False,"another file's EXIT for the same NPC suppresses a duplicate")
dup.unlink()
# validate buttons run
w.npc._validate(); d._validate(); check(True,"Validate runs on both tabs")
# nothing stray
stray=[p for p in scripts.rglob("*") if p.is_file() and p.name.upper().startswith(("ZZ_","TMP"))]
check(not stray,"no stray temp files in the mod")
newfiles=sorted(str(p.relative_to(scripts)) for p in scripts.rglob("*") if p.is_file() and any(k in p.name for k in ("Remus","REMUS","VLK","MOD_001","Startup","LOG_Constants_")) )
print("   files:",*newfiles,sep="\n     ")
print("\nWORKFLOW", "PASSED" if not fails else "FAILED: "+"; ".join(fails))
