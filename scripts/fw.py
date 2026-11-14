#!/usr/bin/env python3
"""fractalwright CLI: render, measure and explain fractals.

Standard library first. NumPy is the reference core (probed; renders and
measures fall back to pure Python for small sizes). Pillow is optional (a
stdlib PNG writer is built in). Playwright and moderngl are only probed.

Commands: doctor, explain, render, measure, identify, palette.
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

VERSION = "0.2.0"
ROOT = Path(__file__).resolve().parent.parent

try:
    import numpy as np
except ImportError:  # pragma: no cover - probed by doctor
    np = None

FAMILIES = ("mandelbrot", "julia", "burning-ship", "tricorn", "multibrot", "kronecker")

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
    "kronecker": ("M_n = M kron M_(n-1), M a k x k 0/1 mask",
                  "Kronecker powers of a small mask draw grid fractals (carpet, Vicsek, Cantor dust) exactly on a k^n pixel grid. Similarity dimension log(ones)/log(k); box counting with boxes k^j returns it exactly, so these are exact test inputs for measure.",
                  "references/08-measuring.md#7-test-values"),
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
    "kronecker-carpet": {"family": "kronecker", "formula": "kronecker", "params": {"mask": ["111", "101", "111"], "power": 6}},
    "kronecker-vicsek": {"family": "kronecker", "formula": "kronecker", "params": {"mask": ["010", "111", "010"], "power": 6}},
    "kronecker-cantor-dust": {"family": "kronecker", "formula": "kronecker", "params": {"mask": ["101", "000", "101"], "power": 6}},
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
    if r["formula"] == "kronecker":
        p = r["params"]
        p["mask"] = [str(x) for x in p.get("mask", KRONECKER["carpet"])]
        p["power"] = int(p.get("power", 5))
        k = len(p["mask"])
        if any(len(x) != k or set(x) - set("01") for x in p["mask"]):
            raise SystemExit("kronecker mask must be k rows of k characters 0 or 1")
        if k ** p["power"] > 8192:
            raise SystemExit(f"kronecker side {k}^{p['power']} is over 8192 px")
        r["family"] = "kronecker"
        r["size"] = {"w": k ** p["power"], "h": k ** p["power"], "supersample": 1}
        for key in ("bailout", "max_iter"):
            p.pop(key, None)
        r["view"] = None
        r["colouring"] = {"method": "mask", "filled": r["colouring"].get("filled", "#000000"),
                          "empty": r["colouring"].get("empty", "#ffffff")}
        r["palette"] = None
        return r
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
    rgb = palette_rgb(r["palette"], nu * float(c.get("density", 0.02)) + float(c.get("phase", 0) or 0))
    rgb[inside] = _hex(c.get("inside", "#000000"))
    return rgb


def render_array(r):
    """Recipe -> uint8 HxWx3 (NumPy)."""
    r = normalise(r)
    if r["formula"] == "kronecker":
        m = kronecker_mask(r["params"]["mask"], r["params"]["power"])
        out = np.empty(m.shape + (3,), np.uint8)
        out[...] = np.array([int(v * 255 + 0.5) for v in _hex(r["colouring"]["empty"])], np.uint8)
        out[m] = [int(v * 255 + 0.5) for v in _hex(r["colouring"]["filled"])]
        return out
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
    if r["formula"] == "kronecker":
        mask, k, n = r["params"]["mask"], len(r["params"]["mask"]), r["params"]["power"]
        on = bytes(int(v * 255 + 0.5) for v in _hex(r["colouring"]["filled"]))
        off = bytes(int(v * 255 + 0.5) for v in _hex(r["colouring"]["empty"]))
        rows = []
        for y in range(k ** n):
            row = bytearray()
            for x in range(k ** n):
                yy, xx, fill = y, x, True
                for _ in range(n):
                    if mask[yy % k][xx % k] != "1":
                        fill = False
                        break
                    yy, xx = yy // k, xx // k
                row += on if fill else off
            rows.append(bytes(row))
        return rows
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


# ---------------------------------------------------------------- measure v2
# Book rules behind this block are credited in RESEARCH.md (R-20261114-3): fit
# range in decades, no "fractal" verdict under two decades, 15+ box sizes over
# random offsets, local-slope curve and curvature, speck removal, coarse-box
# bias, lacunarity, similarity dimension, self-affine profile path.
MIN_DECADES = 2.0
# Verdict thresholds come from measured cases (tests/test_fw.py, TESTS.md T-20261114-3).
SLOPE_SPREAD_MAX = 0.30   # local-slope max-min; fractals measured <= 0.287, decoys >= 0.349
INTEGER_BAND = 0.10       # |D - round(D)| under this reads as an ordinary set (line read 0.931)
SPECK_DUST = 0.5          # more isolated pixels than this share: a dust (Cantor dust), not noise


def remove_specks(mask):
    """Drop specks: 8-connected components of one or two pixels.
    Returns (clean, removed)."""
    m = np.asarray(mask, bool)
    h, w = m.shape
    shifts = [(dy, dx) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx]

    def shift(a, dy, dx):  # out[y, x] = a[y + dy, x + dx], zero outside
        p = np.pad(a, 1)
        return p[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
    nb = sum(shift(m, dy, dx).astype(np.int8) for dy, dx in shifts)
    speck = m & (nb == 0)
    one = m & (nb == 1)
    for dy, dx in shifts:
        speck |= one & shift(one, dy, dx)
    return m & ~speck, int(speck.sum())


def box_sizes(h, w, n=16, smin=2, frac=4):
    smax = max(smin + 1, min(h, w) // frac)
    return [int(v) for v in np.unique(np.round(np.geomspace(smin, smax, n)).astype(int))]


def box_counts(mask, sizes, offsets=8, seed=0):
    """Mean occupied-box count per size over random grid offsets (seeded)."""
    m = np.asarray(mask, bool)
    h, w = m.shape
    smax = max(sizes)
    big = np.zeros((h + 2 * smax, w + 2 * smax), bool)
    big[smax:smax + h, smax:smax + w] = m
    rng = np.random.default_rng(seed)
    out = []
    for s in sizes:
        offs = [(0, 0)] + [tuple(int(v) for v in rng.integers(0, s, 2)) for _ in range(max(0, offsets - 1))]
        ns = []
        for oy, ox in offs:
            ny, nx = -(-(h + oy) // s), -(-(w + ox) // s)
            v = big[smax - oy:smax - oy + ny * s, smax - ox:smax - ox + nx * s]
            ns.append(int(v.reshape(ny, s, nx, s).any(axis=(1, 3)).sum()))
        out.append(float(np.mean(ns)))
    return out


def local_slopes(lx, ly, win=5):
    win = min(win, len(lx))
    return [float(np.polyfit(lx[i:i + win], ly[i:i + win], 1)[0]) for i in range(len(lx) - win + 1)]


def box_analysis(mask, n_sizes=16, offsets=8, seed=0, specks=True, smin=2, frac=4, sizes=None):
    """Box-counting report with fit range, local slopes and a verdict.
    The verdict never names a shape: D alone cannot identify."""
    m = np.asarray(mask, bool)
    warnings, removed, D_raw = [], 0, None
    h, w = m.shape
    sizes = list(sizes) if sizes else box_sizes(h, w, n=n_sizes, smin=smin, frac=frac)
    lx = np.log([1.0 / s for s in sizes])
    if specks:
        clean, removed = remove_specks(m)
        if removed > SPECK_DUST * m.sum():
            warnings.append(f"{removed} of {int(m.sum())} filled pixels are isolated: read as a dust, specks kept")
            removed = 0
        elif removed:
            D_raw = float(np.polyfit(lx, np.log(np.maximum(box_counts(m, sizes, offsets, seed), 1)), 1)[0])
            m = clean
    if not m.any():
        return {"measure": "box-dimension", "verdict": "empty mask", "warnings": ["no filled pixels"]}
    N = box_counts(m, sizes, offsets, seed)
    ly = np.log(np.maximum(N, 1))
    D = float(np.polyfit(lx, ly, 1)[0])
    fit = np.polyval(np.polyfit(lx, ly, 1), lx)
    ss = float(((ly - ly.mean()) ** 2).sum())
    r2 = 1 - float(((ly - fit) ** 2).sum()) / ss if ss > 0 else 1.0
    curv = float(np.polyfit(lx, ly, 2)[0])
    ls = local_slopes(lx, ly)
    spread = max(ls) - min(ls)
    decades = math.log10(max(sizes) / min(sizes))
    if D_raw is not None and abs(D_raw - D) > 0.01:
        warnings.append(f"removed {removed} isolated pixels (specks); D moved {D_raw:.3f} -> {D:.3f}")
    elif removed:
        warnings.append(f"removed {removed} isolated pixels (D moved under 0.01)")
    if len(sizes) < 15:
        warnings.append(f"only {len(sizes)} distinct box sizes (15+ wanted): the image is small")
    warnings.append("coarse boxes bias D; read the local-slope curve, not one number")
    if decades < MIN_DECADES:
        verdict = f"descriptor only: fit range {decades:.2f} decades is under {MIN_DECADES:.0f}"
    elif spread > SLOPE_SPREAD_MAX:
        verdict = (f"not fractal over this range: local slope drifts {min(ls):.2f}..{max(ls):.2f}"
                   " (no single scaling range)")
    elif abs(D - round(D)) < INTEGER_BAND:
        verdict = f"ordinary set: D {D:.3f} is near the integer {round(D)}"
    else:
        verdict = f"fractal-like over {decades:.2f} decades (D alone cannot identify the shape)"
    return {"measure": "box-dimension", "dimension": D, "r2": r2, "curvature": curv,
            "fit_px": [min(sizes), max(sizes)], "decades": decades, "sizes": sizes, "counts": N,
            "local_slopes": ls, "slope_spread": spread, "offsets": offsets, "seed": seed,
            "specks_removed": removed, "image": [w, h], "verdict": verdict, "warnings": warnings}


def lacunarity(mask, radii=None):
    """Gliding-box lacunarity: Lambda(r) = E[S^2] / E[S]^2 over every r x r box."""
    m = np.asarray(mask, float)
    h, w = m.shape
    if radii is None:
        radii, r = [], 2
        while r <= min(h, w) // 8:
            radii.append(r)
            r *= 2
    I = np.zeros((h + 1, w + 1))
    I[1:, 1:] = m.cumsum(0).cumsum(1)
    out = []
    for r in radii:
        S = I[r:, r:] - I[:-r, r:] - I[r:, :-r] + I[:-r, :-r]
        mu = S.mean()
        out.append((int(r), float((S * S).mean() / (mu * mu)) if mu > 0 else float("nan")))
    return out


def similarity_dimension(ratios, tol=1e-12):
    """Root s of sum r_i^s = 1 (Moran equation), by bisection. Exact only when
    the pieces do not overlap (open set condition); an upper bound otherwise."""
    rs = [float(x) for x in ratios]
    if not rs or any(not 0 < x < 1 for x in rs):
        raise ValueError("ratios must lie in (0, 1)")
    lo, hi = 0.0, 1.0
    while sum(x ** hi for x in rs) > 1:
        hi *= 2
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if sum(x ** mid for x in rs) > 1 else (lo, mid)
    return (lo + hi) / 2


# ---------------------------------------------------------------- self-affine
def _slope(x, y):
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


def _logbin(x, y, nb=24):
    edges = np.geomspace(x.min(), x.max() * 1.0000001, nb + 1)
    idx = np.digitize(x, edges) - 1
    xs, ys = [], []
    for b in range(nb):
        s = idx == b
        if s.any():
            xs.append(math.exp(float(np.log(x[s]).mean())))
            ys.append(math.exp(float(np.log(y[s]).mean())))
    return np.array(xs), np.array(ys)


def spectral_slope(y, fmax=1 / 8):
    """Periodogram slope beta (P ~ f^-beta) of a 1D profile, end-matched
    (the line joining the ends is removed), least squares over every
    frequency from 2/n to fmax."""
    y = np.asarray(y, float)
    n = y.size
    y = y - (y[0] + (y[-1] - y[0]) * np.arange(n) / (n - 1))
    P = np.abs(np.fft.rfft(y)) ** 2
    f = np.arange(P.size) / n
    k = (f >= 2 / n) & (f <= fmax)
    return -_slope(f[k], P[k])


def semivariogram_h(y, lags=None):
    """Ha from gamma(l) = mean((y[i+l] - y[i])^2) / 2 ~ l^(2 Ha); lags 1..n/10."""
    y = np.asarray(y, float)
    if lags is None:
        lags = np.unique(np.round(np.geomspace(1, max(2, y.size // 10), 20)).astype(int))
    g = [0.5 * float(np.mean((y[l:] - y[:-l]) ** 2)) for l in lags]
    return _slope(lags, g) / 2


def katz_dimension(x, y=None):
    """Katz dimension of a sampled curve: log10(n) / (log10(n) + log10(d / L)),
    L total length, d largest distance from the first point, n = L / mean step.
    A 1D signal is read as the curve (i, y_i). Book rule: cheap, biased."""
    if y is None:
        y = np.asarray(x, float)
        x = np.arange(y.size, dtype=float)
    x, y = np.asarray(x, float), np.asarray(y, float)
    steps = np.hypot(np.diff(x), np.diff(y))
    L, a = float(steps.sum()), float(steps.mean())
    d = float(np.hypot(x - x[0], y - y[0]).max())
    n = L / a
    return math.log10(n) / (math.log10(n) + math.log10(d / L))


def profile_analysis(y):
    y = np.asarray(y, float)
    beta = spectral_slope(y)
    Hs = semivariogram_h(y)
    res = {"measure": "profile", "n": int(y.size), "beta": beta,
           "H_spectral": (beta - 1) / 2, "D_spectral": (5 - beta) / 2,
           "H_semivariogram": Hs, "D_semivariogram": 2 - Hs, "katz": katz_dimension(y),
           "relations": "beta = 2H + 1; D = 2 - H = (5 - beta) / 2", "warnings": []}
    if not 1 < beta < 3:
        res["warnings"].append(f"beta {beta:.2f} is outside 1..3: a noise, not a walk; the semivariogram H does not apply (use R/S or DFA)")
    res["warnings"].append("Katz is a roughness number with known bias; do not read it as D")
    return res


def radial_psd(z, kmin=2, kmax_frac=1 / 8):
    """2D power per Fourier mode with kmin <= |k| <= n * kmax_frac: (|k|, P).
    A least-squares fit over every mode is the radial exponent; fitting
    integer-k bin averages biased H by -0.04 (convexity in the low bins)."""
    z = np.asarray(z, float)
    F = np.abs(np.fft.fft2(z - z.mean())) ** 2
    ny, nx = z.shape
    ky, kx = np.meshgrid(np.fft.fftfreq(ny) * ny, np.fft.fftfreq(nx) * nx, indexing="ij")
    k = np.hypot(kx, ky).ravel()
    sel = (k >= kmin) & (k <= min(nx, ny) * kmax_frac)
    return k[sel], F.ravel()[sel]


def dbc_dimension(z, sizes=(2, 4, 8, 16, 32, 64, 128)):
    """Differential box (cube) counting of a heightmap whose heights are in pixel units."""
    z = np.asarray(z, float)
    n = min(z.shape)
    sizes = [s for s in sizes if s <= n // 8]
    N = []
    for s in sizes:
        m = n // s * s
        b = z[:m, :m].reshape(m // s, s, m // s, s)
        N.append(float((np.floor(b.max(axis=(1, 3)) / s) - np.floor(b.min(axis=(1, 3)) / s) + 1).sum()))
    return -_slope(sizes, N)


def heightmap_analysis(z):
    z = np.asarray(z, float)
    b2 = -_slope(*radial_psd(z))
    Hr = (b2 - 2) / 2
    step_r = max(1, z.shape[0] // 32)
    step_c = max(1, z.shape[1] // 32)
    b1 = float(np.mean([spectral_slope(z[i]) for i in range(0, z.shape[0], step_r)]
                       + [spectral_slope(z[:, j]) for j in range(0, z.shape[1], step_c)]))
    Hp = (b1 - 1) / 2
    rms = float(np.sqrt(np.mean(np.diff(z, axis=1) ** 2)))
    return {"measure": "heightmap", "shape": list(z.shape), "beta_radial": b2, "beta_profiles": b1,
            "radial_minus_profile": b2 - b1, "H_radial": Hr, "D_surface": 3 - Hr,
            "H_profiles": Hp, "D_profiles_plus_1": 3 - Hp,
            "D_cube_count": dbc_dimension(z / rms * min(z.shape)) if rms > 0 else float("nan"),
            "relations": "radial beta = 2H + 2 = profile beta + 1; surface D = 3 - H = profile D + 1",
            "warnings": ["D_cube_count (differential box counting) read 0.1 to 0.3 low on synthetic fBm at 1024 px; use D_surface"]}


def synth_fbm1d(n, H, seed=0):
    """Exact fBm (n + 1 samples) by Davies-Harte circulant embedding of fGn."""
    rng = np.random.default_rng(seed)
    k = np.arange(n + 1, dtype=float)
    g = 0.5 * (np.abs(k + 1) ** (2 * H) - 2 * k ** (2 * H) + np.abs(k - 1) ** (2 * H))
    c = np.concatenate([g, g[-2:0:-1]])
    lam = np.clip(np.fft.fft(c).real, 0, None)
    M = c.size
    Z = rng.normal(size=M) + 1j * rng.normal(size=M)
    fgn = np.fft.fft(np.sqrt(lam / M) * Z)[:n].real
    return np.concatenate([[0.0], np.cumsum(fgn)])


def synth_fbm2d(n, H, seed=0):
    """Spectral synthesis on an n x n torus: white noise filtered by k^-(H+1)."""
    rng = np.random.default_rng(seed)
    W = np.fft.fft2(rng.normal(size=(n, n)))
    ky, kx = np.meshgrid(np.fft.fftfreq(n) * n, np.fft.fftfreq(n) * n, indexing="ij")
    k = np.hypot(kx, ky)
    k[0, 0] = 1.0
    A = k ** -(H + 1)
    A[0, 0] = 0.0
    return np.fft.ifft2(W * A).real


def read_numbers(path):
    """A profile file: one number per line, or x,y (comma, space or tab) pairs."""
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line[0] in "#%":
            continue
        try:
            rows.append([float(v) for v in line.replace(",", " ").split()])
        except ValueError:
            continue  # header
    return np.array(rows, float)


# ---------------------------------------------------------------- kronecker
KRONECKER = {
    "carpet": ["111", "101", "111"],
    "vicsek": ["010", "111", "010"],
    "cantor-dust": ["101", "000", "101"],
    "sierpinski": ["11", "10"],
}


def kronecker_mask(rows, power):
    """Kronecker power of a k x k 0/1 mask: an exact grid fractal of side k^power."""
    base = np.array([[ch == "1" for ch in r] for r in rows], bool)
    if base.ndim != 2 or base.shape[0] != base.shape[1]:
        raise SystemExit("kronecker mask must be square, rows of 0 and 1")
    m = np.ones((1, 1), bool)
    for _ in range(int(power)):
        m = np.kron(m, base)
    return m


def kronecker_dimension(rows):
    """log(ones) / log(k): the similarity dimension of the mask's attractor."""
    return math.log(sum(r.count("1") for r in rows)) / math.log(len(rows))


