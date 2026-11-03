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
        self.kind = kind          # "give_item" | "take_item" | "give_xp" | "log" | "routine" | "follow" | "unfollow" | "raw"
        self.item = fields.get("item", "")
        self.count = fields.get("count", 1)
        self.xp = fields.get("xp", "")
        self.log_topic = fields.get("log_topic", "")
        self.log_status = fields.get("log_status", "LOG_RUNNING")
        self.log_entry = fields.get("log_entry", "")
        self.routine = fields.get("routine", "")
        self.raw = fields.get("raw", "")    # a statement kept exactly as written

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
        if self.kind == "raw":
            text = " ".join(self.raw.split())
            return text if len(text) <= 60 else text[:57] + "..."
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

def _q(text):
    """A string literal, unless the text starts with `=`: then it is Daedalus
    to emit as written (how a read-in label like DIALOG_BACK survives)."""
    text = text or ""
    return text[1:].strip() if text.startswith("=") else f'"{text}"'


def _log_type(s): return "LOG_MISSION" if ("RUNNING" in s or "SUCCESS" in s) else "LOG_NOTE"

def export_block_name(npc_id, block_name):
    """The exported instance identifier for a top-level scene, e.g. DIA_KDF_405_Torrez_Hello."""
    safe = sanitize(npc_id)
    bn = sanitize(block_name) if block_name else f"DIA_{safe}_Block"
    if not bn.startswith("DIA_"): bn = f"DIA_{safe}_{bn}"
    return bn

KNOWSINFO_RE = re.compile(r'(Npc_KnowsInfo\s*\(\s*\w+\s*,\s*)(\w+)(\s*\))', re.I)

def resolve_condition(expr, npc_id, blocks):
    """Npc_KnowsInfo(other, FollowMe) -> Npc_KnowsInfo(other, DIA_<npc>_FollowMe).

    In the app a scene is called by its short name, but the game only knows the
    exported instance. Names that are not a scene of this file stay as written.
    """
    scenes = {sanitize(b.name).upper(): export_block_name(npc_id, b.name)
              for b in blocks if b.name and not b.is_followup and not b.is_exit}
    return KNOWSINFO_RE.sub(lambda m: m.group(1) + scenes.get(m.group(2).upper(), m.group(2)) + m.group(3), expr)

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
        elif e.kind == "raw":
            if e.raw.strip():
                out.append("\t" + e.raw.strip().replace("\n", "\n\t"))
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
            out.append(f'\tInfo_AddChoice\t({b.func_name},{_q(ch.label)},{ch.func_name});')
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
        if b.description and not b.important: out.append(f'\tdescription\t= {_q(b.description)};')
        if b.is_trade: out.append("\tTrade\t\t= 1;")
        out += ["};", "", f"FUNC int {bn}_Condition()", "{"]
        if b.condition_expr.strip():
            for cl in resolve_condition(b.condition_expr.strip(), npc_id, blocks).splitlines(): out.append(f"\t{cl}")
        else:
            out.append("\treturn 1;")
        out += ["};", "", f"FUNC VOID {bn}_Info()", "{"]
        if b.choices: out.append(f"\tInfo_ClearChoices\t({bn});")
        out += _entry_lines(b.entries, bn)
        if b.choices:
            for ch in b.choices:
                out.append(f'\tInfo_AddChoice\t({bn},{_q(ch.label)},{ch.func_name});')
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
_AI_OUTPUT = re.compile(r'AI_Output\s*\(\s*(\w+)\s*,\s*(\w+)\s*,\s*"[^"]*"\s*\)', re.I)
_CHOICE = re.compile(r'Info_AddChoice\s*\(\s*(\w+)\s*,\s*(.+)\s*,\s*(\w+)\s*\)', re.I | re.S)
_CREATE = re.compile(r'CreateInvItems?\s*\(\s*self\s*,\s*(\w+)\s*(?:,\s*(\d+)\s*)?\)', re.I)
_GIVE_INV = re.compile(r'B_GiveInvItems\s*\(\s*(\w+)\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*(\d+)\s*\)', re.I)
_XP = re.compile(r'B_Give(?:Player)?XP\s*\(\s*(.*?)\s*\)', re.I)
_LOG_TOPIC = re.compile(r'Log_CreateTopic\s*\(\s*(\w+)\s*,\s*\w+\s*\)', re.I)
_LOG_STATUS = re.compile(r'Log_SetTopicStatus\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)', re.I)
_LOG_ENTRY = re.compile(r'B_LogEntry\s*\(\s*(\w+)\s*,\s*"([^"]*)"\s*\)', re.I)
_ROUTINE = re.compile(r'Npc_ExchangeRoutine\s*\(\s*self\s*,\s*"([^"]*)"\s*\)', re.I)
_FOLLOW = re.compile(r'AI_StartState\s*\(\s*self\s*,\s*ZS_Follow_Player\s*,\s*0\s*,\s*""\s*\)', re.I)
_STOP = re.compile(r'AI_StopProcessInfos\s*\(\s*self\s*\)', re.I)
_CLEAR = re.compile(r'Info_ClearChoices\s*\(\s*\w+\s*\)', re.I)


