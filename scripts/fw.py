#!/usr/bin/env python3
"""fractalwright CLI: render, measure and explain fractals.

Standard library first. NumPy is the reference core (probed; renders and
measures fall back to pure Python for small sizes). Pillow is optional (a
stdlib PNG writer is built in). Playwright and moderngl are only probed.

Commands: doctor, explain, render, measure, palette.
"""
import argparse
import importlib.util
import json
import math
import shutil
import struct
import sys
import zlib
from decimal import Decimal
from pathlib import Path

VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parent.parent

try:
    import numpy as np
except ImportError:  # pragma: no cover - probed by doctor
    np = None

FAMILIES = ("mandelbrot", "julia", "burning-ship", "tricorn", "multibrot")

EXPLAIN = {
    "mandelbrot": ("z <- z^2 + c, z0 = 0, c = pixel",
                   "Escape time: iterate each pixel's c until |z| > R or max_iter. Points that never escape form the set (area ~1.50659). Smooth colour mu = n + 1 - log(log|z|)/log 2 with R >= 256.",
                   "references/02-escape-time.md#mandelbrot"),
    "julia": ("z <- z^2 + k, z0 = pixel, k fixed",
              "Same loop as Mandelbrot but the pixel is the start point and k is a constant. k inside the Mandelbrot set gives a connected Julia set, outside it a dust. Recipe params.c holds k as two decimal strings.",
              "references/02-escape-time.md#julia-filled-julia-sets"),
    "burning-ship": ("z <- (|Re z| + i|Im z|)^2 + c",
                     "Absolute values before squaring break the conjugate symmetry; the classic view is drawn with the imaginary axis flipped so the ship sits upright (fw.py flips by default: params.flip_y).",
                     "references/02-escape-time.md#burning-ship"),
    "tricorn": ("z <- conj(z)^2 + c",
                "The Mandelbar: conjugate before squaring. Three-fold symmetry, mirror symmetric across the real axis.",
                "references/02-escape-time.md#tricorn--mandelbar"),
    "multibrot": ("z <- z^d + c (params.power = d)",
                  "Generalised Mandelbrot with d-1 fold rotational symmetry. Smooth colour divides by log d.",
                  "references/02-escape-time.md#multibrot"),
}

PRESETS = {
    "mandelbrot-full": {"formula": "mandelbrot", "view": {"centre": ["-0.75", "0"], "width": "3.5"}},
    "seahorse": {"formula": "mandelbrot", "params": {"max_iter": 1000},
                 "view": {"centre": ["-0.7436447860", "0.1318252536"], "width": "1e-4"}},
    "julia-dendrite": {"formula": "julia", "params": {"c": ["0", "1"]},
                       "view": {"centre": ["0", "0"], "width": "3.2"}},
    "julia-rabbit": {"formula": "julia", "params": {"c": ["-0.123", "0.745"]},
                     "view": {"centre": ["0", "0"], "width": "3.2"}},
    "burning-ship-full": {"formula": "burning-ship", "view": {"centre": ["-0.45", "-0.5"], "width": "3.6"}},
    "burning-ship-armada": {"formula": "burning-ship", "params": {"max_iter": 500},
                            "view": {"centre": ["-1.762", "-0.028"], "width": "0.08"}},
    "tricorn-full": {"formula": "tricorn", "view": {"centre": ["-0.3", "0"], "width": "4"}},
    "multibrot-3": {"formula": "multibrot", "params": {"power": 3}, "view": {"centre": ["0", "0"], "width": "3.2"}},
}

PALETTES = {
    "classic": {"type": "cosine", "a": [0.5, 0.5, 0.5], "b": [0.5, 0.5, 0.5], "c": [1, 1, 1], "d": [0.0, 0.33, 0.67]},
    "fire": {"type": "cosine", "a": [0.5, 0.3, 0.1], "b": [0.5, 0.4, 0.2], "c": [1, 1, 1], "d": [0.0, 0.1, 0.2]},
    "ocean": {"type": "cosine", "a": [0.2, 0.4, 0.6], "b": [0.2, 0.3, 0.4], "c": [1, 1, 1], "d": [0.3, 0.2, 0.1]},
    "ultra": {"type": "stops", "stops": [[0.0, "#000764"], [0.16, "#206bcb"], [0.42, "#edffff"],
                                         [0.6425, "#ffaa00"], [0.8575, "#000200"], [1.0, "#000764"]]},
    "grey": {"type": "stops", "stops": [[0.0, "#000000"], [0.5, "#ffffff"], [1.0, "#000000"]]},
}