# ---------------------------------------------------------------- identify
def julia_connected(c, max_iter=1000):
    """The quadratic Julia set of z^2 + c is connected iff the orbit of 0 stays bounded."""
    z = 0j
    for n in range(max_iter):
        z = z * z + c
        if abs(z) > 2:
            return False, n + 1
    return True, max_iter


def mirror_scores(img):
    """Fraction of pixels unchanged by a left-right, up-down or 180-degree flip."""
    a = np.asarray(img)

    def eq(b):
        e = a == b
        return float((e.all(axis=-1) if a.ndim == 3 else e).mean())
    return {"left-right": eq(a[:, ::-1]), "up-down": eq(a[::-1]), "rot180": eq(a[::-1, ::-1])}


def identify(recipe=None, image=None):
    """identify v1: hand-built features. Never names a shape from dimension alone."""
    feats, hints = {}, []
    if recipe is not None:
        formula = recipe.get("formula")
        feats["family"] = recipe.get("family", "escape-time")
        feats["formula"] = formula
        if formula == "julia":
            cr, ci = (float(Decimal(str(x))) for x in recipe["params"]["c"])
            conn, n = julia_connected(complex(cr, ci))
            feats["julia_connected"] = conn
            hints.append("connected Julia set: the orbit of 0 stays bounded, so c is in the Mandelbrot set" if conn
                         else f"Cantor dust: the orbit of 0 escapes after {n} steps, so c is outside the Mandelbrot set")
            q = (cr - 0.25) ** 2 + ci * ci
            if q * (q + (cr - 0.25)) <= 0.25 * ci * ci:
                feats["c_region"] = "main cardioid"
                hints.append("c in the main cardioid: one attracting fixed point; the set is a deformed circle")
            elif (cr + 1) ** 2 + ci * ci <= 1 / 16:
                feats["c_region"] = "period-2 bulb"
                hints.append("c in the period-2 bulb: an attracting 2-cycle; basilica-like")
        elif formula in ("mandelbrot", "tricorn"):
            v = recipe.get("view") or {}
            on_axis = Decimal(str(v.get("centre", ["0", "0"])[1])) == 0 and not v.get("rotation_deg")
            hints.append("the set is mirror symmetric across the real axis"
                         + ("; this view is centred on it, so the picture is too" if on_axis else "; this view is off the axis"))
        elif formula == "multibrot":
            hints.append(f"{int(recipe['params'].get('power', 2)) - 1}-fold rotational symmetry")
        elif formula == "kronecker":
            rows = recipe["params"]["mask"]
            feats["similarity_dimension"] = kronecker_dimension(rows)
            hints.append(f"exact grid fractal: D = log({sum(r.count('1') for r in rows)}) / log({len(rows)})")
    if image is not None:
        a = np.asarray(image)
        sc = mirror_scores(a)
        feats["mirror"] = sc
        hints += [f"{k} mirror symmetric ({v:.3f} of pixels match)" for k, v in sc.items() if v > 0.995]
        grey = a.mean(axis=-1) if a.ndim == 3 else a
        rep = box_analysis(grey < 128, offsets=4)
        feats["box"] = {k: rep.get(k) for k in ("dimension", "decades", "slope_spread", "verdict")}
        hints.append("box dimension is a descriptor here, not an identification")
    return {"identify": "v1", "features": feats, "hints": hints}


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
    rows.append(("moderngl", mgl, "optional accelerator: probed only; no command uses it (renders go through NumPy or Playwright)"))
    if has("playwright"):
        import fw_serve
        ok, note = fw_serve.probe_browser()
        pw = ("ready: " if ok else "") + note
    else:
        pw = "missing"
    rows.append(("playwright", pw, "optional accelerator: render --route browser (WebGL2, float32), same shader as serve"))
    browsers = [b for b in ("msedge", "chrome", "google-chrome", "chromium") if shutil.which(b)]
    edge = Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    if edge.exists():
        browsers.append("msedge")
    rows.append(("browser", ", ".join(sorted(set(browsers))) or "none on PATH", "for the playwright route"))
    rows.append(("3d", "browser route only", "fw.py 3d needs the playwright route above; no NumPy fallback for 3D"))
    rows.append(("ffmpeg", shutil.which("ffmpeg") or "missing", "video and audio commands: zoom, morph, loop, audio (H.264 encode, audio decode and mux), flashcheck"))
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
    if a.mask or a.power:
        r["formula"] = "kronecker"
        if a.mask:
            r["params"]["mask"] = KRONECKER.get(a.mask, a.mask.split(","))
        if a.power:
            r["params"]["power"] = a.power
    r = normalise(r)
    out = Path(a.out)
    if getattr(a, "route", "auto") == "browser" and not a.deep:
        import fw_serve
        if not fw_serve.float32_ok(r):
            print(f"browser route: float32 cannot hold this view (pixel {fw_serve.float32_rel(r):.1e} of the coordinate,"
                  f" limits: pixel {fw_serve.F32_REL_LIMIT:g}, width {fw_serve.F32_WIDTH_LIMIT:g}); using numpy")
        else:
            try:
                arr = fw_serve.browser_render(r)
                r["render"] = {"route": "browser", "precision": "float32"}
                write_png(out, arr=arr)
                rec = out.with_suffix(".json")
                rec.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
                print(f"wrote {out} and {rec} (browser route)")
                return 0
            except Exception as e:  # noqa: BLE001
                print(f"browser route unavailable ({str(e).splitlines()[0][:120]}); using numpy")
    if np is not None and r["formula"] in ("mandelbrot", "julia") and int(r["params"].get("power", 2)) == 2 and (a.deep or Decimal(r["view"]["width"]) < Decimal("1e-12")):
        import fw_deep  # perturbation (Mandelbrot, Julia): Decimal reference orbit, float64 deltas, rebasing
        st = {}
        r["render"] = {"route": "numpy-perturbation", "precision": "decimal+float64"}
        write_png(out, arr=fw_deep.render_array(r, st))
        print(f"deep: rebased {st['rebased_pixels']} pixels")
    elif np is not None:
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


