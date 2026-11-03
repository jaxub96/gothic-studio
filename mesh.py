"""
mesh.py - reads Gothic's compiled meshes (zCProgMeshProto).

Used by the 3D preview. Handles the container types that wrap the same mesh
structure:

    .MRM  item model            - the proto mesh directly
    .MMB  morph mesh (heads)    - proto mesh + morph data we ignore
    .MDM  model mesh (bodies,   - one or more soft-skin meshes; we read the
          armors)                 bind-pose positions and skip the bone weights

Layout, derived by measuring 400 meshes in this install:

    u16 chunk id 0xB100, u32 chunk length
    u16 version
    u32 poolSize
    <poolSize bytes: every vertex/triangle/wedge array lives in here>
    u8  numSubMeshes
    16 bytes : (offset,count) for positions, then for normals
    80 bytes per submesh : ten (offset,count) pairs, of which we need
                           triangles (pair 0) and wedges (pair 1)
    ZenGin archive : the material list, which names the texture

    position = 3 floats
    triangle = 3 u16 wedge indices
    wedge    = normal 3f, uv 2f, position index u16, 2 bytes padding  (24 total)
"""

import re
import struct
from functools import lru_cache

import textures

CHUNK_MESH = 0xB100
WEDGE = struct.Struct("<5fH")
TRI = struct.Struct("<3H")
VEC3 = struct.Struct("<3f")


class SubMesh:
    """One material's worth of triangles.

    Meshes are split by material: an armor's submeshes are typically the
    garment and the bare skin at the neck and hands, which need different
    textures. Treating a mesh as a single lump paints one over the other.
    """

    __slots__ = ("triangles", "material_textures")

    def __init__(self, triangles, material_textures):
        self.triangles = triangles
        self.material_textures = material_textures

    @property
    def is_skin(self):
        return any("BODY_NAKED" in n.upper() for n in self.material_textures)


class Mesh:
    """Triangles with UVs, ready to rasterise."""

    __slots__ = ("positions", "submeshes", "name")

    def __init__(self, name=""):
        self.name = name
        self.positions = []        # [(x, y, z)]
        self.submeshes = []        # [SubMesh, ...]

    @property
    def triangles(self):
        """Every triangle, ignoring material. Handy for counts and checks."""
        return [t for sub in self.submeshes for t in sub.triangles]

    @property
    def material_textures(self):
        return [n for sub in self.submeshes for n in sub.material_textures]

    def __bool__(self):
        return any(sub.triangles for sub in self.submeshes)

    def bounds(self):
        xs = [p[0] for p in self.positions]
        ys = [p[1] for p in self.positions]
        zs = [p[2] for p in self.positions]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def _find_mesh_chunk(data, start=0):
    """Locate a 0xB100 chunk whose declared length fits inside the file."""
    pos = data.find(b"\x00\xb1", start)
    while pos >= 0:
        if pos + 6 <= len(data):
            cid, clen = struct.unpack_from("<HI", data, pos)
            if cid == CHUNK_MESH and 0 < clen <= len(data) - pos:
                return pos
        pos = data.find(b"\x00\xb1", pos + 1)
    return -1


def _material_list(data, start):
    """Texture candidates per material, in submesh order.

    The material archive follows the submesh descriptors and lists one material
    per submesh, in the same order. Each entry becomes the candidate names for
    that submesh: the name as written, plus the same name without Piranha
    Bytes' "PB" prefix, which is what the file on disk is called.
    """
    materials = []
    for raw in re.findall(rb"[A-Za-z0-9_\-]+\.TGA", data[start:], re.I):
        name = raw.decode("latin-1").upper()[:-4]
        candidates = [name]
        if name.startswith("PB"):
            candidates.append(name[2:])
        materials.append(candidates)
    return materials