# ---------------------------------------------------------------- recipes
def default_recipe():
    return {
        "fractalwright": VERSION,
        "family": "escape-time",
        "formula": "mandelbrot",
        "params": {"power": 2, "bailout": 256, "max_iter": 500},
        "view": {"centre": ["-0.75", "0"], "width": "3.5", "rotation_deg": 0},
        "size": {"w": 800, "h": 600, "supersample": 1},
        "colouring": {"method": "smooth", "density": 0.02, "inside": "#000000"},
        "palette": dict(PALETTES["classic"]),
        "seed": 0,
        "render": {"route": "numpy", "precision": "float64"},
        "ai_pass": None,
    }


def _merge(base, over):
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load_recipe(spec):
    """spec: a preset name or a path to a recipe JSON."""
    r = default_recipe()
    if spec in PRESETS:
        return _merge(r, json.loads(json.dumps(PRESETS[spec])))
    p = Path(spec)
    if not p.is_file():
        raise SystemExit(f"no preset or file named {spec!r}; presets: {', '.join(PRESETS)}")
    return _merge(r, json.loads(p.read_text(encoding="utf-8")))


def normalise(r):
    if r["formula"] not in FAMILIES:
        raise SystemExit(f"unknown formula {r['formula']!r}; known: {', '.join(FAMILIES)}")
    v = r["view"]
    v["centre"] = [str(Decimal(str(x))) for x in v["centre"]]
    v["width"] = str(Decimal(str(v["width"])))
    if r["formula"] == "julia":
        r["params"].setdefault("c", ["-0.8", "0.156"])
        r["params"]["c"] = [str(Decimal(str(x))) for x in r["params"]["c"]]
    if r["formula"] == "burning-ship":
        r["params"].setdefault("flip_y", True)
    if r["formula"] != "multibrot":
        r["params"]["power"] = 2
    if isinstance(r.get("palette"), str):
        r["palette"] = dict(PALETTES[r["palette"]])
    return r


# ---------------------------------------------------------------- palettes
def _hex(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def palette_rgb(pal, t):
    """t: float array (any shape) -> float array (..., 3) in 0..1. NumPy path."""
    if pal["type"] == "cosine":
        a, b, c, d = (np.array(pal[k], float) for k in "abcd")
        return a + b * np.cos(2 * math.pi * (c * t[..., None] + d))
    stops = pal["stops"]
    pos = np.array([s[0] for s in stops], float)
    cols = np.array([_hex(s[1]) for s in stops], float)
    f = np.mod(t, 1.0)
    return np.stack([np.interp(f, pos, cols[:, k]) for k in range(3)], -1)


def palette_rgb_py(pal, t):
    if pal["type"] == "cosine":
        return [pal["a"][k] + pal["b"][k] * math.cos(2 * math.pi * (pal["c"][k] * t + pal["d"][k])) for k in range(3)]
    stops = pal["stops"]
    f = t % 1.0
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if p0 <= f <= p1:
            u = 0.0 if p1 == p0 else (f - p0) / (p1 - p0)
            a, b = _hex(c0), _hex(c1)
            return [a[k] + (b[k] - a[k]) * u for k in range(3)]
    return _hex(stops[-1][1])


# ---------------------------------------------------------------- core
def _grid(r):
    w, h = r["size"]["w"], r["size"]["h"]
    ss = int(r["size"].get("supersample", 1) or 1)
    W, H = w * ss, h * ss
    cx, cy = (float(Decimal(x)) for x in r["view"]["centre"])
    px = float(Decimal(r["view"]["width"])) / W
    xs = cx + (np.arange(W) + 0.5 - W / 2) * px
    # rows top to bottom; offsets are exact negatives about the centre
    ys = cy + (H / 2 - (np.arange(H) + 0.5)) * px
    rot = math.radians(float(r["view"].get("rotation_deg", 0) or 0))
    X, Y = np.meshgrid(xs, ys)
    if rot:
        dx, dy = X - cx, Y - cy
        X, Y = cx + dx * math.cos(rot) - dy * math.sin(rot), cy + dx * math.sin(rot) + dy * math.cos(rot)
    if r["formula"] == "burning-ship" and r["params"].get("flip_y"):
        Y = 2 * cy - Y
    return X, Y, ss


def escape_numpy(r, X, Y):
    """Return (nu, inside) as float64 smooth counts and a bool mask."""
    p = r["params"]
    f, d = r["formula"], int(p.get("power", 2))
    maxit, R2 = int(p["max_iter"]), float(p["bailout"]) ** 2
    if f == "julia":
        zr, zi = X.copy(), Y.copy()
        kr, ki = (float(Decimal(x)) for x in p["c"])
        cr, ci = np.full_like(X, kr), np.full_like(X, ki)
    else:
        zr, zi = np.zeros_like(X), np.zeros_like(X)
        cr, ci = X, Y
    shape = X.shape
    zr, zi, cr, ci = zr.ravel(), zi.ravel(), cr.ravel(), ci.ravel()
    n_out = np.full(zr.size, -1, np.int64)
    m_out = np.zeros(zr.size)
    idx = np.arange(zr.size)
    for n in range(maxit):
        if f == "burning-ship":
            zr, zi = np.abs(zr), np.abs(zi)
        elif f == "tricorn":
            zi = -zi
        if d == 2:
            zr, zi = zr * zr - zi * zi + cr, 2 * zr * zi + ci
        else:
            z = (zr + 1j * zi) ** d
            zr, zi = z.real + cr, z.imag + ci
        m = zr * zr + zi * zi
        esc = m > R2
        if esc.any():
            n_out[idx[esc]] = n + 1
            m_out[idx[esc]] = m[esc]
            keep = ~esc
            zr, zi, cr, ci, idx = zr[keep], zi[keep], cr[keep], ci[keep], idx[keep]
            if idx.size == 0:
                break
    inside = n_out < 0
    nu = np.zeros(n_out.size)
    e = ~inside
    nu[e] = n_out[e] + 1 - np.log(np.log(m_out[e]) / 2) / math.log(d)
    return nu.reshape(shape), inside.reshape(shape)


def colour(r, nu, inside):
    c = r["colouring"]
    rgb = palette_rgb(r["palette"], nu * float(c.get("density", 0.02)))
    rgb[inside] = _hex(c.get("inside", "#000000"))
    return rgb


def render_array(r):
    """Recipe -> uint8 HxWx3 (NumPy)."""
    r = normalise(r)
    X, Y, ss = _grid(r)
    nu, inside = escape_numpy(r, X, Y)
    rgb = colour(r, nu, inside)
    if ss > 1:
        h, w = r["size"]["h"], r["size"]["w"]
        rgb = rgb.reshape(h, ss, w, ss, 3).mean(axis=(1, 3))
    return np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)