def _truthy(value):
    value = value.strip().upper()
    return int(value) if value.isdigit() else int(value == "TRUE")


def _parse_body(body):
    """Statements of one function body -> entries, choices, stop flag.

    Whatever is not a recognised dialog statement becomes a "raw" entry, kept
    as written, so reading a hand-written scene and writing it back loses
    nothing but the voice-file ids.
    """
    from daedalus_read import norm, split_statements

    sts = split_statements(body)
    entries, choices, stop = [], [], False
    i = 0
    while i < len(sts):
        raw, comment = sts[i]
        t = norm(raw)
        nxt = norm(sts[i + 1][0]) if i + 1 < len(sts) else ""
        m = _AI_OUTPUT.fullmatch(t)
        if m:
            entries.append(DialogLine("other" if m.group(1).lower() == "other" else "self",
                                      comment))
        elif _STOP.fullmatch(t):
            stop = True
        elif _CLEAR.fullmatch(t):
            pass
        elif (m := _CHOICE.fullmatch(t)):
            label = m.group(2).strip()
            if len(label) >= 2 and label[0] == label[-1] == '"' and label.count('"') == 2:
                choices.append(DialogChoice(label[1:-1], m.group(3)))
            else:
                choices.append(DialogChoice("= " + label, m.group(3)))
        elif (m := _CREATE.fullmatch(t)) and (g := _GIVE_INV.fullmatch(nxt)) \
                and g.group(1).lower() == "self" and g.group(3).lower() == m.group(1).lower():
            entries.append(EffectEntry("give_item", item=g.group(3), count=int(g.group(4))))
            i += 1
        elif (m := _GIVE_INV.fullmatch(t)) and m.group(1).lower() == "self":
            entries.append(EffectEntry("give_item", item=m.group(3), count=int(m.group(4))))
        elif m and m.group(2).lower() == "self":
            entries.append(EffectEntry("take_item", item=m.group(3), count=int(m.group(4))))
        elif (m := _XP.fullmatch(t)):
            entries.append(EffectEntry("give_xp", xp=m.group(1)))
        elif (m := _LOG_TOPIC.fullmatch(t)) and (s := _LOG_STATUS.fullmatch(nxt)) \
                and s.group(1).lower() == m.group(1).lower():
            topic, status, text = m.group(1), s.group(2), ""
            i += 1
            if i + 1 < len(sts) and (e := _LOG_ENTRY.fullmatch(norm(sts[i + 1][0]))) \
                    and e.group(1).lower() == topic.lower():
                text = e.group(2)
                i += 1
            entries.append(EffectEntry("log", log_topic=topic, log_status=status, log_entry=text))
        elif (m := _ROUTINE.fullmatch(t)):
            entries.append(EffectEntry("routine", routine=m.group(1)))
        elif _FOLLOW.fullmatch(t):
            entries.append(EffectEntry("follow"))
        else:
            entries.append(EffectEntry("raw", raw=raw.strip()))
        i += 1
    return entries, choices, stop


