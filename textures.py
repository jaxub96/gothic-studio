"""
textures.py - reads Gothic's compiled textures so the app can show you what a
face, body or armor actually looks like instead of just its constant name.

Gothic stores textures as ZTEX: a 36-byte header, then the mipmap chain
smallest-first, in DXT1/DXT3/DXT5 or a plain uncompressed layout. No external
image library is used - the decoders below are short enough to read.

Only pixel decoding lives here. Turning that into a QPixmap is texture_view.py.
"""

import re
import struct
from functools import lru_cache
from pathlib import Path

from project import SCRIPTS, iglob

TEXTURE_DIR = SCRIPTS.parent / "Textures" / "_compiled"

# zTEX_FORMAT
FMT_B8G8R8A8, FMT_R8G8B8A8, FMT_A8B8G8R8, FMT_A8R8G8B8 = 0, 1, 2, 3
FMT_B8G8R8, FMT_R8G8B8 = 4, 5
FMT_A4R4G4B4, FMT_A1R5G5B5, FMT_R5G6B5, FMT_P8 = 6, 7, 8, 9
FMT_DXT1, FMT_DXT2, FMT_DXT3, FMT_DXT4, FMT_DXT5 = 10, 11, 12, 13, 14

_HEADER = struct.Struct("<9I")   # sig, ver, format, w, h, mips, refW, refH, avgColor


def _level_size(fmt, w, h):
    """Bytes one mip level occupies."""
    if fmt in (FMT_DXT1,):
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 8
    if fmt in (FMT_DXT2, FMT_DXT3, FMT_DXT4, FMT_DXT5):
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * 16
    bpp = {FMT_B8G8R8A8: 4, FMT_R8G8B8A8: 4, FMT_A8B8G8R8: 4, FMT_A8R8G8B8: 4,
           FMT_B8G8R8: 3, FMT_R8G8B8: 3,
           FMT_A4R4G4B4: 2, FMT_A1R5G5B5: 2, FMT_R5G6B5: 2, FMT_P8: 1}.get(fmt)
    return None if bpp is None else w * h * bpp


def _rgb565(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def _decode_dxt(data, w, h, fmt):
    """DXT1/3/5 -> RGB888 bytes. Alpha is ignored; we only ever show opaque art."""
    import fastpath
    if fastpath.HAVE_NUMPY:
        fast = fastpath.decode_dxt(data, w, h, fmt != FMT_DXT1)
        if fast is not None:
            return fast

    out = bytearray(w * h * 3)
    blocks_x = max(1, (w + 3) // 4)
    blocks_y = max(1, (h + 3) // 4)
    big = fmt != FMT_DXT1
    stride = 16 if big else 8
    colour_offset = 8 if big else 0

    pos = 0
    for by in range(blocks_y):
        for bx in range(blocks_x):
            if pos + stride > len(data):
                return bytes(out)
            block = data[pos:pos + stride]
            pos += stride

            c0, c1 = struct.unpack_from("<HH", block, colour_offset)
            bits = struct.unpack_from("<I", block, colour_offset + 4)[0]
            r0, g0, b0 = _rgb565(c0)
            r1, g1, b1 = _rgb565(c1)

            if c0 > c1 or big:
                palette = ((r0, g0, b0), (r1, g1, b1),
                           ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3),
                           ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3))
            else:
                palette = ((r0, g0, b0), (r1, g1, b1),
                           ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2),
                           (0, 0, 0))

            for py in range(4):
                y = by * 4 + py
                if y >= h:
                    break
                row = (bits >> (py * 8)) & 0xFF
                for px in range(4):
                    x = bx * 4 + px
                    if x >= w:
                        break
                    r, g, b = palette[(row >> (px * 2)) & 0x3]
                    i = (y * w + x) * 3
                    out[i] = r
                    out[i + 1] = g
                    out[i + 2] = b
    return bytes(out)


