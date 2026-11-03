"""
dialog_gen.py — Data models plus everything that turns them into Daedalus
(.d) code, plain-text dialog exports, and back again (parsing). No Qt here.
"""

import re


def is_hero_speaker(speaker):
    return speaker == "other"

def speaker_display_name(speaker):
    return "Hero" if is_hero_speaker(speaker) else "NPC"


# ── Data models ───────────────────────────────────────────────────────────────
class DialogLine:
    def __init__(self, speaker="self", text=""):
        self.speaker = speaker   # "self" = NPC, "other" = Hero
        self.text = text

class DialogChoice:
    def __init__(self, label="", func_name=""):
        self.label = label
        self.func_name = func_name

class EffectEntry:
    """A give-item / take-item / give-xp / log-entry / routine effect, placed
    inline among a scene's DialogLines at whatever point it should fire."""
    def __init__(self, kind, **fields):
        self.kind = kind          # "give_item" | "take_item" | "give_xp" | "log" | "routine" | "follow" | "unfollow"
        self.item = fields.get("item", "")
        self.count = fields.get("count", 1)
        self.xp = fields.get("xp", "")
        self.log_topic = fields.get("log_topic", "")
        self.log_status = fields.get("log_status", "LOG_RUNNING")
        self.log_entry = fields.get("log_entry", "")
        self.routine = fields.get("routine", "")

    def summary(self):
        """Short human-readable label, used by the effect bubble in the UI."""
        if self.kind == "give_item":
            return f"Give {self.count}× {self.item}" if self.item else "Give item"
        if self.kind == "take_item":
            return f"Take {self.count}× {self.item}" if self.item else "Take item"
        if self.kind == "give_xp":
            return f"XP: {self.xp}" if self.xp else "Give XP"
        if self.kind == "log":
            parts = [self.log_topic or "Log"]
            if self.log_status: parts.append(self.log_status)
            return " · ".join(parts)
        if self.kind == "routine":
            return f"Routine: {self.routine}" if self.routine else "Change routine"
        if self.kind == "follow":
            return "NPC follows Hero"
        if self.kind == "unfollow":
            return f"Resume routine: {self.routine}" if self.routine else "Stop following"
        return self.kind


class DialogBlock:
    """A dialog scene. Either a top-level C_INFO instance, or a follow-up
    'func void' triggered by a choice in another block (is_followup=True)."""
    def __init__(self):
        self.name = ""; self.description = ""; self.nr = 1
        self.permanent = 0; self.important = 0; self.condition_expr = ""
        self.entries: list = []       # DialogLine and EffectEntry, in flow order
        self.choices: list[DialogChoice] = []
        self.stop_after = True; self.is_exit = False; self.is_trade = False

        # Follow-up (choice) scenes only:
        self.is_followup = False
        self.func_name = ""          # fixed export identifier, e.g. DIA_Gomez_Reward_ItemChoice
        self.parent_block = None     # the DialogBlock this is a choice of (runtime link, not exported)

    def lines(self):
        return [e for e in self.entries if isinstance(e, DialogLine)]


# ── Code generator ────────────────────────────────────────────────────────────
def sanitize(n): return re.sub(r'[^A-Za-z0-9_]', '_', n)

def voice_code(bname, idx, speaker):
    return f"{bname}_{'15' if speaker == 'other' else '10'}_{idx:02d}"

def _log_type(s): return "LOG_MISSION" if ("RUNNING" in s or "SUCCESS" in s) else "LOG_NOTE"

def export_block_name(npc_id, block_name):
    """The exported instance identifier for a top-level scene, e.g. DIA_KDF_405_Torrez_Hello."""
    safe = sanitize(npc_id)
    bn = sanitize(block_name) if block_name else f"DIA_{safe}_Block"
    if not bn.startswith("DIA_"): bn = f"DIA_{safe}_{bn}"
    return bn

