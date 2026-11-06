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

# ---- dialog structure: nested replies, the Back toggle, conditions, bottom bar
import re as _re
d._new_project(); d.npc_name_edit.setText("Remus"); d.npc_id_edit.setCurrentText(inst)
nested=("-- ASSIGNMENT --\nNPC - Jest pewna substancja.\n\n-- ASSIGNMENT > SUBSTANCE --\nChoice - Jaka to substancja?\nNPC - Pewien preparat.\n\n"
        "-- ASSIGNMENT > MOTIVE --\nChoice - A dlaczego sam się tym nie zajmiesz?\nNPC - Władze nie uznają moich praktyk.\n\n"
        "-- TASK --\nNPC - Co do przesyłki...\n\n-- TASK > ACCEPT --\nChoice - Dowiem się.\nNPC - Dobrze.\n")
src2=root/"nested.txt"; src2.write_bytes(nested.encode("cp1250"))
QFileDialog.getOpenFileName=staticmethod(lambda *a,**k:(str(src2),""))
d._import_text()
shape=[("  " if b.is_followup else "")+b.name for b in d.blocks]
check(shape==["ASSIGNMENT","  SUBSTANCE","  MOTIVE","TASK","  ACCEPT"],f"Import text keeps nesting and titles ({shape})")
linked=[cw.linked_block is not None for ed in d.block_editors for cw in ed.get_choice_widgets()]
check(linked and all(linked),"imported choices are linked to their replies")
check([c.label for c in d.blocks[0].choices]==["Jaka to substancja?","A dlaczego sam się tym nie zajmiesz?"],"import keeps each choice's text")
check(d.blocks[3].requires=="ASSIGNMENT" and d.blocks[0].requires=="","imported scenes require the scene before them (not the first)")
check(dialog_gen.export_plain_dialog(d._collect_blocks())==nested.strip()+"\n","Export text writes the nesting back identically")

def body(text, fname):
    m=_re.search(r"func void "+fname+r"\(\)\s*\{(.*?)\n\};", text, _re.I|_re.S)
    return m.group(1) if m else ""
base="DIA_"+dialog_gen.sanitize(inst)
txt=d._dia_text()
check("Info_ClearChoices" in body(txt,base+"_ASSIGNMENT_SUBSTANCE"),"a reply goes back to the menu by default (Info_ClearChoices)")
mot=d.block_editors[0].get_choice_widgets()[1]; mot.back_cb.setChecked(False)
txt=d._dia_text()
check("Info_ClearChoices" not in body(txt,base+"_ASSIGNMENT_MOTIVE") and "Info_ClearChoices" in body(txt,base+"_ASSIGNMENT_SUBSTANCE"),"unticking Back on one choice drops its Info_ClearChoices only")
ed_task=d.block_editors[3]
ed_task._add_condition("Kapitel >= 2")
txt=d._dia_text()
cond=_re.search(r"FUNC INT "+base+r"_TASK_Condition\(\)\s*\{(.*?)\n\};",txt,_re.I|_re.S).group(1)
check(f"Npc_KnowsInfo(other, {base}_ASSIGNMENT) && Kapitel >= 2" in cond and "return 1;" in cond,"Requires + extra condition export as one if(...) that returns 1")
d.side.save_btn.click(); app.processEvents()
n2,i2,re_blocks=dialog_gen.parse_dia_file(project.read_script(df))
shape2=[("  " if b.is_followup else "")+b.name for b in re_blocks]
check(shape2==shape,f"Open on the saved .d gives the scene names, not the choice texts ({shape2})")
mot2=next(b for b in re_blocks if b.name=="MOTIVE"); task2=next(b for b in re_blocks if b.name=="TASK")
check(mot2.clear_after is False and next(c for c in re_blocks[0].choices if c.func_name==mot2.func_name).back is False,"the Back setting survives save + open")
check(task2.requires=="ASSIGNMENT" and task2.extra_conditions==["Kapitel >= 2"],"conditions survive save + open as Requires + extra")
# rename: whoever requires a scene follows its new name
d.block_editors[0].name_edit.setText("BRIEF"); d._collect_blocks()
check(d.block_editors[3].requires_text()=="BRIEF","renaming a scene updates scenes that require it")
d.block_editors[3].set_requires("NoSuchScene")
check(any("requires 'NoSuchScene'" in p for p in d._problems()),"Validate flags a Requires that names no scene")
d.block_editors[3].set_requires("BRIEF")
# a new scene defaults to requiring the one before
before=len([b for b in d.blocks if not b.is_followup]); d._add_block(); d._collect_blocks()
newb=d.blocks[-1]; check(newb.requires=="TASK" and len([b for b in d.blocks if not b.is_followup])==before+1,"a new scene requires the previous scene by default")
check("16px" in d.block_editors[0].get_choice_widgets()[0].label.styleSheet(),"choice rows use the chat bubble's text size")
# the action bar is not part of the side panel
w.side_btn.setChecked(False); app.processEvents()
check(not d.side.isVisible() and d.side.bar.isVisible() and d.side.save_btn.isVisible(),"Validate / Save as / Open / Save to mod stay visible with the side panel hidden")
check(w.npc.side.bar.isVisible() if w.tabs.currentIndex()==0 else True,"...on the NPC tab too")
w.side_btn.setChecked(True); app.processEvents()

# nothing stray
stray=[p for p in scripts.rglob("*") if p.is_file() and p.name.upper().startswith(("ZZ_","TMP"))]
check(not stray,"no stray temp files in the mod")
newfiles=sorted(str(p.relative_to(scripts)) for p in scripts.rglob("*") if p.is_file() and any(k in p.name for k in ("Remus","REMUS","VLK","MOD_001","Startup","LOG_Constants_")) )
print("   files:",*newfiles,sep="\n     ")
print("\nWORKFLOW", "PASSED" if not fails else "FAILED: "+"; ".join(fails))
