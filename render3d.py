"""
render3d.py - a small software rasteriser for the NPC preview.

Deliberately not OpenGL: this has to work inside a frozen exe on any machine,
including over remote desktop and on boxes with no usable GL driver. The meshes
are tiny by modern standards (a clothed character is ~1400 triangles), so a
plain z-buffered scanline fill in Python renders a preview in well under a
second.

Gothic's world is Y-up and centimetre-scaled: a human is about 170 units tall.

numpy, when installed, is used for two different things with two different
answers, both measured by benchmark.py on this mod:

  * texture decoding is bulk per-pixel work and is ~9x faster with numpy, so
    it always uses it;
  * rasterising is per-triangle, and numpy's per-call overhead is paid ~1300
    times a frame. Its cost is almost flat with frame size while pure Python
    grows linearly, so numpy loses on small frames and wins on big ones. The
    two curves cross at roughly 125k pixels, which is the threshold below.

    frame     pure    numpy
     20k px   17ms     43ms     <- pure wins by 2.5x
    112k px   49ms     55ms
    147k px   61ms     56ms     <- crossover
    360k px  133ms     67ms     <- numpy wins by 2x

That matters in practice: dragging renders at half size, which lands in the
small-frame regime where pure Python is the faster path.
"""

import math

import textures

#: Below this many pixels the pure-Python rasteriser beats numpy. Measured;
#: re-run benchmark.py if the renderer changes.
RASTER_NUMPY_MIN_PIXELS = 125_000


class Model:
    """A mesh plus the texture it wears and where it sits in the world.

    `matrix` is an optional row-major 4x4 applied before drawing - used to put
    a head, which is stored in its own bone-local frame, onto a body.
    """

    __slots__ = ("mesh", "texture", "offset", "matrix", "submesh")

    def __init__(self, mesh, texture=None, offset=(0.0, 0.0, 0.0), matrix=None,
                 submesh=None):
        self.mesh = mesh
        self.texture = texture      # (w, h, rgb bytes) or None
        self.offset = offset
        self.matrix = matrix
        #: draw only this submesh; None means the whole mesh
        self.submesh = submesh


def load_texture(ref):
    return textures.decode(ref) if ref else None


def _submesh_texture(sub):
    """The texture a submesh's material names."""
    for name in sub.material_textures:
        ref = textures.find(name)
        if ref:
            decoded = textures.decode(ref)
            if decoded:
                return decoded
    return None


def character(npc):
    """Assemble one NPC: body (or its armor), plus the head on the head bone.

    Falls back gracefully - a missing head still renders the body, and a
    missing texture still renders shaded grey geometry.
    """
    import gamedata
    import mesh as meshlib

    models = []

    naked = npc.armor in ("-1", "", None)
    skin_tex = None
    value = gamedata.body_texture_values().get(npc.body_tex)
    if value is not None:
        skin_tex = load_texture(textures.body_texture(value))

    def add(mesh_obj, override=None, matrix=None):
        """One Model per submesh, so each material gets its own texture."""
        for sub in mesh_obj.submeshes:
            tex = override
            if tex is None:
                # Bare skin follows the NPC's chosen tone; everything else uses
                # whatever the material names.
                tex = skin_tex if (sub.is_skin and skin_tex) else _submesh_texture(sub)
            models.append(Model(mesh_obj, tex, matrix=matrix, submesh=sub))

    # An armor file usually holds more than one mesh - the garment plus the skin
    # that shows at the neck and hands, or a matching helm. Drawing only the
    # first leaves a hole where the neck should be.
    parts = meshlib.body_meshes(None if naked else npc.armor,
                                female=str(npc.gender).upper() == "FEMALE")
    for part in parts:
        add(part)

    head = meshlib.head_mesh(npc.head)
    if head and parts:
        value = gamedata.face_values().get(npc.face)
        face_tex = load_texture(textures.face_texture(value)) if value is not None else None
        add(head, override=face_tex, matrix=meshlib.head_placement())
    return models


#: Rendering is done at this multiple of the requested size and averaged back
#: down. The rasteriser has no edge smoothing and samples textures at the
#: nearest texel, so a plain render shows stair-stepped silhouettes and
#: shimmering skin; averaging a 2x2 block per pixel fixes both.
SUPERSAMPLE = 2
SUPERSAMPLE_MAX_PIXELS = 4_000_000