def export_followup_name(parent_bn, block_name):
    suffix = sanitize(block_name) if block_name else "Choice"
    return f"{parent_bn}_{suffix}"


def _entry_lines(entries, bn):
    """Render a scene's entries (dialog lines + effects) in the exact order
    they appear, so effects land at the point in the conversation they were
    placed at. Voice-code indices only advance for actual spoken lines."""
    out = []
    i = 0
    for e in entries:
        if isinstance(e, DialogLine):
            sf = "other" if e.speaker == "other" else "self"
            st = "self"  if e.speaker == "other" else "other"
            out.append(f'\tAI_Output ({sf}, {st},"{voice_code(bn, i, e.speaker)}"); //{e.text}')
            i += 1
        elif e.kind == "give_item":
            if not e.item: continue
            if e.count > 1:
                out.append(f"\tCreateInvItems(self, {e.item}, {e.count});")
            else:
                out.append(f"\tCreateInvItem(self, {e.item});")
            out.append(f"\tB_GiveInvItems (self, hero, {e.item}, {e.count});")
        elif e.kind == "take_item":
            if not e.item: continue
            out.append(f"\tB_GiveInvItems(other, self, {e.item}, {e.count});")
        elif e.kind == "give_xp":
            if not e.xp: continue
            out.append(f"\tB_GivePlayerXP({e.xp});")
        elif e.kind == "log":
            if not e.log_topic: continue
            out.append(f"\tLog_CreateTopic\t({e.log_topic}, {_log_type(e.log_status)});")
            out.append(f"\tLog_SetTopicStatus\t({e.log_topic}, {e.log_status});")
            if e.log_entry:
                out.append(f'\tB_LogEntry\t({e.log_topic},"{e.log_entry}");')
        elif e.kind == "routine":
            if not e.routine: continue
            out.append(f'\tNpc_ExchangeRoutine(self, "{e.routine}");')
        elif e.kind == "follow":
            out.append('\tAI_StartState(self, ZS_Follow_Player, 0, "");')
        elif e.kind == "unfollow":
            routine = e.routine or "START"
            out.append(f'\tNpc_ExchangeRoutine(self, "{routine}");')
    return out


def _render_followup(b, all_blocks, root_bn):
    """Render one choice follow-up as a `func void` block, then its own
    children (choices made inside this follow-up), recursively."""
    children = [c for c in all_blocks if c.parent_block is b]
    out = [f"func void {b.func_name}()", "{"]
    out += _entry_lines(b.entries, b.func_name)
    if b.choices or children:
        out.append(f"\tInfo_ClearChoices\t({b.func_name});")
        for ch in b.choices:
            out.append(f'\tInfo_AddChoice\t({b.func_name},"{ch.label}",{ch.func_name});')
    if not b.choices and not children:
        out.append(f"\tInfo_ClearChoices\t({root_bn});")
    out += ["};", ""]
    for child in children:
        out += _render_followup(child, all_blocks, root_bn)
    return out


