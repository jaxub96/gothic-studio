"""Compare two dialog files by meaning, not layout.

    python3 manual-test/compare.py ORIGINAL.d SAVED.d

Prints what is the same and what differs. Layout, comments between statements, spacing,
TRUE/1 spelling and the order of menu calls on different menus do not count; names, fields,
condition terms (in order), spoken lines with their subtitles, effects and statement order do.
"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dialog_gen as g
from daedalus_read import functions, top_level


def load(path):
    text = Path(path).read_bytes().decode("cp1250", errors="replace").replace("\r\n", "\n")
    defs = {n.lower(): (k, text[a:b]) for k, n, a, b in top_level(text)}
    for key, (name, body) in functions(text).items():
        if key not in defs:
            m = re.search(r"\b(func\s+\w+)\s+" + re.escape(name) + r"\b", text, re.I)
            defs[key] = ("func", f"{m.group(1) if m else 'func void'} {name}()\n{{{body}}}")
    return defs


def main(a, b):
    A, B = load(a), load(b)
    same = [n for n in A if n in B and g._same_def(A[n], B[n])]
    differ = [n for n in A if n in B and not g._same_def(A[n], B[n])]
    lost = [n for n in A if n not in B]
    added = [n for n in B if n not in A]
    print(f"{len(same)} definitions are the same in meaning")
    for title, names in (("DIFFER", differ), ("MISSING from the saved file", lost), ("NEW in the saved file", added)):
        if names:
            print(f"\n{title} ({len(names)}):")
            for n in names:
                print("   ", n)
    return 0 if not (differ or lost) else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
