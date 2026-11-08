"""
daedalus_read.py - just enough Daedalus lexing to read scripts nobody here wrote.

Not a compiler. It knows strings, // and /* */ comments, braces and semicolons,
which is all it takes to pull out instances, functions and their statements
from a vanilla file whatever its layout, capitalisation or comments. Anything
a caller does not recognise stays available as text, so it can be reported
instead of silently dropped. No Qt in here.
"""

import re


def _skip(text, i):
    """Index just past the string or comment starting at text[i], or i itself."""
    if text[i] == '"':
        j = text.find('"', i + 1)
        return len(text) if j < 0 else j + 1
    if text.startswith("//", i):
        j = text.find("\n", i)
        return len(text) if j < 0 else j
    if text.startswith("/*", i):
        j = text.find("*/", i + 2)
        return len(text) if j < 0 else j + 2
    return i


def strip_comments(text):
    """`text` with every // and /* */ comment blanked out, strings and line breaks kept.

    For scanning identifiers only (pickers, validation): vanilla parks whole blocks
    of old items in /* */, and those do not exist for the compiler. Never use it to
    read a file back in - a dialog's spoken text lives in its // comments.
    """
    out, i, n = [], 0, len(text)
    while i < n:
        j = _skip(text, i)
        if j == i:
            k = i + 1
            while k < n and text[k] not in '"/':
                k += 1
            out.append(text[i:k]); i = k
        elif text[i] == '"':
            out.append(text[i:j]); i = j
        else:
            out.append("\n" * text.count("\n", i, j)); i = j
    return "".join(out)


def match_brace(text, start):
    """Index of the `}` that closes the `{` at text[start], or -1."""
    depth, i, n = 0, start, len(text)
    while i < n:
        j = _skip(text, i)
        if j != i:
            i = j
            continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def split_statements(body):
    """[(raw statement, trailing // comment)] for a block body.

    A braced statement (`if (...) { ... };`, with any `else` chain) is a single
    statement, kept with the comments inside it. A comment that follows a statement
    on its own line is returned with that statement - Gothic dialogs keep the
    spoken text there.
    """
    out, cur = [], []
    depth, i, n, last_end = 0, 0, len(body), 0

    def flush(end):
        nonlocal last_end
        text = "".join(cur).strip()
        cur.clear()
        if text:
            out.append([text, ""])
        last_end = end

    while i < n:
        c = body[i]
        if c == '"':
            j = _skip(body, i)
            cur.append(body[i:j])
            i = j
        elif body.startswith("//", i):
            j = _skip(body, i)
            if depth > 0:
                cur.append(body[i:j])      # inside { } the comment stays: it may be spoken text
            elif (out and not "".join(cur).strip() and not out[-1][1]
                    and "\n" not in body[last_end:i]):
                out[-1][1] = body[i + 2:j].strip()
            i = j
        elif body.startswith("/*", i):
            j = _skip(body, i)
            if depth > 0:
                cur.append(body[i:j])
            i = j
        elif c == "{":
            depth += 1
            cur.append(c)
            i += 1
        elif c == "}":
            depth -= 1
            cur.append(c)
            i += 1
            if depth == 0:
                k = i
                while k < n and body[k] in " \t\r\n":
                    k += 1
                if body[k:k + 4].lower() == "else":
                    cur.append(" ")
                    i = k
                    continue
                if k < n and body[k] == ";":
                    cur.append(";")
                    i = k + 1
                flush(i)
        elif c == ";" and depth == 0:
            cur.append(c)
            i += 1
            flush(i)
        else:
            cur.append(c)
            i += 1
    flush(i)
    return [(t, c) for t, c in out]


_FUNC = re.compile(r"\bfunc\s+\w+\s+(\w+)\s*\([^)]*\)\s*\{", re.I)
_INSTANCE = re.compile(r"\binstance\s+(\w+)\s*\(\s*(\w+)\s*\)\s*\{", re.I)


def _blocks(text, pattern):
    """(match, body) for every `<header> { body }` the pattern finds."""
    out, pos = [], 0
    while True:
        m = pattern.search(text, pos)
        if not m:
            return out
        end = match_brace(text, m.end() - 1)
        if end < 0:
            return out
        out.append((m, text[m.end():end]))
        pos = end + 1


def functions(text):
    """{lower-case name: (name, body)} for every func in `text`."""
    return {m.group(1).lower(): (m.group(1), body) for m, body in _blocks(text, _FUNC)}


def instances(text):
    """[(name, parent, body)] for every instance in `text`."""
    return [(m.group(1), m.group(2), body) for m, body in _blocks(text, _INSTANCE)]


_TOP_STATEMENT = re.compile(r"^[ \t]*(?:var|const)\s+\w+\s+(\w+)[^;]*;[ \t]*$", re.I | re.M)


def top_level(text):
    """[(kind, name, start, end)] for every top-level func, instance and var/const
    statement, in file order. `start` includes the // comment lines directly above
    it (no blank line between), `end` is exclusive and includes a trailing `;`."""
    spans = []
    for kind, pattern in (("func", _FUNC), ("instance", _INSTANCE)):
        pos = 0
        while True:
            m = pattern.search(text, pos)
            if not m:
                break
            close = match_brace(text, m.end() - 1)
            if close < 0:
                break
            end = close + 1
            while end < len(text) and text[end] in " \t":
                end += 1
            if end < len(text) and text[end] == ";":
                end += 1
            spans.append([kind, m.group(1), m.start(), end])
            pos = close + 1
    inside = lambda i: any(s[2] <= i < s[3] for s in spans)
    for m in _TOP_STATEMENT.finditer(text):
        if not inside(m.start()):
            spans.append(["var", m.group(1), m.start(), m.end()])
    spans.sort(key=lambda s: s[2])
    for s in spans:                                   # pull the comment lines above it in
        start = s[2]
        while start > 0:
            prev = text.rfind("\n", 0, start - 1)
            line = text[prev + 1:start - 1] if start >= 1 else ""
            if line.strip().startswith("//") and start - 1 > 0 and text[start - 1] == "\n":
                start = prev + 1
            else:
                break
        s[2] = start
    return [tuple(s) for s in spans]


def norm(statement):
    """A statement with whitespace collapsed and the closing `;` removed."""
    return " ".join(statement.split()).rstrip(";").strip()


def assignment(statement):
    """(key, value) for `key = value`, else None. Handles `aivar[X] = Y`."""
    m = re.fullmatch(r"([\w\[\]\s]+?)\s*=\s*(.+)", norm(statement), re.S)
    return (m.group(1).replace(" ", ""), m.group(2).strip()) if m else None


def unquote(value):
    value = value.strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value


def canon(value, options):
    """`value` spelled the way `options` spell it, if it is one of them (any case)."""
    lookup = {str(o).lower(): o for o in options}
    return lookup.get(str(value).lower().strip(), value)