def generate_dia_file(npc_name, npc_id, blocks, emit_exit=True):
    safe = sanitize(npc_id)
    out = [f"// Dialog file for {npc_name} ({npc_id})",
           "// Generated by Gothic Dialog Generator", ""]

    en = f"DIA_{safe}_EXIT"
    exit_lines = ["// " + "="*60, "// \t\t\t\t\tEXIT", "// " + "="*60,
            f"instance {en} (C_INFO)", "{",
            f"\tnpc\t\t\t= {npc_id};", "\tnr\t\t\t= 999;",
            f"\tcondition\t= {en}_Condition;", f"\tinformation\t= {en}_Info;",
            "\tpermanent\t= 1;", "\tdescription = DIALOG_ENDE;", "};", "",
            f"FUNC int {en}_Condition()", "{", "\treturn 1;", "};", "",
            f"FUNC VOID {en}_Info()", "{", "\tAI_StopProcessInfos\t(self);", "};", ""]

    if emit_exit:
        out += exit_lines

    top_level = [b for b in blocks if not b.is_exit and not b.is_followup]
    for b in top_level:
        bn = export_block_name(npc_id, b.name)
        out += ["// " + "="*60, f"// \t\t\t{b.description or b.name}", "// " + "="*60,
                f"instance {bn} (C_INFO)", "{",
                f"\tnpc\t\t\t= {npc_id};", f"\tnr\t\t\t= {b.nr};",
                f"\tcondition\t= {bn}_Condition;", f"\tinformation\t= {bn}_Info;",
                f"\tpermanent\t= {b.permanent};"]
        if b.important: out.append("\timportant\t= 1;")
        if b.description and not b.important: out.append(f'\tdescription\t= "{b.description}";')
        if b.is_trade: out.append("\tTrade\t\t= 1;")
        out += ["};", "", f"FUNC int {bn}_Condition()", "{"]
        if b.condition_expr.strip():
            for cl in b.condition_expr.strip().splitlines(): out.append(f"\t{cl}")
        else:
            out.append("\treturn 1;")
        out += ["};", "", f"FUNC VOID {bn}_Info()", "{"]
        if b.choices: out.append(f"\tInfo_ClearChoices\t({bn});")
        out += _entry_lines(b.entries, bn)
        if b.choices:
            for ch in b.choices:
                out.append(f'\tInfo_AddChoice\t({bn},"{ch.label}",{ch.func_name});')
        if b.stop_after and not b.choices: out.append("\tAI_StopProcessInfos\t(self);")
        out += ["};", ""]

        for f in [c for c in blocks if c.parent_block is b]:
            out += _render_followup(f, blocks, root_bn=bn)

    return "\n".join(out)


def generate_constants_file(npc_id, blocks, known_topics=()):
    """Emit the log-topic constants a dialog needs.

    Gothic 2 log topics are `const string NAME = "Display text";` - NOT the
    `const int NAME = 100;` the old generator produced. A dialog that uses an
    undeclared topic does not compile, and this file used to never be written
    at all (generate_constants_file was imported but never called).

    `known_topics` are topics that already exist in Content/; they are skipped
    so we never redefine one.
    """
    known = {t.upper() for t in known_topics}
    topics = sorted({e.log_topic for b in blocks for e in b.entries
                     if not isinstance(e, DialogLine) and e.kind == "log" and e.log_topic})
    fresh = [t for t in topics if t.upper() not in known]
    if not fresh:
        return ""
    out = [f"// Log topic constants for {npc_id}",
           "// Generated by Gothic Studio. Edit the display text - it is what",
           "// the player sees as the quest title in the log.", ""]
    for t in fresh:
        label = t[6:].replace("_", " ").title() if t.upper().startswith("TOPIC_") else t
        out.append('const string ' + t + '\t= "' + label + '";')
    out.append("")
    return "\n".join(out)


def export_plain_dialog(blocks):
    """A simple 'Speaker - line' reference text, scene by scene, in reading
    order (each scene followed immediately by any choice follow-ups it has).
    Effects are skipped — this is dialog-only reference text."""
    out = []

    def walk(b):
        spoken = b.lines()
        if spoken:
            out.append(f"-- {b.name or 'Scene'} --")
            for ln in spoken:
                out.append(f"{speaker_display_name(ln.speaker)} - {ln.text}")
            out.append("")
        for c in [c for c in blocks if c.parent_block is b]:
            walk(c)

    for b in blocks:
        if b.is_exit or b.is_followup: continue
        walk(b)
    return "\n".join(out).strip() + "\n"


