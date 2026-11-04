r"""
install.py - copy the mod's script package into a Gothic II Scripts folder
and hook it into the build.

    python mod/install.py                      # the mod Gothic Studio is using
    python mod/install.py "C:\Gothic II\_work\Data\Scripts"
    python mod/install.py --dry-run            # say what would change, change nothing
    python mod/install.py --force              # overwrite files you edited in the mod

What it does, every step safe to repeat:

1. Copies mod/Content/** into <Scripts>/Content/, written the way the engine
   reads scripts (CP1250, CRLF). A file that already exists there with other
   content is left alone and reported - you edited it in the mod - unless
   --force is given.
2. Adds the package's lines to Content/Gothic.src (the files vanilla does not
   pick up by itself): the guild and constant files right after
   _intern\Constants.d, the items and guild attitudes just before Story\NPC.
3. Calls B_Mod_InitGuildAttitudes() after every B_InitGuildAttitudes() in
   Story/Startup.d, so the mod's attitudes win.

Gothic.src and Startup.d get a .bak copy the first time they are changed.
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE / "Content"
ENCODING = "cp1250"

#: (anchor, where, lines). The anchor is a regex over one Gothic.src line;
#: `after` puts the lines after its first match, `before` before it.
SRC_LINES = [
    (r"_intern\\constants\.d", "after", [
        r"MOD\MOD_GUILDS.D",
        r"MOD\MOD_CONSTANTS.D",
    ]),
    (r"story\\npc\\", "before", [
        r"MOD\ITEMS\*.D",
        r"MOD\MOD_GUILD_ATTITUDES.D",
    ]),
]

#: Folders the package puts files into that vanilla Gothic.src already globs.
#: If one is missing, its file would silently never compile - say so.
EXPECTED_GLOBS = {
    r"story\\npc\\\*": r"STORY\NPC\*.D",
    r"story\\dialoge\\dia\*": r"STORY\DIALOGE\DIA*.D",
    r"story\\log_entries\\": r"STORY\LOG_ENTRIES\*.D",
}

ATTITUDE_CALL = "B_Mod_InitGuildAttitudes ();"


def default_scripts():
    """The Scripts folder Gothic Studio would use (GOTHIC_SCRIPTS, the saved
    folder, or walking up from the repo)."""
    sys.path.insert(0, str(HERE.parent))
    try:
        import project
    except Exception:                         # noqa: BLE001 - any failure: ask for a path
        return None
    return project.SCRIPTS if project.FOUND else None


def read(path):
    # latin-1 maps every byte to one char and back, so files we only patch
    # keep their exact bytes whatever code page they were written in.
    return path.read_bytes().decode("latin-1")


def write(path, text, dry):
    if dry:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("latin-1"))


def backup(path, dry):
    bak = path.with_name(path.name + ".bak")
    if not dry and not bak.exists():
        bak.write_bytes(path.read_bytes())


def copy_package(content, force, dry):
    for src in sorted(PACKAGE.rglob("*.d")):
        rel = src.relative_to(PACKAGE)
        dst = content / rel
        raw = src.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:            # already saved in the game's code page
            text = raw.decode(ENCODING)
        text = text.replace("\r\n", "\n").replace("\n", "\r\n")
        data = text.encode(ENCODING)
        if dst.exists():
            if dst.read_bytes() == data:
                print(f"  same     {rel}")
                continue
            if not force:
                print(f"  KEPT     {rel}  (differs from the package - you edited it? --force overwrites)")
                continue
            print(f"  replaced {rel}")
        else:
            print(f"  added    {rel}")
        if not dry:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)


def patch_gothic_src(src, dry):
    text = read(src)
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)
    have = {ln.strip().upper() for ln in lines}
    changed = False

    for anchor, where, new in SRC_LINES:
        missing = [n for n in new if n.upper() not in have]
        if not missing:
            print(f"  present  {', '.join(new)}")
            continue
        at = next((i for i, ln in enumerate(lines) if re.search(anchor, ln.strip(), re.I)), None)
        if at is None:
            print(f"  !! no line matching {anchor!r} - add these by hand: {', '.join(missing)}")
            continue
        at = at + 1 if where == "after" else at
        lines[at:at] = missing
        have |= {n.upper() for n in missing}
        changed = True
        print(f"  added    {', '.join(missing)}")

    for pattern, example in EXPECTED_GLOBS.items():
        if not any(re.search(pattern, ln.strip(), re.I) for ln in lines):
            print(f"  !! Gothic.src has no {example} line - the package's files there will not compile")

    if changed:
        backup(src, dry)
        write(src, eol.join(lines), dry)


def patch_startup(startup, dry):
    if not startup.is_file():
        print(f"  !! {startup} not found - call {ATTITUDE_CALL} from your INIT_<world> functions by hand")
        return
    text = read(startup)
    eol = "\r\n" if "\r\n" in text else "\n"
    vanilla = re.compile(r"^([ \t]*)B_InitGuildAttitudes\s*\(\s*\)\s*;[^\r\n]*(?=\r?\n|\Z)", re.I | re.M)
    done = re.compile(r"\A\s*B_Mod_InitGuildAttitudes\s*\(", re.I)
    out, last, added, found = [], 0, 0, 0
    for m in vanilla.finditer(text):
        found += 1
        out.append(text[last:m.end()])
        last = m.end()
        if not done.match(text[last:]):
            out.append(f"{eol}{m.group(1)}{ATTITUDE_CALL}")
            added += 1
    out.append(text[last:])
    if not found:
        print(f"  !! no B_InitGuildAttitudes() call in Startup.d - call {ATTITUDE_CALL} "
              "from your INIT_<world> functions by hand")
    elif not added:
        print(f"  present  {ATTITUDE_CALL} ({found}x)")
    else:
        print(f"  added    {ATTITUDE_CALL} after {added} B_InitGuildAttitudes() call(s)")
        backup(startup, dry)
        write(startup, "".join(out), dry)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scripts", nargs="?", help=r"the ...\Data\Scripts folder (holds Content\Gothic.src)")
    ap.add_argument("--force", action="store_true", help="overwrite files that differ from the package")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)

    scripts = Path(args.scripts) if args.scripts else default_scripts()
    if scripts is None:
        ap.error("no Scripts folder found - pass one, e.g. python mod/install.py <...\\Data\\Scripts>")
    content = Path(scripts) / "Content"
    gothic_src = content / "Gothic.src"
    if not gothic_src.is_file():
        ap.error(f"{gothic_src} does not exist - that is not a Scripts folder")

    print(f"Installing into {content}{'  (dry run)' if args.dry_run else ''}")
    print("Files:")
    copy_package(content, args.force, args.dry_run)
    print("Gothic.src:")
    patch_gothic_src(gothic_src, args.dry_run)
    print("Story/Startup.d:")
    patch_startup(content / "Story" / "Startup.d", args.dry_run)
    print("Done. Run Compile check in Gothic Studio (or gdc) to confirm it builds.")


if __name__ == "__main__":
    main()