def cmd_serve(a):
    import fw_serve
    try:
        return fw_serve.serve(a.host, a.port, a.out_dir, a.open)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2


def cmd_export(a):
    import fw_serve
    try:
        r = fw_serve.hash_to_recipe(a.share)
    except ValueError as e:
        print(e, file=sys.stderr)
        return 2
    text = json.dumps(r, indent=2) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        sys.stdout.write(text)
    return 0


PROFILE_EXT = (".csv", ".txt", ".tsv", ".dat")


def _out(res, as_json):
    if as_json:
        print(json.dumps(res, indent=2))
        return
    for k, v in res.items():
        if isinstance(v, float):
            v = f"{v:.4f}"
        elif isinstance(v, list) and v and isinstance(v[0], float):
            v = "[" + ", ".join(f"{x:.3f}" for x in v) + "]"
        print(f"{k}: {v}")


def _load_mask(a):
    if Path(a.image).suffix.lower() == ".npy":
        return np.load(a.image).astype(bool)
    return read_mask(a.image, a.threshold, a.invert)


def _load_grey(path):
    if Path(path).suffix.lower() == ".npy":
        return np.load(path).astype(float)
    from PIL import Image
    return np.asarray(Image.open(path).convert("F"), float)


def cmd_measure(a):
    if np is None:
        print("measure needs NumPy (pip install numpy)", file=sys.stderr)
        return 3
    w = a.what
    if w == "area":
        A = mandelbrot_area(a.size, a.iter)
        res = {"measure": "mandelbrot-area", "size": a.size, "max_iter": a.iter, "area": A,
               "reference": 1.50659177, "error": A - 1.50659177}
    elif w == "ifs":
        if not a.ratios:
            print("measure ifs needs --ratios r1,r2,...", file=sys.stderr)
            return 2
        rs = [float(x) for x in a.ratios.split(",")]
        res = {"measure": "similarity-dimension", "ratios": rs, "dimension": similarity_dimension(rs),
               "note": "exact only when the pieces do not overlap (open set condition); with overlap it is an upper bound"}
    else:
        if not a.image:
            print(f"measure {w} needs a file", file=sys.stderr)
            return 2
        ext = Path(a.image).suffix.lower()
        if w in ("box", "lacunarity") and ext in PROFILE_EXT:
            print(f"refused: {a.image} is a profile (numbers), and box counting a self-affine profile gives the wrong D. "
                  "Use: fw.py measure profile FILE", file=sys.stderr)
            return 2
        if w == "box":
            res = box_analysis(_load_mask(a), offsets=a.offsets, seed=a.seed, specks=not a.keep_specks)
            res["image_file"] = a.image
            if ext != ".npy":
                grey = _load_grey(a.image)
                levels = np.unique(grey.astype(np.uint8)).size
                if levels > 64:
                    res["warnings"].append(f"{levels} grey levels: if this is a heightmap use 'measure heightmap'; box counting reads only the thresholded shape")
        elif w == "lacunarity":
            lac = lacunarity(_load_mask(a))
            res = {"measure": "lacunarity", "image_file": a.image, "lacunarity": lac,
                   "note": "gliding box E[S^2]/E[S]^2; compare shapes at the same box sizes; a second number beside D"}
        elif w in ("profile", "katz"):
            data = read_numbers(a.image)
            if data.ndim != 2 or data.size == 0:
                print("no numbers read", file=sys.stderr)
                return 2
            if w == "katz":
                kd = katz_dimension(data[:, 0], data[:, 1]) if data.shape[1] >= 2 else katz_dimension(data[:, 0])
                res = {"measure": "katz", "points": int(data.shape[0]), "katz": kd,
                       "note": "book rule (Katz 1988 via Banerjee): cheap, scale dependent, biased; exact on a Koch polyline"}
            else:
                res = profile_analysis(data[:, -1])
        elif w == "heightmap":
            res = heightmap_analysis(_load_grey(a.image))
    _out(res, a.json)
    return 0