def parse_plain_dialog(text):
    """The inverse of export_plain_dialog(): reads a dropped-in text file of

        -- Scene Name --
        NPC - line
        Hero - line

    and turns it into a flat list of top-level DialogBlocks (dialog lines
    only — no choices/effects, since the plain format doesn't carry those).
    Lines before the first '-- Name --' header land in an 'Untitled' scene.
    """
    header_re  = re.compile(r'^--\s*(.+?)\s*--$')
    speaker_re = re.compile(r'^(NPC|Hero)\s*-\s*(.*)$', re.I)

    blocks = []
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        header_m = header_re.match(line)
        if header_m:
            current = DialogBlock()
            current.name = header_m.group(1).strip()
            blocks.append(current)
            continue
        speaker_m = speaker_re.match(line)
        if speaker_m:
            if current is None:
                current = DialogBlock()
                current.name = "Untitled"
                blocks.append(current)
            speaker = "self" if speaker_m.group(1).lower() == "npc" else "other"
            current.entries.append(DialogLine(speaker=speaker, text=speaker_m.group(2).strip()))
    return blocks


# ── Parser (round-trips files produced by this tool) ───────────────────────────
_LINE_RE   = re.compile(r'AI_Output\s*\((\w+),\s*(\w+),\s*"[^"]*"\);\s*//(.*)')
_CHOICE_RE = re.compile(r'Info_AddChoice\s*\(\s*\w+\s*,\s*"([^"]*)"\s*,\s*(\w+)\s*\);')
_GIVE_RE   = re.compile(
    r'(?:CreateInvItems?\(self,\s*([^,)]+)(?:,\s*(\d+))?\);\s*)?'
    r'B_GiveInvItems\s*\(self,\s*\w+,\s*([^,]+),\s*(\d+)\);')
_TAKE_RE   = re.compile(r'B_GiveInvItems\s*\(other,\s*self,\s*([^,]+),\s*(\d+)\);')
_XP_RE     = re.compile(r'B_Give(?:Player)?XP\s*\(([^)]*)\);')
_LOG_RE    = re.compile(
    r'Log_CreateTopic\s*\(([^,]+),\s*\w+\);\s*'
    r'Log_SetTopicStatus\s*\(([^,]+),\s*(\w+)\);'
    r'(?:\s*B_LogEntry\s*\([^,]+,\s*"([^"]*)"\);)?')
_ROUTINE_RE = re.compile(r'Npc_ExchangeRoutine\s*\(self,\s*"([^"]*)"\);')
_FOLLOW_RE  = re.compile(r'AI_StartState\s*\(self,\s*ZS_Follow_Player,\s*0,\s*""\);')


def _parse_body(seg, bn):
    """Pull the shared pieces (entries in order, choices) out of one function
    body — used for both top-level Info() bodies and follow-up func bodies."""
    found = []
    for m in _LINE_RE.finditer(seg):
        speaker = "other" if m.group(1) == "other" else "self"
        found.append((m.start(), DialogLine(speaker=speaker, text=m.group(3).strip())))
    for m in _GIVE_RE.finditer(seg):
        item = (m.group(1) or m.group(3)).strip()
        count = int(m.group(2) or m.group(4) or 1)
        found.append((m.start(), EffectEntry("give_item", item=item, count=count)))
    for m in _TAKE_RE.finditer(seg):
        found.append((m.start(), EffectEntry("take_item", item=m.group(1).strip(), count=int(m.group(2)))))
    for m in _XP_RE.finditer(seg):
        found.append((m.start(), EffectEntry("give_xp", xp=m.group(1).strip())))
    for m in _LOG_RE.finditer(seg):
        found.append((m.start(), EffectEntry(
            "log", log_topic=m.group(1).strip(), log_status=m.group(3).strip(),
            log_entry=(m.group(4) or ""))))
    for m in _ROUTINE_RE.finditer(seg):
        found.append((m.start(), EffectEntry("routine", routine=m.group(1).strip())))
    for m in _FOLLOW_RE.finditer(seg):
        found.append((m.start(), EffectEntry("follow")))

    found.sort(key=lambda x: x[0])
    entries = [e for _, e in found]

    choices = [DialogChoice(label=m.group(1), func_name=m.group(2))
               for m in _CHOICE_RE.finditer(seg)]

    stop_after = bool(re.search(r'AI_StopProcessInfos\s*\(self\);', seg))
    return dict(entries=entries, choices=choices, stop_after=stop_after)