def render_rows_py(r):
    """Pure-Python fallback: list of rows of bytes. Slow; small sizes only."""
    r = normalise(r)
    w, h = r["size"]["w"], r["size"]["h"]
    p = r["params"]
    f, d = r["formula"], int(p.get("power", 2))
    maxit, R2 = int(p["max_iter"]), float(p["bailout"]) ** 2
    cx, cy = (float(Decimal(x)) for x in r["view"]["centre"])
    px = float(Decimal(r["view"]["width"])) / w
    dens = float(r["colouring"].get("density", 0.02))
    ins = bytes(int(v * 255 + 0.5) for v in _hex(r["colouring"].get("inside", "#000000")))
    rows = []
    for j in range(h):
        y = cy + (h / 2 - (j + 0.5)) * px
        if f == "burning-ship" and p.get("flip_y"):
            y = 2 * cy - y
        row = bytearray()
        for i in range(w):
            x = cx + (i + 0.5 - w / 2) * px
            if f == "julia":
                z = complex(x, y)
                c = complex(*(float(Decimal(v)) for v in p["c"]))
            else:
                z, c = 0j, complex(x, y)
            out = None
            for n in range(maxit):
                if f == "burning-ship":
                    z = complex(abs(z.real), abs(z.imag))
                elif f == "tricorn":
                    z = z.conjugate()
                z = z ** d + c if d != 2 else z * z + c
                m = z.real * z.real + z.imag * z.imag
                if m > R2:
                    out = n + 1 + 1 - math.log(math.log(m) / 2) / math.log(d)
                    break
            if out is None:
                row += ins
            else:
                row += bytes(min(255, max(0, int(v * 255 + 0.5))) for v in palette_rgb_py(r["palette"], out * dens))
        rows.append(bytes(row))
    return rows