def cmd_identify(a):
    if np is None:
        print("identify needs NumPy", file=sys.stderr)
        return 3
    recipe = image = None
    if a.target:
        p = Path(a.target)
        if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            from PIL import Image
            image = np.asarray(Image.open(p).convert("RGB"))
            rec = p.with_suffix(".json")
            if rec.is_file():
                recipe = normalise(load_recipe(str(rec)))
        else:
            recipe = normalise(load_recipe(a.target))
    if a.c:
        cr, ci = a.c.split(",")
        recipe = normalise(_merge(default_recipe(), {"formula": "julia", "params": {"c": [cr, ci]}}))
    if recipe is None and image is None:
        print("identify needs a preset, recipe, image or --c re,im", file=sys.stderr)
        return 2
    _out(identify(recipe, image), a.json)
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


# ---------------------------------------------------------------- video (sheet, zoom, morph, loop, flashcheck)
COMFY_HOSTS = tuple(h.strip() for h in __import__("os").environ.get("FW_COMFY_HOSTS", "127.0.0.1:8188,127.0.0.1:8199").split(",") if h.strip())
FLASH_SWING = 0.10   # relative luminance swing that counts (WCAG 2.3.1 general flash, refs/09 5.1)
FLASH_MAX_PER_S = 3


def _set_path(r, path, value):
    keys = path.split(".")
    d = r
    for k in keys[:-1]:
        d = d.setdefault(k, {})
    d[keys[-1]] = value