def _apply_body(b, body):
    b.entries = body["entries"]
    b.choices = body["choices"]
    b.stop_after = body["stop_after"]


def _parse_followups(parent_block, choices, full_text, blocks_out):
    for ch in choices:
        name = ch.func_name
        m = re.search(rf'func void {re.escape(name)}\s*\(\)\s*\{{(.*?)\n\}};', full_text, re.S)
        if not m: continue
        fb = DialogBlock()
        fb.is_followup = True
        fb.name = ch.label or name
        fb.func_name = name
        fb.parent_block = parent_block
        body = _parse_body(m.group(1), name)
        _apply_body(fb, body)
        blocks_out.append(fb)
        if body["choices"]:
            _parse_followups(fb, body["choices"], full_text, blocks_out)


def parse_dia_file(text):
    header_m = re.search(r'//\s*Dialog file for\s+(.*?)\s*\((.*?)\)', text)
    npc_name = header_m.group(1).strip() if header_m else ""
    npc_id   = header_m.group(2).strip() if header_m else ""
    prefix = f"DIA_{sanitize(npc_id)}_"

    blocks = []
    segments = re.split(r'\binstance\s+', text)
    for seg in segments[1:]:
        seg = "instance " + seg
        name_m = re.match(r'instance\s+(\w+)\s*\(C_INFO\)', seg)
        if not name_m:
            continue
        bn = name_m.group(1)
        if bn.endswith("_EXIT"):
            continue  # the EXIT block is regenerated automatically, skip it

        body_m = re.search(r'\{(.*?)\}\s*;', seg, re.S)
        inst_body = body_m.group(1) if body_m else ""

        def field(pat, default=""):
            m = re.search(pat, inst_body)
            return m.group(1).strip() if m else default

        b = DialogBlock()
        b.name = bn[len(prefix):] if bn.startswith(prefix) else bn
        try: b.nr = int(field(r'nr\s*=\s*(\d+)\s*;', "1"))
        except ValueError: b.nr = 1
        perm = field(r'permanent\s*=\s*(\d+)\s*;', "0")
        b.permanent = int(perm) if perm.isdigit() else 0
        b.important = 1 if re.search(r'important\s*=\s*1\s*;', inst_body) else 0
        b.description = field(r'description\s*=\s*"([^"]*)"\s*;', "")
        b.is_trade = bool(re.search(r'Trade\s*=\s*1\s*;', inst_body))

        cond_m = re.search(rf'FUNC int {re.escape(bn)}_Condition\(\)\s*\{{(.*?)\}};\s*FUNC VOID', seg, re.S)
        cond_body = cond_m.group(1).strip() if cond_m else ""
        if cond_body and cond_body != "return 1;":
            b.condition_expr = cond_body

        info_m = re.search(rf'FUNC VOID {re.escape(bn)}_Info\(\)\s*\{{(.*)', seg, re.S)
        info_body = info_m.group(1) if info_m else ""
        cut = info_body.find("\n};")
        if cut != -1: info_body = info_body[:cut]

        body = _parse_body(info_body, bn)
        _apply_body(b, body)
        blocks.append(b)
        if body["choices"]:
            _parse_followups(b, body["choices"], text, blocks)

    # sort top-level scenes by nr, keeping each one's follow-ups clustered
    # immediately after it so the flat list stays in pre-order (parent, then
    # its children, recursively) — that's the order the UI expects to append in.
    clusters, current = [], None
    for blk in blocks:
        if not blk.is_followup:
            current = (blk, [])
            clusters.append(current)
        else:
            current[1].append(blk)
    clusters.sort(key=lambda c: c[0].nr)
    ordered = []
    for top, children in clusters:
        ordered.append(top); ordered.extend(children)
    return npc_name, npc_id, ordered
