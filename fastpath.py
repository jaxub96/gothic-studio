"""
fastpath.py - optional numpy acceleration.

numpy is not required. If it is missing, `HAVE_NUMPY` is False and callers fall
back to the pure-Python code, so the app and the exe work exactly as before -
just slower. Nothing else in the project imports numpy directly.

Two hot spots are worth vectorising:

  * DXT texture decoding, which is a bulk per-pixel transform over hundreds of
    thousands of pixels - the ideal shape for numpy;
  * triangle rasterising, which is per-triangle and therefore pays numpy's
    per-call overhead many times. Whether that wins is an empirical question,
    so benchmark.py measures it rather than assuming.

Set GOTHIC_STUDIO_NO_NUMPY=1 to force the pure-Python path (used by the
benchmark to compare the two fairly in one process).
"""

import os

HAVE_NUMPY = False
np = None

if not os.environ.get("GOTHIC_STUDIO_NO_NUMPY"):
    try:
        import numpy as _np

        np = _np
        HAVE_NUMPY = True
    except ImportError:
        pass


# --- DXT decoding -----------------------------------------------------------

def decode_dxt(data, w, h, big):
    """DXT1 (big=False) / DXT3,DXT5 (big=True) -> RGB888 bytes, vectorised.

    Every 4x4 block is decoded at once instead of pixel by pixel: the two
    endpoint colours are unpacked for all blocks in parallel, the four-entry
    palette is built as an array, and the 2-bit indices select from it.
    """
    if not HAVE_NUMPY:
        return None

    bx = max(1, (w + 3) // 4)
    by = max(1, (h + 3) // 4)
    stride = 16 if big else 8
    need = bx * by * stride
    if len(data) < need:
        data = data + b"\x00" * (need - len(data))

    raw = np.frombuffer(data[:need], dtype=np.uint8).reshape(by, bx, stride)
    colour = raw[:, :, 8:16] if big else raw

    c0 = colour[:, :, 0].astype(np.uint16) | (colour[:, :, 1].astype(np.uint16) << 8)
    c1 = colour[:, :, 2].astype(np.uint16) | (colour[:, :, 3].astype(np.uint16) << 8)
    bits = (colour[:, :, 4].astype(np.uint32)
            | (colour[:, :, 5].astype(np.uint32) << 8)
            | (colour[:, :, 6].astype(np.uint32) << 16)
            | (colour[:, :, 7].astype(np.uint32) << 24))

    def unpack565(c):
        r = ((c >> 11) & 0x1F).astype(np.uint16)
        g = ((c >> 5) & 0x3F).astype(np.uint16)
        b = (c & 0x1F).astype(np.uint16)
        return (np.stack([(r << 3) | (r >> 2),
                          (g << 2) | (g >> 4),
                          (b << 3) | (b >> 2)], axis=-1).astype(np.int16))

    e0 = unpack565(c0)
    e1 = unpack565(c1)

    palette = np.empty((by, bx, 4, 3), dtype=np.int16)
    palette[:, :, 0] = e0
    palette[:, :, 1] = e1
    # DXT1 with c0 <= c1 uses a 3-colour block plus transparent; DXT3/5 always
    # use the 4-colour form.
    four = np.ones((by, bx), dtype=bool) if big else (c0 > c1)
    f = four[:, :, None]
    palette[:, :, 2] = np.where(f, (2 * e0 + e1) // 3, (e0 + e1) // 2)
    palette[:, :, 3] = np.where(f, (e0 + 2 * e1) // 3, 0)

    # 16 texels per block, 2 bits each
    shifts = (np.arange(16, dtype=np.uint32) * 2).reshape(4, 4)
    idx = (bits[:, :, None, None] >> shifts[None, None, :, :]) & 0x3

    bi, bj = np.meshgrid(np.arange(by), np.arange(bx), indexing="ij")
    texels = palette[bi[:, :, None, None], bj[:, :, None, None], idx]

    # (by, bx, 4, 4, 3) -> (by*4, bx*4, 3)
    img = texels.transpose(0, 2, 1, 3, 4).reshape(by * 4, bx * 4, 3)
    return np.ascontiguousarray(img[:h, :w].astype(np.uint8)).tobytes()


# --- Rasterising ------------------------------------------------------------

def make_frame(width, height, background):
    """Colour and depth buffers as numpy arrays."""
    colour = np.empty((height, width, 3), dtype=np.uint8)
    colour[:, :] = background
    depth = np.full((height, width), np.inf, dtype=np.float32)
    return colour, depth


def draw_triangle(colour, depth, sx, sy, sz, uvs, tex, shade, inv_area):
    """Fill one triangle, vectorised over its bounding box."""
    height, width = depth.shape
    x0 = max(0, int(min(sx)))
    x1 = min(width - 1, int(max(sx)) + 1)
    y0 = max(0, int(min(sy)))
    y1 = min(height - 1, int(max(sy)) + 1)
    if x0 > x1 or y0 > y1:
        return

    xs = np.arange(x0, x1 + 1, dtype=np.float32) + 0.5
    ys = np.arange(y0, y1 + 1, dtype=np.float32) + 0.5
    gx = xs[None, :]
    gy = ys[:, None]

    w0 = ((sx[1] - gx) * (sy[2] - gy) - (sx[2] - gx) * (sy[1] - gy)) * inv_area
    w1 = ((sx[2] - gx) * (sy[0] - gy) - (sx[0] - gx) * (sy[2] - gy)) * inv_area
    w2 = 1.0 - w0 - w1
    inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
    if not inside.any():
        return

    z = w0 * sz[0] + w1 * sz[1] + w2 * sz[2]
    sub_depth = depth[y0:y1 + 1, x0:x1 + 1]
    visible = inside & (z < sub_depth)
    if not visible.any():
        return

    sub_depth[visible] = z[visible]

    if tex is not None:
        tw, th, tdata = tex
        tarr = _as_array(tdata, tw, th)
        u = w0 * uvs[0][0] + w1 * uvs[1][0] + w2 * uvs[2][0]
        v = w0 * uvs[0][1] + w1 * uvs[1][1] + w2 * uvs[2][1]
        tx = (np.mod(u[visible], 1.0) * tw).astype(np.int32)
        ty = (np.mod(v[visible], 1.0) * th).astype(np.int32)
        np.clip(tx, 0, tw - 1, out=tx)
        np.clip(ty, 0, th - 1, out=ty)
        texel = tarr[ty, tx].astype(np.float32)
    else:
        texel = np.full((int(visible.sum()), 3), 235.0, dtype=np.float32)

    colour[y0:y1 + 1, x0:x1 + 1][visible] = (texel * shade).astype(np.uint8)


_ARRAY_CACHE = {}


def _as_array(tdata, tw, th):
    """Texture bytes as an (h, w, 3) array, cached - conversion is not free.

    The cache holds the source bytes alongside the array. np.frombuffer does
    not copy, so the array is a view into that buffer: if the bytes were
    collected the view would point at freed memory, and - because the cache is
    keyed by id() - a later object reusing that id would silently hand back the
    corrupt view. Keeping the reference makes both impossible.
    """
    key = (id(tdata), tw, th)
    hit = _ARRAY_CACHE.get(key)
    if hit is None:
        if len(_ARRAY_CACHE) > 64:
            _ARRAY_CACHE.clear()
        arr = np.frombuffer(tdata, dtype=np.uint8).reshape(th, tw, 3)
        hit = (tdata, arr)
        _ARRAY_CACHE[key] = hit
    return hit[1]


def frame_bytes(colour):
    return np.ascontiguousarray(colour).tobytes()