def _parse_value(s):
    s = s.strip()
    if ":" in s:  # complex pair re:im, kept as decimal strings
        return [str(Decimal(x)) for x in s.split(":")]
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return s


def sheet(base, vary, values, cols=None):
    """Render one tile per value; returns (uint8 sheet, list of (label, recipe))."""
    from PIL import Image, ImageDraw
    tiles = []
    for v in values:
        r = json.loads(json.dumps(base))
        if vary == "palette":
            r["palette"] = dict(PALETTES[v])
            label = f"palette={v}"
        else:
            _set_path(r, vary, v)
            label = f"{vary}={v if not isinstance(v, list) else ','.join(v)}"
        r = normalise(r)
        tiles.append((label, r, render_array(r)))
    n = len(tiles)
    cols = cols or math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    th, tw = tiles[0][2].shape[:2]
    band = 14
    img = Image.new("RGB", (cols * tw, rows * (th + band)), (24, 24, 24))
    dr = ImageDraw.Draw(img)
    for i, (label, _, arr) in enumerate(tiles):
        x, y = (i % cols) * tw, (i // cols) * (th + band)
        img.paste(Image.fromarray(arr), (x, y))
        dr.text((x + 3, y + th + 2), label, fill=(230, 230, 230))
    return np.asarray(img), [(lab, r) for lab, r, _ in tiles]


def smoothstep(t):
    return t * t * (3 - 2 * t)


def zoom_frames(base, w0, w1, n, centre_to=None):
    """Exponential width interpolation: w_i = w0 * (w1/w0)^(i/(n-1)); centre fixed or eased."""
    c0 = [float(Decimal(x)) for x in base["view"]["centre"]]
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        r = json.loads(json.dumps(base))
        w = w0 * (w1 / w0) ** t
        r["view"]["width"] = repr(w)
        if centre_to is not None:
            s = smoothstep(t)
            r["view"]["centre"] = [repr(a + (b - a) * s) for a, b in zip(c0, centre_to)]
        out.append(r)
    return out


def _interp_path(points, t):
    """Piecewise linear along a list of points, t in 0..1."""
    if len(points) == 1:
        return list(points[0])
    seg = t * (len(points) - 1)
    k = min(int(seg), len(points) - 2)
    u = seg - k
    return [a + (b - a) * u for a, b in zip(points[k], points[k + 1])]


def morph_frames(base, path, vary, n):
    out = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.0
        r = json.loads(json.dumps(base))
        val = _interp_path(path, t)
        _set_path(r, vary, [repr(x) for x in val] if len(val) > 1 else val[0])
        out.append(r)
    return out


def loop_frames(base, n, circle=None, phase=False):
    """Closed path sampled at k/n, k = 0..n-1, so frame n would equal frame 0."""
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = json.loads(json.dumps(base))
        if circle:
            cr, ci, rad = circle
            r["params"]["c"] = [repr(cr + rad * math.cos(a)), repr(ci + rad * math.sin(a))]
        if phase:
            r["colouring"]["phase"] = k / n
        out.append(r)
    return out


def probe_comfy(hosts=None, timeout=2.0):
    import urllib.request
    if hosts is None:
        env = __import__("os").environ.get("FW_COMFY_HOSTS")
        hosts = COMFY_HOSTS if env is None else [h for h in env.split(",") if h.strip()]
    for h in hosts:
        try:
            with urllib.request.urlopen(f"http://{h}/system_stats", timeout=timeout) as resp:
                if resp.status == 200:
                    return h
        except Exception:  # noqa: BLE001
            continue
    return None


def encode_mp4(frame_dir, fps, out):
    ff = shutil.which("ffmpeg")
    if not ff:
        raise SystemExit("ffmpeg not on PATH: frames written, video skipped")
    cmd = [ff, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(Path(frame_dir) / "f_%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-r", str(fps), str(out)]
    import subprocess
    subprocess.run(cmd, check=True)
    return out


def probe_video(path):
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames",
                          "-show_entries", "stream=nb_read_frames,r_frame_rate,width,height",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True)
    s = json.loads(out.stdout)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return {"frames": int(s["nb_read_frames"]), "fps": int(num) / int(den), "w": s["width"], "h": s["height"]}


def write_video(kind, recipes, anim, out, ai=True):
    """Render frames, encode, write the animation recipe. Exact frames and video always written."""
    out = Path(out)
    fdir = out.with_name(out.stem + "_frames")
    fdir.mkdir(parents=True, exist_ok=True)
    for i, r in enumerate(recipes):
        write_png(fdir / f"f_{i:05d}.png", arr=render_array(normalise(r)))
    encode_mp4(fdir, anim["fps"], out)
    rec = json.loads(json.dumps(normalise(recipes[0])))
    rec["animation"] = dict(anim, kind=kind, frames=len(recipes), frame_dir=fdir.name)
    notes = []
    import fw_ai
    fw_ai.apply(rec, notes, fdir, out, anim["fps"], ai=ai)
    rec["notes"] = notes
    rp = out.with_suffix(".json")
    rp.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    fw_ai.write_ai_recipe(rec, out)
    return rp, notes


def read_frames(src):
    """Frame dir (PNGs) or video file -> list of float arrays HxWx3 in 0..1, plus fps (None for dirs)."""
    src = Path(src)
    if src.is_dir():
        from PIL import Image
        fr = [np.asarray(Image.open(p).convert("RGB"), dtype=np.float64) / 255 for p in sorted(src.glob("*.png"))]
        return fr, None
    import subprocess
    info = probe_video(src)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    w, h = info["w"], info["h"]
    arr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3).astype(np.float64) / 255
    return list(arr), info["fps"]