def parse(data, name=""):
    """Parse the first proto mesh in `data`. Returns a Mesh, or None."""
    at = _find_mesh_chunk(data)
    if at < 0:
        return None
    try:
        _version, pool_size = struct.unpack_from("<HI", data, at + 6)
        pool_at = at + 12
        end = pool_at + pool_size
        if end + 17 > len(data):
            return None

        num_sub = data[end]
        if not 0 < num_sub <= 32:
            return None
        cur = end + 1
        pos_off, pos_count, _n_off, _n_count = struct.unpack_from("<4I", data, cur)
        cur += 16

        subs = []
        for _ in range(num_sub):
            vals = struct.unpack_from("<20I", data, cur)
            cur += 80
            subs.append(vals[:4])          # tri offset/count, wedge offset/count

        pool = data[pool_at:end]
        mesh = Mesh(name)

        if pos_off + pos_count * 12 > len(pool):
            return None
        mesh.positions = [VEC3.unpack_from(pool, pos_off + i * 12)
                          for i in range(pos_count)]

        materials = _material_list(data, cur)

        for index, (tri_off, tri_count, wedge_off, wedge_count) in enumerate(subs):
            if (wedge_off + wedge_count * 24 > len(pool)
                    or tri_off + tri_count * 6 > len(pool)):
                continue
            wedges = []
            for i in range(wedge_count):
                _nx, _ny, _nz, u, v, vi = WEDGE.unpack_from(pool, wedge_off + i * 24)
                wedges.append((vi, u, v))
            n_wedges = len(wedges)
            triangles = []
            for i in range(tri_count):
                a, b, c = TRI.unpack_from(pool, tri_off + i * 6)
                if a < n_wedges and b < n_wedges and c < n_wedges:
                    triangles.append((wedges[a], wedges[b], wedges[c]))
            if triangles:
                names = materials[index] if index < len(materials) else []
                mesh.submeshes.append(SubMesh(triangles, names))

        return mesh if mesh.positions and mesh.submeshes else None
    except (struct.error, IndexError):
        return None


def parse_all(data, name=""):
    """Every proto mesh in `data`, in file order.

    A .MDM is a mesh *library*: an armor file commonly holds two parts with
    different textures - the garment plus the skin that shows at the neck and
    hands, or a matching helmet. Reading only the first leaves a hole where the
    neck should be, so they are all returned and drawn as separate parts.
    """
    meshes = []
    at = _find_mesh_chunk(data)
    while at >= 0:
        try:
            _cid, clen = struct.unpack_from("<HI", data, at)
        except struct.error:
            break
        piece = parse(data[at:at + 6 + clen], f"{name}#{len(meshes)}" if meshes else name)
        if piece:
            if name.upper().endswith(".MDM"):
                _skin(piece, data, at + 6 + clen)
            meshes.append(piece)
        at = _find_mesh_chunk(data, at + 6 + max(clen, 1))
    return meshes


CHUNK_SKIN = 0xB1FF


def _skin(piece, data, at):
    """Replace a body part's stored positions with its skinned bind pose.

    The positions stored beside the triangles are not reliable. For the naked
    body they are the skeleton-space pose plus a fixed shift, but an armor's
    differ from it by up to ~15 units and not by a constant - drawn as stored,
    an armor sits behind the naked body and the head floats off its collar.
    The real data is the weight list in the chunk that follows the mesh: per
    vertex, a few (weight, bone-local position, bone) entries. Summing
    weight * (bone matrix * position) lands every part in the skeleton's own
    space, which is also where the head bone's matrix puts the head.

    Leaves the stored positions alone if there is no skeleton or the weight
    chunk does not parse, so a damaged file still draws.
    """
    bones = list(skeleton().values())
    try:
        cid, clen = struct.unpack_from("<HI", data, at)
        if cid != CHUNK_SKIN or not bones:
            return
        pos = at + 6 + 4                      # skip the u32 stream length
        out = []
        for _ in piece.positions:
            n = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            x = y = z = 0.0
            for _ in range(n):
                w, px, py, pz, node = struct.unpack_from("<4fB", data, pos)
                pos += 17
                qx, qy, qz = transform_point(bones[node], (px, py, pz))
                x, y, z = x + w * qx, y + w * qy, z + w * qz
            out.append((x, y, z))
        piece.positions = out
    except (struct.error, IndexError):
        return


@lru_cache(maxsize=64)
def load_all(mesh_name):
    """Every part of a compiled mesh file, e.g. 'ARMOR_KDF_H.MDM' -> [robe, skin]."""
    ref = textures._mesh_index().get(str(mesh_name).upper())
    if not ref:
        return ()
    return tuple(parse_all(ref.data(), str(mesh_name).upper()))


def load(mesh_name):
    """The first/main part of a mesh file. Use load_all() to draw it properly."""
    parts = load_all(mesh_name)
    return parts[0] if parts else None


@lru_cache(maxsize=32)
def head_mesh(head_constant):
    """'HUM_HEAD_PONY' -> its .MMB, trying the numbered variants the game uses."""
    base = str(head_constant).upper()
    for candidate in (f"{base}.MMB", f"{base}0.MMB", f"{base}_V0.MMB"):
        m = load(candidate)
        if m:
            return m
    return None