def _followups(parent, choices, funcs, out, notes, seen):
    for ch in choices:
        key = ch.func_name.lower()
        if key in seen:
            continue
        seen.add(key)
        if key not in funcs:
            notes.append(f"choice handler {ch.func_name} is not in this file")
            continue
        name, body = funcs[key]
        entries, sub, stop = _parse_body(body)
        fb = DialogBlock()
        fb.is_followup, fb.func_name, fb.parent_block = True, name, parent
        fb.name = name if ch.label.startswith("=") or not ch.label else ch.label
        fb.entries, fb.choices, fb.stop_after = entries, sub, stop
        out.append(fb)
        if sub:
            _followups(fb, sub, funcs, out, notes, seen)


def _dedent(body):
    import textwrap
    return textwrap.dedent(body.strip("\n")).strip()


def parse_dia_file(text, notes=None):
    """Read dialog scenes back into blocks: files from this tool and vanilla ones.

    Every C_INFO instance becomes a scene; the functions it names for its
    condition and body are found by name, in any capitalisation or layout.
    Statements with no editor equivalent are kept as "raw" entries. Pass a list
    as `notes` to be told what could not be carried over (functions nothing
    refers to, variables, choice handlers defined elsewhere).
    """
    from daedalus_read import assignment, functions, instances, norm, split_statements, unquote

    notes = notes if notes is not None else []
    funcs = functions(text)
    infos = [(n, body) for n, parent, body in instances(text) if parent.upper() == "C_INFO"]

    header_m = re.search(r'//\s*Dialog file for\s+(.*?)\s*\((.*?)\)', text)
    npc_name = header_m.group(1).strip() if header_m else ""
    npc_id = header_m.group(2).strip() if header_m else ""
    fields_of = {}
    for name, body in infos:
        pairs = [assignment(s_) for s_, _ in split_statements(body)]
        fields_of[name] = {a[0].lower(): a[1] for a in pairs if a}
    if not npc_id:
        npc_id = next((f["npc"] for f in fields_of.values() if f.get("npc")), "")
    prefix = f"DIA_{sanitize(npc_id)}_"

    blocks, used = [], set()
    for bn, _ in infos:
        f = fields_of[bn]
        if bn.upper().endswith("_EXIT") or f.get("description", "").upper() == "DIALOG_ENDE":
            continue                       # the EXIT scene is regenerated automatically
        b = DialogBlock()
        b.name = bn[len(prefix):] if bn.startswith(prefix) else bn
        b.nr = int(f["nr"]) if f.get("nr", "").isdigit() else 1
        b.permanent = _truthy(f.get("permanent", "0"))
        b.important = _truthy(f.get("important", "0"))
        desc = f.get("description", "")
        b.description = unquote(desc) if desc.startswith('"') else (f"= {desc}" if desc else "")
        b.is_trade = _truthy(f.get("trade", "0")) == 1

        cond = f.get("condition", "").lower()
        if cond in funcs:
            used.add(cond)
            expr = _dedent(funcs[cond][1])
            if norm(expr).lower() not in ("return 1", "return true", ""):
                b.condition_expr = expr
        info = f.get("information", "").lower()
        if info in funcs:
            used.add(info)
            b.entries, b.choices, b.stop_after = _parse_body(funcs[info][1])
        b.func_name = bn
        blocks.append(b)
        if b.choices:
            tail = []
            _followups(b, b.choices, funcs, tail, notes, used)
            blocks.extend(tail)
            used |= {x.func_name.lower() for x in tail}

    for key, (name, _) in funcs.items():
        if key not in used and not name.upper().endswith("_EXIT_CONDITION") \
                and not name.upper().endswith("_EXIT_INFO"):
            notes.append(f"function {name} is not used by any scene")
    for var in re.findall(r"^\s*var\s+\w+\s+(\w+)", text, re.I | re.M):
        notes.append(f"variable {var} is declared here")

    # sort top-level scenes by nr, keeping each one's follow-ups clustered
    # immediately after it so the flat list stays in pre-order (parent, then
    # its children, recursively) - that's the order the UI expects to append in.
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
        ordered.append(top)
        ordered.extend(children)
    return npc_name, npc_id, ordered