def rel_luminance(rgb):
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return lin @ np.array([0.2126, 0.7152, 0.0722])


def swing_walk(L, swing=FLASH_SWING, dark_max=None):
    """Turning-point walk over a luminance series (any trailing shape, vectorised per element).
    Returns a bool array (frames, ...) marking frames where a swing of >= swing completes. With dark_max,
    a swing counts only if its darker end is below dark_max (WCAG: darker image below 0.80)."""
    L = np.asarray(L, float)
    ev = np.zeros(L.shape, bool)
    lo = L[0].copy(); hi = L[0].copy()
    d = np.zeros(L.shape[1:], np.int8)
    for i in range(1, len(L)):
        x = L[i]
        z, up, dn = d == 0, d > 0, d < 0
        lo = np.where(z, np.minimum(lo, x), lo); hi = np.where(z, np.maximum(hi, x), hi)
        hi = np.where(up & (x > hi), x, hi); lo = np.where(dn & (x < lo), x, lo)
        rise = (z | dn) & (x - lo >= swing)
        fall = (z | up) & (hi - x >= swing) & ~rise
        if dark_max is not None:
            ok_r, ok_f = lo < dark_max, x < dark_max
        else:
            ok_r = ok_f = True
        ev[i] = (rise & ok_r) | (fall & ok_f)
        d = np.where(rise, 1, np.where(fall, -1, d)).astype(np.int8)
        hi = np.where(rise, x, hi); lo = np.where(fall, x, lo)
    return ev


def _per_second_max(ev, win):
    """Max count of events in any window of win frames, per element."""
    c = np.concatenate([np.zeros((1,) + ev.shape[1:]), np.cumsum(ev, 0)])
    n = len(ev)
    if n <= win:
        return c[-1]
    return (c[win:] - c[:-win]).max(0)


def _box_max_fraction(mask, bh, bw):
    """Max fraction of any bh x bw box (sliding, cell stride) covered by mask."""
    H, W = mask.shape
    bh, bw = min(bh, H), min(bw, W)
    S = np.zeros((H + 1, W + 1)); S[1:, 1:] = np.cumsum(np.cumsum(mask, 0), 1)
    tot = S[bh:, bw:] - S[:-bh, bw:] - S[bh:, :-bw] + S[:-bh, :-bw]
    return float(tot.max() / (bh * bw))