@lru_cache(maxsize=32)
def body_meshes(armor_instance=None):
    """Every part of the worn body: an armor's .MDM if it has one, else naked."""
    if armor_instance and str(armor_instance) not in ("-1", "NO_ARMOR"):
        import gamedata
        visual = gamedata.item_visuals().get(str(armor_instance).upper(), "")
        stem = re.sub(r"\.(3DS|ASC)$", "", visual, flags=re.I).upper()
        for candidate in (f"ARMOR_{str(armor_instance).upper()[5:]}.MDM",
                          f"{stem}.MDM"):
            parts = load_all(candidate)
            if parts:
                return parts
    return load_all("HUM_BODY_NAKED0.MDM")


def body_mesh(armor_instance=None):
    """The main body part only - for measurements, not for drawing."""
    parts = body_meshes(armor_instance)
    return parts[0] if parts else None


# --- Skeleton (.MDH) --------------------------------------------------------
# Needed because a head mesh is stored in its own bone-local frame (its "up" is
# +X), so it only lines up with a body once the head bone's transform is
# applied.
#
#   u16 0xD100, u32 length, u32 version, u16 numNodes
#   per node: name terminated by '\n', s16 parent, 16 floats (row-major 4x4)

CHUNK_HIERARCHY = 0xD100


def _mat_mul(a, b):
    return tuple(sum(a[r * 4 + k] * b[k * 4 + c] for k in range(4))
                 for r in range(4) for c in range(4))


def transform_point(m, p):
    x, y, z = p
    return (m[0] * x + m[1] * y + m[2] * z + m[3],
            m[4] * x + m[5] * y + m[6] * z + m[7],
            m[8] * x + m[9] * y + m[10] * z + m[11])


@lru_cache(maxsize=8)
def skeleton(name="HUMANS.MDH"):
    """{bone name: world matrix} in the skeleton's own space."""
    ref = textures._mesh_index().get(str(name).upper())
    if not ref:
        return {}
    data = ref.data()
    try:
        cid, _clen = struct.unpack_from("<HI", data, 0)
        if cid != CHUNK_HIERARCHY:
            return {}
        count = struct.unpack_from("<H", data, 10)[0]
        pos = 12
        nodes, world = [], {}
        for i in range(count):
            end = data.index(b"\n", pos)
            bone = data[pos:end].decode("latin-1")
            pos = end + 1
            parent = struct.unpack_from("<h", data, pos)[0]
            pos += 2
            local = struct.unpack_from("<16f", data, pos)
            pos += 64
            world[i] = local if parent < 0 or parent >= i else _mat_mul(world[parent], local)
            nodes.append(bone)
        return {n: world[i] for i, n in enumerate(nodes)}
    except (struct.error, ValueError, IndexError):
        return {}


def _neck_hole(body, band=10.0, radius=14.0):
    """Centre (x, z) and top (y) of a body's neck opening.

    The ring of vertices at the very top of the torso, near the vertical axis.
    That ring is literally the hole the head plugs into, which makes it the
    right landmark for lining the head up horizontally.
    """
    if not body:
        return None
    top = body.bounds()[1][1]
    ring = [p for p in body.positions
            if p[1] > top - band and abs(p[0]) < radius and abs(p[2]) < radius]
    if not ring:
        return None
    return (sum(p[0] for p in ring) / len(ring),
            top,
            sum(p[2] for p in ring) / len(ring))


def head_placement(body=None, head=None):
    """Matrix putting a head mesh into the body meshes' space.

    A head mesh is stored in its own bone-local frame (its "up" is +X, not +Y),
    and the head bone's world matrix is exactly the transform that places it.
    Body parts are skinned into the same skeleton space (see `_skin`), so no
    extra offset is needed - nothing is fitted or measured.
    """
    head_bone = skeleton().get("BIP01 HEAD")
    return tuple(head_bone) if head_bone else None


if __name__ == "__main__":
    for n in ("ITAR_BAU_L.MRM", "HUM_HEAD_PONY.MMB", "HUM_HEAD_FIGHTER.MMB",
              "HUM_BODY_NAKED0.MDM", "ARMOR_BAU_L.MDM"):
        m = load(n)
        if m:
            lo, hi = m.bounds()
            size = tuple(round(hi[i] - lo[i], 1) for i in range(3))
            print(f"{n:24} verts={len(m.positions):5} tris={len(m.triangles):5} "
                  f"size={size} tex={m.material_textures[:2]}")
        else:
            print(f"{n:24} FAILED")