def _decode_plain(data, w, h, fmt):
    """The handful of uncompressed layouts, -> RGB888."""
    out = bytearray(w * h * 3)
    n = w * h
    if fmt in (FMT_B8G8R8A8, FMT_A8R8G8B8, FMT_R8G8B8A8, FMT_A8B8G8R8):
        order = {FMT_B8G8R8A8: (2, 1, 0), FMT_A8R8G8B8: (1, 2, 3),
                 FMT_R8G8B8A8: (0, 1, 2), FMT_A8B8G8R8: (3, 2, 1)}[fmt]
        for i in range(n):
            p = i * 4
            if p + 3 >= len(data):
                break
            out[i * 3] = data[p + order[0]]
            out[i * 3 + 1] = data[p + order[1]]
            out[i * 3 + 2] = data[p + order[2]]
    elif fmt in (FMT_B8G8R8, FMT_R8G8B8):
        rev = fmt == FMT_B8G8R8
        for i in range(n):
            p = i * 3
            if p + 2 >= len(data):
                break
            r, g, b = data[p + 2], data[p + 1], data[p] if rev else (data[p], data[p + 1], data[p + 2])
            out[i * 3], out[i * 3 + 1], out[i * 3 + 2] = (r, g, b)
    elif fmt == FMT_R5G6B5:
        for i in range(n):
            p = i * 2
            if p + 1 >= len(data):
                break
            r, g, b = _rgb565(struct.unpack_from("<H", data, p)[0])
            out[i * 3], out[i * 3 + 1], out[i * 3 + 2] = r, g, b
    else:
        return None
    return bytes(out)


def decode(ref):
    """Decode a texture. Returns (width, height, rgb888_bytes) or None.

    Accepts a TexRef, a Path, or raw bytes. ZTEX stores mipmaps smallest-first,
    so the full-size image is the tail of the file.

    Cached: decoding a 512x512 DXT1 costs ~80ms in Python, and the 3D preview
    would otherwise pay that for every mesh on every frame.
    """
    if ref is None:
        return None
    if isinstance(ref, TexRef):
        key = (str(ref.path), ref.offset, ref.size)
        hit = _decoded.get(key)
        if hit is None and key not in _decoded:
            hit = _decode_raw(ref.data())
            if len(_decoded) > 64:
                _decoded.clear()
            _decoded[key] = hit
        return hit
    if isinstance(ref, (bytes, bytearray)):
        return _decode_raw(bytes(ref))
    try:
        return _decode_raw(Path(ref).read_bytes())
    except OSError:
        return None


_decoded = {}


def _decode_raw(raw):
    if not raw or len(raw) < _HEADER.size or raw[:4] != b"ZTEX":
        return None

    _, _, fmt, w, h, mips, _, _, _ = _HEADER.unpack_from(raw, 0)
    if not (0 < w <= 4096 and 0 < h <= 4096):
        return None

    size0 = _level_size(fmt, w, h)
    if size0 is None or size0 > len(raw):
        return None

    body = raw[_HEADER.size:]
    if fmt == FMT_P8:
        return None                      # paletted: not used by the art we show

    level0 = body[-size0:] if mips > 1 else body[:size0]

    if fmt in (FMT_DXT1, FMT_DXT2, FMT_DXT3, FMT_DXT4, FMT_DXT5):
        rgb = _decode_dxt(level0, w, h, fmt)
    else:
        rgb = _decode_plain(level0, w, h, fmt)
    return (w, h, rgb) if rgb else None


# --- Finding the right file for a thing you picked in the UI ----------------

class TexRef:
    """One texture, either a loose file or a slice of a .vdf archive."""

    __slots__ = ("name", "path", "offset", "size")

    def __init__(self, name, path, offset=None, size=None):
        self.name = name
        self.path = path
        self.offset = offset
        self.size = size

    @property
    def archived(self):
        return self.offset is not None

    def data(self):
        try:
            if not self.archived:
                return self.path.read_bytes()
            with open(self.path, "rb") as f:
                f.seek(self.offset)
                return f.read(self.size)
        except OSError:
            return b""

    def __repr__(self):
        where = f"{self.path.name}@{self.offset}" if self.archived else "loose"
        return f"<TexRef {self.name} ({where})>"