def render(models, width=320, height=460, yaw=25.0, pitch=8.0,
           background=(0xF5, 0xED, 0xD6), margin=0.06,
           zoom=1.0, pan=(0.0, 0.0), wireframe=False, textured=True,
           supersample=None):
    """Rasterise `models` to (width, height, rgb888 bytes), anti-aliased.

    `supersample` is the oversampling factor (1 turns it off). The default is
    SUPERSAMPLE when numpy is available and the frame is not huge; without
    numpy the averaging would cost more than the render, so it is skipped.
    Wireframes are 1px lines, which averaging would only wash out.
    """
    import fastpath
    n = SUPERSAMPLE if supersample is None else int(supersample)
    if (n < 2 or wireframe or not fastpath.HAVE_NUMPY
            or width * height * n * n > SUPERSAMPLE_MAX_PIXELS):
        return _render(models, width, height, yaw, pitch, background, margin,
                       zoom, pan, wireframe, textured)

    big = _render(models, width * n, height * n, yaw, pitch, background, margin,
                  zoom, (pan[0] * n, pan[1] * n), wireframe, textured)
    if not big:
        return None
    np = fastpath.np
    frame = np.frombuffer(big[2], dtype=np.uint8).reshape(height, n, width, n, 3)
    small = frame.mean(axis=(1, 3)).round().astype(np.uint8)
    return width, height, small.tobytes()


def bounds(models):
    """(half_w, half_h) of the models' world bounding box, as _render frames it.

    half_w takes the wider of X and Z, so it does not change as the figure
    turns. None when there is nothing to draw.
    """
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for model in models:
        if not model.mesh:
            continue
        off = model.offset
        pos = model.mesh.positions
        if model.matrix:
            import mesh as _mesh
            pos = [_mesh.transform_point(model.matrix, p) for p in pos]
        source = model.submesh.triangles if model.submesh else model.mesh.triangles
        for tri in source:
            for w in tri:
                if w[0] >= len(pos):
                    continue
                p = pos[w[0]]
                for i in range(3):
                    v = p[i] + off[i]
                    if v < lo[i]:
                        lo[i] = v
                    if v > hi[i]:
                        hi[i] = v
    if lo[0] == math.inf:
        return None
    half_h = max(hi[1] - lo[1], 1e-6) / 2
    half_w = max(hi[0] - lo[0], hi[2] - lo[2], 1e-6) / 2
    return half_w, half_h


def fit_scale(half_w, half_h, width, height, margin=0.06, zoom=1.0):
    """Pixels per world unit that frame a box of this size, times zoom."""
    return min(width * (1 - 2 * margin) / (2 * half_w),
               height * (1 - 2 * margin) / (2 * half_h)) * zoom