# ---------------------------------------------------------------- PNG
def write_png(path, arr=None, rows=None, w=None, h=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if arr is not None:
        h, w = arr.shape[:2]
        if arr.ndim == 2:
            arr = np.repeat(arr[..., None], 3, -1)
        rows = [arr[j].tobytes() for j in range(h)]
    raw = b"".join(b"\x00" + row for row in rows)

    def chunk(t, data):
        return struct.pack(">I", len(data)) + t + data + struct.pack(">I", zlib.crc32(t + data) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    path.write_bytes(png)
    return path


def read_mask(path, threshold=128, invert=False):
    """Read an image to a bool mask (True = filled). Needs Pillow."""
    from PIL import Image
    a = np.asarray(Image.open(path).convert("L"))
    m = a < threshold if not invert else a >= threshold
    return m


# ---------------------------------------------------------------- measure
def box_dimension(mask, sizes=None):
    """Box-counting dimension of a bool mask. Returns (D, [(s, N)]).

    Box sizes are powers of two from 2 px up to 1/8 of the shorter side; the
    image is padded to a multiple of the largest box. Slope of log N against
    log(1/s) by least squares.
    """
    mask = np.asarray(mask, bool)
    h, w = mask.shape
    if sizes is None:
        sizes, s = [], 2
        while s <= min(h, w) // 8:
            sizes.append(s)
            s *= 2
    smax = max(sizes)
    H, W = -(-h // smax) * smax, -(-w // smax) * smax
    m = np.zeros((H, W), bool)
    m[:h, :w] = mask
    pts = []
    for s in sizes:
        n = int(m.reshape(H // s, s, W // s, s).any(axis=(1, 3)).sum())
        pts.append((s, n))
    xs = np.log([1.0 / s for s, _ in pts])
    ys = np.log([max(n, 1) for _, n in pts])
    slope = float(np.polyfit(xs, ys, 1)[0])
    return slope, pts


def _in_cardioid_or_bulb(cr, ci):
    q = (cr - 0.25) ** 2 + ci * ci
    card = q * (q + (cr - 0.25)) <= 0.25 * ci * ci
    bulb = (cr + 1) ** 2 + ci * ci <= 1 / 16
    return card | bulb


def mandelbrot_area(n=1024, max_iter=10000):
    """Pixel-count area of the Mandelbrot set on an n x n grid over
    [-2, 0.5] x [-1.25, 1.25] (pixel centres). Uses the real-axis mirror
    (upper half only) and skips the main cardioid and period-2 bulb, which
    are inside by formula."""
    if n % 2:
        raise ValueError("n must be even")
    span = 2.5
    px = span / n
    xs = -2.0 + (np.arange(n) + 0.5) * px
    ys = (np.arange(n // 2) + 0.5) * px          # upper half, centres
    X, Y = np.meshgrid(xs, ys)
    cr, ci = X.ravel(), Y.ravel()
    known = _in_cardioid_or_bulb(cr, ci)
    cr, ci = cr[~known], ci[~known]
    zr, zi = np.zeros_like(cr), np.zeros_like(ci)
    for _ in range(max_iter):
        zr, zi = zr * zr - zi * zi + cr, 2 * zr * zi + ci
        keep = zr * zr + zi * zi <= 4.0
        if not keep.all():
            zr, zi, cr, ci = zr[keep], zi[keep], cr[keep], ci[keep]
            if cr.size == 0:
                break
    inside = int(known.sum()) + cr.size
    return 2 * inside * px * px


# ---------------------------------------------------------------- commands
def cmd_doctor(a):
    def has(m):
        return importlib.util.find_spec(m) is not None
    rows = [("python", sys.version.split()[0], "required (3.9+)")]
    rows.append(("numpy", np.__version__ if np is not None else "missing", "core: render, measure (pure Python fallback for small renders)"))
    pil = "missing"
    if has("PIL"):
        import PIL
        pil = PIL.__version__
    rows.append(("Pillow", pil, "optional: measure on image files (PNG writing is built in)"))
    mgl = "missing"
    if has("moderngl"):
        try:
            import moderngl
            ctx = moderngl.create_standalone_context()
            mgl = f"{moderngl.__version__} ({ctx.info.get('GL_RENDERER', '?')})"
            ctx.release()
        except Exception as e:  # noqa: BLE001
            mgl = f"installed, no context: {e.__class__.__name__}"
    rows.append(("moderngl", mgl, "optional accelerator: float64 GLSL stills (not wired yet)"))
    rows.append(("playwright", "installed" if has("playwright") else "missing", "optional accelerator: WebGL2 page and frames (not wired yet)"))
    browsers = [b for b in ("msedge", "chrome", "google-chrome", "chromium") if shutil.which(b)]
    edge = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    if edge.exists():
        browsers.append("msedge")
    rows.append(("browser", ", ".join(sorted(set(browsers))) or "none on PATH", "for the playwright route"))
    rows.append(("ffmpeg", shutil.which("ffmpeg") or "missing", "optional: video commands (later)"))
    if a.json:
        print(json.dumps([{"name": n, "value": v, "role": r} for n, v, r in rows], indent=2))
    else:
        for n, v, r in rows:
            print(f"{n:11} {v:40} {r}")
    return 0


def cmd_explain(a):
    fam = a.family.lower()
    if fam not in EXPLAIN:
        print(f"unknown family {fam!r}; known: {', '.join(EXPLAIN)}", file=sys.stderr)
        return 2
    formula, how, ref = EXPLAIN[fam]
    presets = [k for k, v in PRESETS.items() if v["formula"] == fam]
    print(f"{fam}\n  formula: {formula}\n  how: {how}\n  presets: {', '.join(presets) or '-'}\n  more: {ref}")
    return 0


def cmd_render(a):
    r = load_recipe(a.recipe)
    if a.size:
        w, h = a.size.lower().split("x")
        r["size"]["w"], r["size"]["h"] = int(w), int(h)
    if a.iter:
        r["params"]["max_iter"] = a.iter
    if a.palette:
        r["palette"] = dict(PALETTES[a.palette])
    if a.supersample:
        r["size"]["supersample"] = a.supersample
    r = normalise(r)
    out = Path(a.out)
    if np is not None:
        r["render"] = {"route": "numpy", "precision": "float64"}
        write_png(out, arr=render_array(r))
    else:
        if r["size"]["w"] * r["size"]["h"] > 200_000:
            print("NumPy missing: pure Python is limited to 200k pixels; pass --size", file=sys.stderr)
            return 3
        r["render"] = {"route": "python", "precision": "float64"}
        write_png(out, rows=render_rows_py(r), w=r["size"]["w"], h=r["size"]["h"])
    rec = out.with_suffix(".json")
    rec.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} and {rec}")
    return 0


def cmd_measure(a):
    if np is None:
        print("measure needs NumPy (pip install numpy)", file=sys.stderr)
        return 3
    if a.what == "area":
        A = mandelbrot_area(a.size, a.iter)
        res = {"measure": "mandelbrot-area", "size": a.size, "max_iter": a.iter, "area": A,
               "reference": 1.50659177, "error": A - 1.50659177}
    else:
        if not a.image:
            print("measure box needs an image path", file=sys.stderr)
            return 2
        D, pts = box_dimension(read_mask(a.image, a.threshold, a.invert))
        res = {"measure": "box-dimension", "image": a.image, "dimension": D, "boxes": pts}
    print(json.dumps(res, indent=2) if a.json else "\n".join(f"{k}: {v}" for k, v in res.items()))
    return 0


def cmd_palette(a):
    if not a.name:
        for k, v in PALETTES.items():
            print(f"{k:8} {v['type']}")
        return 0
    pal = PALETTES.get(a.name)
    if pal is None:
        print(f"unknown palette {a.name!r}", file=sys.stderr)
        return 2
    if a.out:
        w, h = 512, 48
        if np is not None:
            t = np.tile(np.linspace(0, 1, w, endpoint=False), (h, 1))
            write_png(a.out, arr=np.clip(palette_rgb(pal, t) * 255 + 0.5, 0, 255).astype(np.uint8))
        else:
            row = bytes(min(255, max(0, int(v * 255 + 0.5))) for i in range(w) for v in palette_rgb_py(pal, i / w))
            write_png(a.out, rows=[row] * h, w=w, h=h)
        print(f"wrote {a.out}")
    else:
        print(json.dumps(pal, indent=2))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fw.py", description=__doc__.splitlines()[0])
    ap.add_argument("--version", action="version", version=VERSION)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("doctor", help="probe dependencies and accelerators")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_doctor)
    s = sub.add_parser("explain", help="formula and method of a family")
    s.add_argument("family")
    s.set_defaults(fn=cmd_explain)
    s = sub.add_parser("render", help="recipe JSON or preset -> PNG + recipe")
    s.add_argument("recipe", help=f"preset ({', '.join(PRESETS)}) or recipe.json")
    s.add_argument("-o", "--out", default="render.png")
    s.add_argument("--size", help="WxH")
    s.add_argument("--iter", type=int)
    s.add_argument("--palette", choices=list(PALETTES))
    s.add_argument("--supersample", type=int)
    s.set_defaults(fn=cmd_render)
    s = sub.add_parser("measure", help="box dimension of an image, or Mandelbrot area")
    s.add_argument("what", choices=["box", "area"])
    s.add_argument("image", nargs="?")
    s.add_argument("--threshold", type=int, default=128, help="grey level; darker pixels count as filled")
    s.add_argument("--invert", action="store_true", help="lighter pixels count as filled")
    s.add_argument("--size", type=int, default=2048, help="area grid side")
    s.add_argument("--iter", type=int, default=10000)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_measure)
    s = sub.add_parser("palette", help="list palettes, print one, or write a swatch")
    s.add_argument("name", nargs="?")
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_palette)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