# Gothic's archive format: 296-byte header, then a flat catalogue of 80-byte
# entries. Directory entries carry 0x80000000; everything else is a real file
# whose `offset` is an absolute byte position in the same archive.
_VDF_SIG = b"PSVDSC_V2.00\n\r\n\r"
_VDF_HEADER = struct.Struct("<6I")
_VDF_ENTRY = struct.Struct("<4I")
_DIR_FLAG = 0x80000000


def _read_vdf(path):
    """{NAME: TexRef} for every file in one .vdf. Reads only the catalogue."""
    out = {}
    try:
        with open(path, "rb") as f:
            f.seek(256)
            if f.read(16) != _VDF_SIG:
                return out
            num_entries, _, _, _, root, _ = _VDF_HEADER.unpack(f.read(24))
            f.seek(root)
            blob = f.read(num_entries * 80)
    except OSError:
        return out

    for i in range(num_entries):
        raw = blob[i * 80:(i + 1) * 80]
        if len(raw) < 80:
            break
        offset, size, typ, _ = _VDF_ENTRY.unpack(raw[64:80])
        if typ & _DIR_FLAG:
            continue
        name = raw[:64].decode("latin-1").strip().rstrip("\x00").strip().upper()
        if name:
            out[name] = TexRef(name, path, offset, size)
    return out


def _strip(stem):
    stem = stem.upper()
    if stem.endswith(".TEX"):
        stem = stem[:-4]
    return stem[:-2] if stem.endswith("-C") else stem


def _mod_volumes(data_dir):
    """The texture-pack volumes the active mod loads, oldest first.

    system/mod.ini names them: `VDF=HD_Heads.mod  Armor_HD.mod`. A volume that is in
    ModVDF but not on that line is not loaded by the game, so it is not read here either.
    """
    ini = data_dir.parent / "system" / "mod.ini"
    names = []
    try:
        for line in ini.read_text(encoding="latin-1").splitlines():
            if line.strip().upper().startswith("VDF="):
                names = line.split("=", 1)[1].split()
    except OSError:
        return []
    found = []
    for name in names:
        found += [f for f in iglob(data_dir / "ModVDF", name) if f.is_file()]
    return sorted(set(found), key=lambda f: f.stat().st_mtime)


@lru_cache
def _index():
    """Every texture we can reach, keyed by bare uppercase name.

    Loose files in _work win over archived ones, which is the same precedence
    the engine itself uses.
    """
    out = {}
    # Archives first (lowest priority). The base game's textures live here; the
    # .disabled suffix is how the MDK parks them while loose files take over.
    # SCRIPTS is ...\Gothic II\_work\Data\Scripts, so the game's own Data\ is
    # three levels up. The MDK parks the base archives there as *.vdf.disabled.
    data_dir = SCRIPTS.parents[2] / "Data"
    for pattern in ("Textures*.vdf", "Textures*.vdf.disabled"):
        for vdf in sorted(iglob(data_dir, pattern)):
            for name, ref in _read_vdf(vdf).items():
                if name.endswith(".TEX"):
                    out[_strip(name)] = ref

    # Texture packs: the volumes the mod lists on the VDF= line of system/mod.ini
    # (Data/ModVDF/HD_Heads.mod and the like). They replace the base game's textures;
    # when two hold the same one, the newer volume wins, as in the engine.
    for vdf in _mod_volumes(data_dir):
        for name, ref in _read_vdf(vdf).items():
            if name.endswith(".TEX"):
                out[_strip(name)] = ref

    # Loose compiled textures override.
    if TEXTURE_DIR.is_dir():
        for f in iglob(TEXTURE_DIR, "*.TEX"):
            out[_strip(f.name)] = TexRef(_strip(f.name), f)
    return out


def find(name):
    """Look a texture up by name, with or without the -C/.TEX decoration."""
    key = re.sub(r"(-C)?(\.TEX)?$", "", str(name).upper())
    return _index().get(key)


def face_texture(face_value, skin=0):
    """Face constant value -> its head texture. Face_N_Gomez = 0 -> HUM_HEAD_V0_C0."""
    return find(f"HUM_HEAD_V{int(face_value)}_C{int(skin)}")