def _render(models, width, height, yaw, pitch, background, margin,
            zoom, pan, wireframe, textured):
    """One pass at exactly the size asked for. See `render`.

    Orthographic, so UV interpolation can be affine without visible warping.
    The camera frames everything automatically - which keeps a head and a full
    body both filling the panel - and `zoom`/`pan` adjust from there.
    """
    tris = []
    for model in models:
        if not model.mesh:
            continue
        ox, oy, oz = model.offset
        pos = model.mesh.positions
        if model.matrix:
            import mesh as _mesh
            pos = [_mesh.transform_point(model.matrix, p) for p in pos]
        tex = model.texture
        source = model.submesh.triangles if model.submesh else model.mesh.triangles
        for tri in source:
            try:
                p = [pos[w[0]] for w in tri]
            except IndexError:
                continue
            tris.append((
                [(p[i][0] + ox, p[i][1] + oy, p[i][2] + oz) for i in range(3)],
                [(tri[i][1], tri[i][2]) for i in range(3)],
                tex,
            ))
    if not tris:
        return None

    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))

    def transform(v):
        x, y, z = v
        x, z = x * cy + z * sy, -x * sy + z * cy       # yaw about Y
        y, z = y * cp - z * sp, y * sp + z * cp        # pitch about X
        return x, y, z

    view = [([transform(v) for v in vs], uvs, tex) for vs, uvs, tex in tris]

    # Frame on the model's bounding box in world space, not on the rotated
    # silhouette: otherwise the figure would grow and shrink as you turn it.
    wxs = [v[0] for vs, _, _ in tris for v in vs]
    wys = [v[1] for vs, _, _ in tris for v in vs]
    wzs = [v[2] for vs, _, _ in tris for v in vs]
    centre = ((min(wxs) + max(wxs)) / 2,
              (min(wys) + max(wys)) / 2,
              (min(wzs) + max(wzs)) / 2)
    half_h = max(max(wys) - min(wys), 1e-6) / 2
    half_w = max(max(wxs) - min(wxs), max(wzs) - min(wzs), 1e-6) / 2

    scale = fit_scale(half_w, half_h, width, height, margin, zoom)
    cx, ccy, _ = transform(centre)
    ox = width / 2 - cx * scale + pan[0]
    oy = height / 2 + ccy * scale + pan[1]            # flip Y for screen

    import fastpath
    use_numpy = fastpath.HAVE_NUMPY and (width * height) >= RASTER_NUMPY_MIN_PIXELS

    br, bg, bb = background
    if use_numpy:
        colour_buf, depth_buf = fastpath.make_frame(width, height, background)
    else:
        buf = bytearray(bytes((br, bg, bb)) * (width * height))
        zbuf = [1e30] * (width * height)

    light = (-0.35, 0.55, -0.75)
    ln = math.sqrt(sum(c * c for c in light))
    light = tuple(c / ln for c in light)

    if wireframe:
        ink = (max(0, br - 110), max(0, bg - 110), max(0, bb - 110))
        if use_numpy:
            def set_pixel(px, py):
                colour_buf[py, px] = ink
        else:
            def set_pixel(px, py, _i=ink):
                o = (py * width + px) * 3
                buf[o], buf[o + 1], buf[o + 2] = _i
    else:
        set_pixel = None

    for vs, uvs, tex in view:
        sx = [v[0] * scale + ox for v in vs]
        sy = [oy - v[1] * scale for v in vs]
        sz = [v[2] for v in vs]

        area = (sx[1] - sx[0]) * (sy[2] - sy[0]) - (sx[2] - sx[0]) * (sy[1] - sy[0])
        if area >= -1e-9:                              # back-facing or degenerate
            continue
        inv_area = 1.0 / area

        # flat shading from the geometric normal - enough to read the silhouette
        ax, ay, az = (vs[1][0] - vs[0][0], vs[1][1] - vs[0][1], vs[1][2] - vs[0][2])
        bx2, by2, bz2 = (vs[2][0] - vs[0][0], vs[2][1] - vs[0][1], vs[2][2] - vs[0][2])
        nx, ny, nz = (ay * bz2 - az * by2, az * bx2 - ax * bz2, ax * by2 - ay * bx2)
        nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        lam = (nx * light[0] + ny * light[1] + nz * light[2]) / nl
        shade = 0.62 + 0.38 * max(0.0, lam)

        x0 = max(0, int(min(sx)));  x1 = min(width - 1, int(max(sx)) + 1)
        y0 = max(0, int(min(sy)));  y1 = min(height - 1, int(max(sy)) + 1)
        if x0 > x1 or y0 > y1:
            continue

        if not textured:
            tex = None

        if wireframe:
            _wire(set_pixel, sx, sy, width, height)
            continue

        if use_numpy:
            fastpath.draw_triangle(colour_buf, depth_buf, sx, sy, sz, uvs,
                                   tex, shade, inv_area)
            continue

        # Barycentric weights are linear in screen space, so step them across
        # the scanline instead of recomputing two cross products per pixel.
        a0 = (sy[1] - sy[2]) * inv_area
        a1 = (sy[2] - sy[0]) * inv_area

        z0, z1, z2 = sz
        if tex:
            tw, th, tdata = tex
            u0, v0 = uvs[0]
            du1 = uvs[1][0] - u0; dv1 = uvs[1][1] - v0
            du2 = uvs[2][0] - u0; dv2 = uvs[2][1] - v0
        else:
            flat = int(235 * shade)

        for py in range(y0, y1 + 1):
            fy = py + 0.5
            row = py * width
            fx = x0 + 0.5
            w0 = ((sx[1] - fx) * (sy[2] - fy) - (sx[2] - fx) * (sy[1] - fy)) * inv_area
            w1 = ((sx[2] - fx) * (sy[0] - fy) - (sx[0] - fx) * (sy[2] - fy)) * inv_area
            for px in range(x0, x1 + 1):
                if w0 >= 0.0 and w1 >= 0.0:
                    w2 = 1.0 - w0 - w1
                    if w2 >= 0.0:
                        idx = row + px
                        z = w0 * z0 + w1 * z1 + w2 * z2
                        if z < zbuf[idx]:
                            zbuf[idx] = z
                            o = idx * 3
                            if tex:
                                u = u0 + w1 * du1 + w2 * du2
                                v = v0 + w1 * dv1 + w2 * dv2
                                ti = ((int(v % 1.0 * th) * tw) + int(u % 1.0 * tw)) * 3
                                buf[o] = int(tdata[ti] * shade)
                                buf[o + 1] = int(tdata[ti + 1] * shade)
                                buf[o + 2] = int(tdata[ti + 2] * shade)
                            else:
                                buf[o] = buf[o + 1] = buf[o + 2] = flat
                w0 += a0
                w1 += a1

    if use_numpy:
        return width, height, fastpath.frame_bytes(colour_buf)
    return width, height, bytes(buf)


def _wire(set_pixel, sx, sy, width, height):
    """Outline one triangle - Bresenham over its three edges."""
    for i in range(3):
        x0, y0 = int(sx[i]), int(sy[i])
        x1, y1 = int(sx[(i + 1) % 3]), int(sy[(i + 1) % 3])
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        step_x = 1 if x0 < x1 else -1
        step_y = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            if 0 <= x0 < width and 0 <= y0 < height:
                set_pixel(x0, y0)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += step_x
            if e2 <= dx:
                err += dx
                y0 += step_y
