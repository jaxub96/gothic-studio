"""
benchmark.py - does numpy actually make the preview faster?

    python benchmark.py

Runs the same work twice in two subprocesses, one with numpy enabled and one
with GOTHIC_STUDIO_NO_NUMPY=1, and compares. It also checks the two paths
produce the *same picture*, because a fast renderer that draws something
different is not an optimisation.

Reports per stage, since the answer differs by stage: bulk pixel work
vectorises well, per-triangle work has to overcome numpy's call overhead.
"""

import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPEATS = 5


def _time(fn, repeats=REPEATS):
    """Best-of-N wall time. Best, not mean: it is the least noisy estimate."""
    fn()                                   # warm caches
    runs = []
    for _ in range(repeats):
        t = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - t)
    return min(runs), statistics.median(runs)


def run_suite():
    """The measurements themselves. Runs inside each subprocess."""
    sys.path.insert(0, str(HERE))
    import fastpath
    import npc_model
    import render3d
    import textures

    results = {"numpy": fastpath.HAVE_NUMPY}

    npc = npc_model.Npc()
    npc.armor = "ITAR_PAL_H"
    npc.head = "HUM_HEAD_FIGHTER"
    npc.face = "Face_B_Thorus"

    # --- texture decode (bulk per-pixel work) --------------------------------
    ref = textures.armor_texture("ITAR_PAL_H")
    raw = ref.data()
    best, med = _time(lambda: textures._decode_raw(raw))
    decoded = textures._decode_raw(raw)
    results["decode_512"] = best
    results["decode_512_med"] = med
    results["decode_size"] = f"{decoded[0]}x{decoded[1]}"

    face = textures.find("HUM_HEAD_V4_C0")
    raw_face = face.data()
    best, med = _time(lambda: textures._decode_raw(raw_face))
    results["decode_256"] = best

    # --- rasterising (per-triangle work) -------------------------------------
    models = render3d.character(npc)
    results["triangles"] = sum(len(m.mesh.triangles) for m in models)
    for w, h in ((160, 230), (320, 460), (640, 920)):
        best, med = _time(lambda w=w, h=h: render3d.render(models, w, h))
        results[f"render_{w}x{h}"] = best

    # --- a full frame from cold ----------------------------------------------
    def cold_frame():
        textures._decoded.clear()
        render3d.character.__wrapped__ if hasattr(render3d.character, "__wrapped__") else None
        m = render3d.character(npc)
        render3d.render(m, 320, 460)

    best, med = _time(cold_frame, repeats=3)
    results["cold_frame"] = best

    # --- image equality check ------------------------------------------------
    img = render3d.render(models, 200, 300)
    results["checksum"] = sum(img[2][::997])
    results["pixels"] = len(img[2])
    return results


def main():
    if os.environ.get("BENCH_CHILD"):
        import json
        print("RESULT " + json.dumps(run_suite()))
        return 0

    import json
    out = {}
    for label, env_extra in (("numpy", {}), ("pure", {"GOTHIC_STUDIO_NO_NUMPY": "1"})):
        env = dict(os.environ, BENCH_CHILD="1", PYTHONIOENCODING="utf-8", **env_extra)
        proc = subprocess.run([sys.executable, str(Path(__file__))],
                              capture_output=True, text=True, env=env, cwd=str(HERE))
        line = next((l for l in proc.stdout.splitlines() if l.startswith("RESULT ")), None)
        if not line:
            print(f"{label}: FAILED\n{proc.stdout}\n{proc.stderr}")
            return 1
        out[label] = json.loads(line[len("RESULT "):])

    n, p = out["numpy"], out["pure"]
    if not n["numpy"]:
        print("numpy is not installed - nothing to compare.")
        return 1

    print(f"triangles per frame: {n['triangles']}     "
          f"armor texture: {n['decode_size']}")
    print(f"repeats: {REPEATS}, best-of shown\n")
    print(f"{'stage':<24}{'pure python':>14}{'numpy':>12}{'speed-up':>12}")
    print("-" * 62)

    import render3d
    threshold = render3d.RASTER_NUMPY_MIN_PIXELS

    rows = [
        ("decode 512x512 DXT", "decode_512", None),
        ("decode 256x128 DXT", "decode_256", None),
        ("render 160x230", "render_160x230", 160 * 230),
        ("render 320x460", "render_320x460", 320 * 460),
        ("render 640x920", "render_640x920", 640 * 920),
        ("cold frame (both)", "cold_frame", None),
    ]
    for label, key, pixels in rows:
        pv, nv = p[key], n[key]
        ratio = pv / nv if nv else float("inf")
        if pixels is not None and pixels < threshold:
            note = "   (pure path chosen)"
        elif ratio < 0.98:
            note = "   <-- SLOWER"
        else:
            note = ""
        print(f"{label:<24}{pv * 1000:>12.1f}ms{nv * 1000:>10.1f}ms"
              f"{ratio:>11.1f}x{note}")

    print(f"\nrasteriser switches to numpy above {threshold:,} pixels "
          f"(render3d.RASTER_NUMPY_MIN_PIXELS)")
    print("texture decoding always uses numpy when it is installed")

    print()
    same = n["checksum"] == p["checksum"] and n["pixels"] == p["pixels"]
    print(f"identical output: {'yes' if same else 'NO - the two paths disagree'}"
          f"   (checksum {n['checksum']} vs {p['checksum']})")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