def body_texture(body_value, skin=0):
    """BodyTex constant value -> HUM_BODY_NAKED_V<n>_C<n>."""
    return find(f"HUM_BODY_NAKED_V{int(body_value)}_C{int(skin)}")


# --- Meshes: the link between an item and the texture it actually wears -----

MESH_DIR = SCRIPTS.parent / "Meshes" / "_compiled"


@lru_cache
def _mesh_index():
    """{NAME.EXT: TexRef} over every compiled mesh, loose and archived.

    Item models (.MRM) live in Meshes*.vdf; character parts - heads (.MMB),
    bodies and armors (.MDM), skeletons (.MDH) - live in Anims*.vdf.
    """
    out = {}
    data_dir = SCRIPTS.parents[2] / "Data"
    for stem in ("Meshes", "Anims"):
        for pattern in (f"{stem}*.vdf", f"{stem}*.vdf.disabled"):
            for vdf in sorted(iglob(data_dir, pattern)):
                out.update(_read_vdf(vdf))
    for loose in (MESH_DIR, SCRIPTS.parent / "Anims" / "_compiled"):
        if loose.is_dir():
            for f in loose.iterdir():
                if f.suffix.upper() in (".MRM", ".MMB", ".MDM", ".MDH", ".MDL"):
                    out[f.name.upper()] = TexRef(f.name.upper(), f)
    return out


_TGA_RE = re.compile(rb"[A-Za-z0-9_\-]+\.TGA", re.I)


def mesh_textures(mesh_name):
    """Texture names referenced by a compiled mesh.

    A .MRM embeds its material list, and each material names a .TGA. Those
    names carry Piranha Bytes' "PB" prefix - the file on disk is the name
    without it, so both spellings are returned.
    """
    ref = _mesh_index().get(str(mesh_name).upper())
    if not ref:
        return []
    names = []
    for raw in dict.fromkeys(_TGA_RE.findall(ref.data())):
        name = raw.decode("latin-1").upper()[:-4]
        names.append(name)
        if name.startswith("PB"):
            names.append(name[2:])
    return names


@lru_cache
def armor_texture(armor_instance):
    """The texture an armor actually uses.

    Resolution chain, which is how the engine itself gets there:
        ITAR_BARKEEPER
          -> visual = "ItAr_Wirt.3DS"      (from Content/Items)
          -> ITAR_WIRT.MRM                 (compiled mesh, loose or in a .vdf)
          -> "PBWIRT.TGA" in its material list
          -> WIRT-C.TEX                    (drop the PB prefix)

    Falls back to the instance name as the mesh name, which is what most
    armors use. Returns None rather than guessing - the UI then says "no
    preview" instead of showing you somebody else's armor.
    """
    if not armor_instance or str(armor_instance) in ("-1", "NO_ARMOR"):
        return None

    import gamedata

    inst = str(armor_instance).upper()
    candidates = []

    visual = gamedata.item_visuals().get(inst)
    if visual:
        stem = re.sub(r"\.(3DS|ASC|MMS|MDS)$", "", visual, flags=re.I).upper()
        candidates.append(stem + ".MRM")
    candidates.append(inst + ".MRM")

    for mesh in candidates:
        for name in mesh_textures(mesh):
            hit = find(name)
            if hit:
                return hit
    return None


def coverage():
    """How many armors we can actually show. Used by the self-test and by
    `python textures.py`, so the gap is a measured number, not a guess."""
    import gamedata
    armors = list(gamedata.armors())
    hit = [a for a in armors if armor_texture(a)]
    return len(hit), len(armors)


if __name__ == "__main__":
    idx = _index()
    print(f"texture dir : {TEXTURE_DIR}")
    print(f"indexed     : {len(idx)}")
    for label, path in (("face 0", face_texture(0)), ("face 9", face_texture(9)),
                        ("body 1", body_texture(1)),
                        ("ITAR_Vlk_H", armor_texture("ITAR_Vlk_H"))):
        if path:
            got = decode(path)
            print(f"  {label:12} {path.name:34} -> {got[0]}x{got[1]}" if got
                  else f"  {label:12} {path.name:34} -> DECODE FAILED")
        else:
            print(f"  {label:12} (no texture found)")