def _cells(f, gh, gw):
    """Block-mean an HxWxC frame onto a gh x gw grid (edge rows/cols dropped)."""
    H, W = f.shape[:2]
    gh, gw = min(gh, H), min(gw, W)
    hh, ww = H // gh * gh, W // gw * gw
    return f[:hh, :ww].reshape(gh, hh // gh, gw, ww // gw, -1).mean(axis=(1, 3))


def _uv(rgb):
    """CIE 1976 u'v' of sRGB values (via linear RGB -> XYZ)."""
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    X, Y, Z = np.moveaxis(lin @ M.T, -1, 0)
    den = X + 15 * Y + 3 * Z + 1e-12
    return np.stack([4 * X / den, 9 * Y / den], -1)


FLASH_AREA = 0.25          # WCAG 2.x: 25% of any 10-degree visual field
FLASH_FIELD = (256 / 768, 341 / 1024)  # 10-degree field as a fraction of the screen (341x256 at 1024x768)
FLASH_GRID = (36, 48)      # analysis cells (rows, cols); the field is 12 x 16 cells
FLASH_MIN_CELL = 4         # px; smaller cells measure single-pixel aliasing on tiny previews, not flashes


def flash_check(frames, fps):
    """WCAG 2.x general flash and red flash thresholds (W3C Understanding SC 2.3.1, fetched 2026-11-14):
    a general flash is a pair of opposing changes in relative luminance of 10% or more where the darker
    image is below 0.80; a red flash is a pair of opposing transitions to or from saturated red
    (R/(R+G+B) >= 0.8) with a u'v' difference above 0.2. Content fails only if more than 3 flashes in any
    second cover more than 25% of a 10-degree field (341x256 px at 1024x768, here a 1/3 x 1/3 box).
    Frames are block-averaged onto a grid of up to 36x48 cells (cells at least 4 px); each cell runs the swing walk."""
    F = np.array([np.asarray(f, float)[..., :3] for f in frames])
    L = np.array([rel_luminance(f).mean() for f in F])
    win = max(1, int(round(fps)))
    whole = swing_walk(L)
    worst = int(_per_second_max(whole[:, None], win)[0]) if len(L) > 1 else 0
    H, W = F.shape[1:3]
    gh, gw = max(3, min(FLASH_GRID[0], H // FLASH_MIN_CELL)), max(3, min(FLASH_GRID[1], W // FLASH_MIN_CELL))
    C = np.array([_cells(f, gh, gw) for f in F])            # (n, gh, gw, 3)
    Lc = rel_luminance(C)
    bh = max(1, int(round(FLASH_FIELD[0] * Lc.shape[1]))); bw = max(1, int(round(FLASH_FIELD[1] * Lc.shape[2])))
    gen = _per_second_max(swing_walk(Lc, dark_max=0.80), win)
    # red: state 1 when saturated red; a transition counts when the state flips and u'v' moves > 0.2
    red = C[..., 0] / (C.sum(-1) + 1e-12) >= 0.8
    uv = _uv(C)
    rev = np.zeros(red.shape, bool)
    ref = uv[0].copy(); st = red[0].copy()
    for i in range(1, len(C)):
        flip = (red[i] != st) & (np.linalg.norm(uv[i] - ref, axis=-1) > 0.2)
        rev[i] = flip
        st = np.where(flip, red[i], st); ref = np.where(flip[..., None], uv[i], ref)
    redc = _per_second_max(rev, win) / 2.0  # a red flash is a pair of transitions
    gen_flash = gen / 2.0                   # a general flash is a pair of opposing changes (two swings)
    gen_area = _box_max_fraction(gen_flash > FLASH_MAX_PER_S, bh, bw) if len(L) > 1 else 0.0
    red_area = _box_max_fraction(redc > FLASH_MAX_PER_S, bh, bw) if len(L) > 1 else 0.0
    ok = gen_area <= FLASH_AREA and red_area <= FLASH_AREA
    return {"frames": len(L), "fps": fps, "swings": int(whole.sum()), "max_swings_per_s": worst,
            "limit_per_s": FLASH_MAX_PER_S, "luminance_range": [float(L.min()), float(L.max())],
            "general_flash_area": round(gen_area, 4), "red_flash_area": round(red_area, 4),
            "area_limit": FLASH_AREA, "max_cell_flashes_per_s": float(gen_flash.max()) if len(L) > 1 else 0.0,
            "pass": bool(ok),
            "method": "WCAG 2.x general and red flash thresholds: per-cell swing walk on a 36x48 grid, "
                      "flashing cells (> 3 flashes/s) must cover <= 25% of any 341x256-at-1024x768 box; "
                      "max_swings_per_s is the older whole-frame mean count, kept for reference"}


def seam_ratio(frames):
    d = [np.abs(frames[i + 1] - frames[i]).mean() for i in range(len(frames) - 1)]
    seam = np.abs(frames[0] - frames[-1]).mean()
    return float(seam / np.median(d)), float(seam), float(np.median(d))


def _video_base(a):
    r = load_recipe(a.recipe)
    if a.size:
        w, h = a.size.lower().split("x")
        r["size"]["w"], r["size"]["h"] = int(w), int(h)
    if a.iter:
        r["params"]["max_iter"] = a.iter
    if getattr(a, "palette", None):
        r["palette"] = dict(PALETTES[a.palette])
    return normalise(r)


def _finish_video(kind, recipes, anim, a):
    rp, notes = write_video(kind, recipes, anim, a.out, ai=a.ai)
    fc = flash_check(read_frames(Path(a.out).with_name(Path(a.out).stem + "_frames"))[0], anim["fps"])
    print(f"wrote {a.out}, {rp} and {len(recipes)} frames")
    for n in notes:
        print("note:", n)
    print(f"flashcheck: {fc['max_swings_per_s']} swings/s (limit {FLASH_MAX_PER_S}) {'pass' if fc['pass'] else 'FAIL'}")
    return 0 if fc["pass"] else 4


def _nframes(a):
    return max(2, int(round(a.fps * a.duration)))


def cmd_sheet(a):
    r = load_recipe(a.recipe)
    w, h = (a.tile or "200x150").lower().split("x")
    r["size"]["w"], r["size"]["h"] = int(w), int(h)
    if a.iter:
        r["params"]["max_iter"] = a.iter
    r = normalise(r)
    if a.palettes:
        vary, values = "palette", a.palettes.split(",")
    elif a.vary:
        vary, values = a.vary, [_parse_value(v) for v in a.values.split(",")]
    else:
        raise SystemExit("pass --palettes A,B,C or --vary PATH --values V1,V2 (pairs as re:im)")
    arr, tiles = sheet(r, vary, values, a.cols)
    out = Path(a.out)
    write_png(out, arr=arr)
    side = out.with_suffix(".json")
    side.write_text(json.dumps({"sheet": out.name, "vary": vary,
                                "tiles": [{"label": lab, "recipe": rr} for lab, rr in tiles]}, indent=2) + "\n",
                    encoding="utf-8")
    print(f"wrote {out} ({len(tiles)} tiles) and {side}")
    return 0


def cmd_zoom(a):
    r = _video_base(a)
    w0 = float(Decimal(a.from_width or r["view"]["width"]))
    w1 = float(Decimal(a.to_width))
    ct = [float(x) for x in a.to_centre.split(",")] if a.to_centre else None
    n = _nframes(a)
    frames = zoom_frames(r, w0, w1, n, ct)
    kf = [{"t": 0, "centre": r["view"]["centre"], "width": repr(w0)},
          {"t": a.duration, "centre": [repr(x) for x in ct] if ct else r["view"]["centre"], "width": repr(w1)}]
    return _finish_video("zoom", frames, {"keyframes": kf, "fps": a.fps, "duration_s": a.duration,
                                          "interp": "exponential width, smoothstep centre"}, a)


def cmd_morph(a):
    r = _video_base(a)
    path = [[float(x) for x in p.split(",")] for p in a.path.split(";")]
    n = _nframes(a)
    frames = morph_frames(r, path, a.vary, n)
    kf = [{"t": a.duration * i / (len(path) - 1), a.vary: p} for i, p in enumerate(path)]
    return _finish_video("morph", frames, {"keyframes": kf, "fps": a.fps, "duration_s": a.duration,
                                           "interp": "piecewise linear"}, a)


def cmd_loop(a):
    r = _video_base(a)
    circle = [float(x) for x in a.circle.split(",")] if a.circle else None
    if not circle and not a.phase:
        raise SystemExit("pass --circle re,im,radius (julia c) and/or --phase")
    if circle and r["formula"] != "julia":
        raise SystemExit("--circle moves julia c; use a julia recipe")
    n = _nframes(a)
    frames = loop_frames(r, n, circle, a.phase)
    kf = {"circle": circle, "phase_cycle": bool(a.phase), "closed": True}
    return _finish_video("loop", frames, {"keyframes": kf, "fps": a.fps, "duration_s": a.duration,
                                          "interp": "closed path sampled at k/n"}, a)


def cmd_flashcheck(a):
    frames, fps = read_frames(a.src)
    fps = a.fps or fps or 24
    res = flash_check(frames, fps)
    _out(res, a.json)
    return 0 if res["pass"] else 4


def _video_args(s, default_out):
    s.add_argument("recipe", help="preset or recipe.json")
    s.add_argument("-o", "--out", default=default_out)
    s.add_argument("--size", help="WxH (even numbers for H.264)")
    s.add_argument("--iter", type=int)
    s.add_argument("--palette", choices=list(PALETTES))
    s.add_argument("--fps", type=int, default=24)
    s.add_argument("--duration", type=float, default=4.0, help="seconds")
    s.add_argument("--ai", action=argparse.BooleanOptionalAction, default=True,
                   help="AI styling pass (default on): img2img via ComfyUI to <out>_ai.mp4; exact video always kept")


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
    s.add_argument("--mask", help=f"kronecker mask: {', '.join(KRONECKER)} or rows like 111,101,111")
    s.add_argument("--power", type=int, help="kronecker power (side = k^power)")
    s.add_argument("--deep", action="store_true", help="perturbation route (automatic below width 1e-12)")
    s.add_argument("--route", choices=["auto", "numpy", "browser"], default="auto",
                   help="browser: headless Edge WebGL2 (float32; falls back to numpy when the view is too deep or no browser)")
    s.set_defaults(fn=cmd_render)
    s = sub.add_parser("serve", help="interactive WebGL2 explorer on 127.0.0.1 (pan, zoom, share hash, export, exact render)")
    s.add_argument("--host", default="127.0.0.1", help="loopback only; any other host is refused")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--out-dir", default=".", help="where Export writes recipe JSON")
    s.add_argument("--open", action="store_true", help="open the page in the default browser")
    s.set_defaults(fn=cmd_serve)
    s = sub.add_parser("export", help="share URL or hash from the explorer -> recipe JSON")
    s.add_argument("share", help="http://127.0.0.1:8765/#f=... or #f=... (quote it)")
    s.add_argument("-o", "--out", help="recipe path (default: print)")
    s.set_defaults(fn=cmd_export)
    s = sub.add_parser("measure", help="box/lacunarity of an image, profile/katz of numbers, heightmap, IFS ratios, Mandelbrot area")
    s.add_argument("what", choices=["box", "lacunarity", "profile", "katz", "heightmap", "ifs", "area"])
    s.add_argument("image", nargs="?", help="image or .npy (box, lacunarity, heightmap); numbers file (profile, katz)")
    s.add_argument("--ratios", help="ifs: piece scale ratios, comma separated")
    s.add_argument("--offsets", type=int, default=8, help="box: random grid offsets per size")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--keep-specks", action="store_true", help="box: do not remove 1-2 pixel specks")
    s.add_argument("--threshold", type=int, default=128, help="grey level; darker pixels count as filled")
    s.add_argument("--invert", action="store_true", help="lighter pixels count as filled")
    s.add_argument("--size", type=int, default=2048, help="area grid side")
    s.add_argument("--iter", type=int, default=10000)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_measure)
    s = sub.add_parser("identify", help="hand-built features of a preset, recipe, image or Julia c")
    s.add_argument("target", nargs="?")
    s.add_argument("--c", help="Julia parameter re,im")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_identify)
    s = sub.add_parser("palette", help="list palettes, print one, or write a swatch")
    s.add_argument("name", nargs="?")
    s.add_argument("-o", "--out")
    s.set_defaults(fn=cmd_palette)
    s = sub.add_parser("sheet", help="contact sheet: vary one param or palette over N values")
    s.add_argument("recipe")
    s.add_argument("-o", "--out", default="sheet.png")
    s.add_argument("--vary", help="recipe path, e.g. params.max_iter, view.width, params.c, colouring.density")
    s.add_argument("--values", help="comma separated; complex pairs as re:im")
    s.add_argument("--palettes", help="comma separated palette names")
    s.add_argument("--tile", help="tile WxH (default 200x150)")
    s.add_argument("--cols", type=int)
    s.add_argument("--iter", type=int)
    s.set_defaults(fn=cmd_sheet)
    s = sub.add_parser("zoom", help="keyframed zoom video (exponential width) -> frames + mp4 + recipe")
    _video_args(s, "zoom.mp4")
    s.add_argument("--to-width", required=True)
    s.add_argument("--from-width")
    s.add_argument("--to-centre", help="re,im: eased centre move")
    s.set_defaults(fn=cmd_zoom)
    s = sub.add_parser("morph", help="interpolate a param along keyframes (default julia c)")
    _video_args(s, "morph.mp4")
    s.add_argument("--path", required=True, help="keyframe values: 're,im;re,im;...' (or single numbers)")
    s.add_argument("--vary", default="params.c")
    s.set_defaults(fn=cmd_morph)
    s = sub.add_parser("loop", help="closed path video whose last frame wraps to the first")
    _video_args(s, "loop.mp4")
    s.add_argument("--circle", help="julia c circle: re,im,radius")
    s.add_argument("--phase", action="store_true", help="cycle the palette phase once")
    s.set_defaults(fn=cmd_loop)
    s = sub.add_parser("flashcheck", help="luminance swings per second of a video or frame folder (limit 3)")
    s.add_argument("src")
    s.add_argument("--fps", type=float, help="frame folder fps (default 24)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_flashcheck)
    import fw_extra  # book-derived commands: logistic plots, attractor-search, ifs, terrain, fif
    fw_extra.register(sub, EXPLAIN)
    import fw_gen  # flame, lsystem, attractor
    fw_gen.register(sub, EXPLAIN)
    import fw_neighbours  # reaction-diffusion, cellular automata, tilings, Kleinian limit sets
    fw_neighbours.register(sub, EXPLAIN)
    import fw_audio  # song -> frame-stepped video; live page at /audio on serve
    fw_audio.register(sub)
    import fw_3d  # 3D distance-estimator fractals, browser route only
    fw_3d.register(sub, EXPLAIN)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
