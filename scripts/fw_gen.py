"""fw_gen: generative families for fw.py: fractal flames, L-systems and 2D/3D strange attractors.

Registered by fw.py main() through register(). Flames are reimplemented from Draves and Reckase,
"The Fractal Flame Algorithm" (2003/2008); no flam3 or Apophysis code and no third-party palettes.
Reuses fw_extra (|det| probabilities, Sprott ranking, correlation dimension) and fw (palettes, PNG).
Proof bars: tests/test_gen.py, TESTS.md T-20261114-8.
"""
import json
import math
from pathlib import Path

import numpy as np

import fw_extra as fx

GEN_VERSION = 1  # recipe "gen" schema of this module


def _fw():
    return fx._fw()


def _write_recipe(png, rec):
    p = Path(str(png).rsplit(".", 1)[0] + ".json")
    p.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return p


def _palette(name):
    fw = _fw()
    return dict(fw.PALETTES[name]) if isinstance(name, str) else name


# ================================================================ flames
# theta = atan2(x, y) and phi = atan2(y, x) as in the paper's appendix.
def _v_linear(x, y, r, th, rng):
    return x, y


def _v_sinusoidal(x, y, r, th, rng):
    return np.sin(x), np.sin(y)


def _v_spherical(x, y, r, th, rng):
    r2 = r * r + 1e-12
    return x / r2, y / r2


def _v_swirl(x, y, r, th, rng):
    s, c = np.sin(r * r), np.cos(r * r)
    return x * s - y * c, x * c + y * s


def _v_horseshoe(x, y, r, th, rng):
    ri = 1.0 / (r + 1e-12)
    return ri * (x - y) * (x + y), ri * 2 * x * y


def _v_polar(x, y, r, th, rng):
    return th / math.pi, r - 1


def _v_handkerchief(x, y, r, th, rng):
    return r * np.sin(th + r), r * np.cos(th - r)


def _v_heart(x, y, r, th, rng):
    return r * np.sin(th * r), -r * np.cos(th * r)


def _v_disc(x, y, r, th, rng):
    return th / math.pi * np.sin(math.pi * r), th / math.pi * np.cos(math.pi * r)


def _v_spiral(x, y, r, th, rng):
    ri = 1.0 / (r + 1e-12)
    return ri * (np.cos(th) + np.sin(r)), ri * (np.sin(th) - np.cos(r))


def _v_hyperbolic(x, y, r, th, rng):
    return np.sin(th) / (r + 1e-12), r * np.cos(th)


def _v_julia(x, y, r, th, rng):
    om = math.pi * rng.integers(0, 2, x.shape)
    sr = np.sqrt(r)
    return sr * np.cos(th / 2 + om), sr * np.sin(th / 2 + om)


VARIATIONS = {
    "linear": _v_linear, "sinusoidal": _v_sinusoidal, "spherical": _v_spherical, "swirl": _v_swirl,
    "horseshoe": _v_horseshoe, "polar": _v_polar, "handkerchief": _v_handkerchief, "heart": _v_heart,
    "disc": _v_disc, "spiral": _v_spiral, "hyperbolic": _v_hyperbolic, "julia": _v_julia,
}

FLAME_PRESETS = {
    # affine [a, b, c, d, e, f]: (x, y) -> (a x + b y + e, c x + d y + f), as fw_extra IFS maps
    "sierpinski": {"xforms": [{"affine": m, "variations": {"linear": 1.0}, "colour": i / 2}
                              for i, m in enumerate(fx.IFS_PRESETS["sierpinski"])]},
    "swirl-sierpinski": {"xforms": [{"affine": m, "variations": {"linear": 0.6, "swirl": 0.4}, "colour": i / 2}
                                    for i, m in enumerate(fx.IFS_PRESETS["sierpinski"])],
                         "final": {"affine": [1, 0, 0, 1, -0.5, -0.29], "variations": {"spherical": 1.0}}},
}


def _apply(xf, x, y, rng):
    a, b, c, d, e, f = xf["affine"]
    u, v = a * x + b * y + e, c * x + d * y + f
    r = np.sqrt(u * u + v * v)
    th = np.arctan2(u, v)
    ox, oy = np.zeros_like(u), np.zeros_like(v)
    for name, w in xf["variations"].items():
        px, py = VARIATIONS[name](u, v, r, th, rng)
        ox += w * px
        oy += w * py
    return ox, oy


def flame_points(flame, n=1_000_000, seed=0, walkers=4096, discard=20):
    """Vectorised chaos game: `walkers` orbits in parallel, xform i chosen with its weight (default |det|).
    Returns x, y, colour index of the plotted points (after the final xform)."""
    xfs = flame["xforms"]
    w = [xf.get("weight") for xf in xfs]
    p = fx.ifs_probabilities([xf["affine"] for xf in xfs]) if None in w else np.array(w, float) / sum(w)
    rng = np.random.default_rng(seed)
    x = rng.uniform(-1, 1, walkers)
    y = rng.uniform(-1, 1, walkers)
    c = rng.uniform(0, 1, walkers)
    cols = np.array([xf.get("colour", 0.0) for xf in xfs])
    steps = -(-n // walkers)
    X, Y, C = (np.empty((steps, walkers)) for _ in range(3))
    fin = flame.get("final")
    for s in range(steps + discard):
        k = rng.choice(len(xfs), walkers, p=p)
        nx, ny = np.empty_like(x), np.empty_like(y)
        for i, xf in enumerate(xfs):
            m = k == i
            if m.any():
                nx[m], ny[m] = _apply(xf, x[m], y[m], rng)
        c = (c + cols[k]) / 2
        bad = ~np.isfinite(nx) | ~np.isfinite(ny) | (np.abs(nx) > 1e10) | (np.abs(ny) > 1e10)
        if bad.any():
            nx[bad] = rng.uniform(-1, 1, bad.sum())
            ny[bad] = rng.uniform(-1, 1, bad.sum())
        x, y = nx, ny
        if s >= discard:
            px, py, pc = x, y, c
            if fin:
                px, py = _apply(fin, x, y, rng)
                pc = (c + fin.get("colour", c)) / 2 if "colour" in fin else c
            X[s - discard], Y[s - discard], C[s - discard] = px, py, pc
    X, Y, C = X.ravel()[:n], Y.ravel()[:n], C.ravel()[:n]
    ok = np.isfinite(X) & np.isfinite(Y)
    return X[ok], Y[ok], C[ok]


def auto_view(x, y, q=0.5):
    lo = np.percentile(x, q), np.percentile(y, q)
    hi = np.percentile(x, 100 - q), np.percentile(y, 100 - q)
    return [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2], max(hi[0] - lo[0], hi[1] - lo[1]) * 1.08 or 1.0


def histogram(x, y, c, w, h, centre, width, pal):
    """Accumulate count and palette colour per pixel (y up)."""
    sc = w / width
    u = np.floor((x - centre[0]) * sc + w / 2)
    v = np.floor(h / 2 - (y - centre[1]) * sc)
    ok = (u >= 0) & (u < w) & (v >= 0) & (v < h)
    idx = (v[ok] * w + u[ok]).astype(np.int64)
    cnt = np.bincount(idx, minlength=w * h).astype(float)
    rgb = _fw().palette_rgb(pal, c[ok])
    acc = np.stack([np.bincount(idx, rgb[:, k], w * h) for k in range(3)], -1)
    return cnt.reshape(h, w), acc.reshape(h, w, 3)


def _blur3(a):
    p = np.pad(a, [(1, 1), (1, 1)] + [(0, 0)] * (a.ndim - 2), mode="edge")
    k = (1, 2, 1)
    out = sum(k[i] * k[j] * p[i:i + a.shape[0], j:j + a.shape[1]] for i in range(3) for j in range(3))
    return out / 16.0


def density_estimate(cnt, acc, thresh=4):
    """Cheap density estimation: pixels with fewer than `thresh` hits take a 3x3 blurred value (twice for 1 hit)."""
    b1c, b1a = _blur3(cnt), _blur3(acc)
    b2c, b2a = _blur3(b1c), _blur3(b1a)
    lo = (cnt < thresh)[..., None]
    one = (cnt <= 1)[..., None]
    acc = np.where(one, b2a, np.where(lo, b1a, acc))
    cnt = np.where(one[..., 0], b2c, np.where(lo[..., 0], b1c, cnt))
    return cnt, acc


def tone_map(cnt, acc, gamma=2.2, vibrancy=1.0, brightness=1.0, background=(0, 0, 0)):
    """Log-density alpha, colour = average colour; gamma with vibrancy blend (Draves and Reckase sec. 4)."""
    mx = max(cnt.max(), 1.0)
    alpha = np.log1p(cnt * brightness) / math.log1p(mx * brightness)
    avg = acc / np.maximum(cnt, 1e-12)[..., None]
    a = alpha[..., None]
    g = 1.0 / gamma
    col = vibrancy * avg * a ** g + (1 - vibrancy) * (avg * a) ** g
    bg = np.array(background, float) / 255.0
    out = col + (1 - np.minimum(a ** g, 1)) * bg
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def flame_render(flame, w=400, h=400, n=1_000_000, seed=0, supersample=1, gamma=2.2, vibrancy=1.0,
                 palette="classic", view=None, density=True):
    """Returns (rgb uint8 array, counts at output size, view)."""
    x, y, c = flame_points(flame, n, seed)
    if view is None:
        centre, width = auto_view(x, y)
    else:
        centre, width = [float(v) for v in view["centre"]], float(view["width"])
    ss = max(1, int(supersample))
    cnt, acc = histogram(x, y, c, w * ss, h * ss, centre, width, _palette(palette))
    if ss > 1:
        cnt = cnt.reshape(h, ss, w, ss).sum((1, 3))
        acc = acc.reshape(h, ss, w, ss, 3).sum((1, 3))
    raw = cnt.copy()
    if density:
        cnt, acc = density_estimate(cnt, acc)
    return tone_map(cnt, acc, gamma, vibrancy), raw, {"centre": [repr(float(centre[0])), repr(float(centre[1]))], "width": repr(float(width))}


def flame_score(raw):
    """Keep-only-good-ones score: coverage of hit pixels in a useful band, not blank, not one blob."""
    cov = float((raw > 0).mean())
    if raw.max() <= 0 or cov < 0.02:
        return 0.0, cov
    # spread: share of hits outside the busiest 1% of pixels (a point or a line scores low)
    flat = np.sort(raw.ravel())[::-1]
    top = flat[: max(1, flat.size // 100)].sum() / flat.sum()
    band = 1.0 if 0.05 <= cov <= 0.6 else 0.5
    return float(band * min(cov, 0.6) * (1 - top)), cov


def random_flame(rng, k=None):
    names = list(VARIATIONS)
    k = k or int(rng.integers(2, 5))
    xfs = []
    for i in range(k):
        while True:
            m = rng.uniform(-1, 1, 6)
            if 0.05 < abs(m[0] * m[3] - m[1] * m[2]) < 0.9:
                break
        vs = rng.choice(names, int(rng.integers(1, 3)), replace=False)
        wt = rng.dirichlet(np.ones(len(vs)))
        xfs.append({"affine": [round(float(v), 4) for v in m],
                    "variations": {str(v): round(float(t), 4) for v, t in zip(vs, wt)},
                    "colour": round(i / max(k - 1, 1), 4)})
    fl = {"xforms": xfs}
    if rng.random() < 0.3:
        fl["final"] = {"affine": [1, 0, 0, 1, 0, 0], "variations": {str(rng.choice(names)): 1.0}}
    return fl


def flame_search(seed=0, tries=24, keep=1, size=96, n=60000):
    """Seeded random flames scored at low resolution; returns [(score, coverage, flame)] best first."""
    rng = np.random.default_rng(seed)
    out = []
    for t in range(tries):
        fl = random_flame(rng)
        _, raw, _ = flame_render(fl, size, size, n, seed=t, density=False)
        sc, cov = flame_score(raw)
        if sc > 0:
            out.append((sc, cov, fl))
    out.sort(key=lambda r: -r[0])
    return out[:keep]


def cmd_flame(a):
    if a.recipe and a.recipe.endswith(".json"):
        rec = json.loads(Path(a.recipe).read_text(encoding="utf-8"))
        fl, p = rec["params"]["flame"], rec["params"]
        seed, name = rec.get("seed", 0), rec.get("formula", "random")
    else:
        p = {}
        seed, name = a.seed, a.recipe or "random"
        if a.recipe in FLAME_PRESETS:
            fl = FLAME_PRESETS[a.recipe]
        else:
            best = flame_search(a.seed, a.tries)
            if not best:
                print("no flame passed the score; try another --seed or more --tries")
                return 1
            sc, cov, fl = best[0]
            print(f"random flame: score {sc:.3f}, coverage {cov:.3f} (best of {a.tries})")
    w, h = (int(v) for v in (a.size or p.get("size", "400x400")).split("x"))
    n = a.points or p.get("points", 1_000_000)
    ss = a.supersample or p.get("supersample", 2)
    gamma, vib = a.gamma or p.get("gamma", 2.2), a.vibrancy if a.vibrancy is not None else p.get("vibrancy", 1.0)
    pal = a.palette or p.get("palette", "classic")
    img, raw, view = flame_render(fl, w, h, n, seed, ss, gamma, vib, pal, p.get("view"))
    _fw().write_png(a.out, arr=img)
    rec = {"fractalwright": _fw().VERSION, "family": "flame", "formula": name,
           "params": {"flame": fl, "size": f"{w}x{h}", "points": n, "supersample": ss, "gamma": gamma,
                      "vibrancy": vib, "palette": pal, "view": view},
           "seed": seed, "render": {"route": "numpy"}, "ai_pass": None}
    print(f"wrote {a.out} and {_write_recipe(a.out, rec)} (coverage {float((raw > 0).mean()):.3f})")
    return 0


# ================================================================ L-systems
LSYSTEMS = {
    # ABOP = Prusinkiewicz and Lindenmayer, The Algorithmic Beauty of Plants (1990), figures cited.
    "koch": {"axiom": "F", "rules": {"F": "F+F--F+F"}, "angle": 60, "n": 5},
    "koch-snowflake": {"axiom": "F--F--F", "rules": {"F": "F+F--F+F"}, "angle": 60, "n": 4},
    "dragon": {"axiom": "FX", "rules": {"X": "X+YF+", "Y": "-FX-Y"}, "angle": 90, "n": 12},
    "hilbert": {"axiom": "A", "rules": {"A": "+BF-AFA-FB+", "B": "-AF+BFB+FA-"}, "angle": 90, "n": 5},
    "sierpinski-arrowhead": {"axiom": "A", "rules": {"A": "B-A-B", "B": "A+B+A"}, "angle": 60, "n": 7,
                             "draw": "AB"},
    "plant-a": {"axiom": "F", "rules": {"F": "F[+F]F[-F]F"}, "angle": 25.7, "n": 5, "heading": 90},  # ABOP 1.24a
    "plant-b": {"axiom": "F", "rules": {"F": "F[+F]F[-F][F]"}, "angle": 20, "n": 5, "heading": 90},  # 1.24b
    "plant-d": {"axiom": "X", "rules": {"X": "F[+X]F[-X]+X", "F": "FF"}, "angle": 20, "n": 7, "heading": 90},  # 1.24d
    "plant-e": {"axiom": "X", "rules": {"X": "F[+X][-X]FX", "F": "FF"}, "angle": 25.7, "n": 7, "heading": 90},  # 1.24e
    "plant-f": {"axiom": "X", "rules": {"X": "F-[[X]+X]+F[+FX]-X", "F": "FF"}, "angle": 22.5, "n": 5,
                "heading": 90},  # 1.24f
    "plant-stochastic": {"axiom": "F", "rules": {"F": [[0.33, "F[+F]F[-F]F"], [0.33, "F[+F]F"], [0.34, "F[-F]F"]]},
                         "angle": 25.7, "n": 5, "heading": 90},  # ABOP 1.27
}


def lsystem_expand(axiom, rules, n, seed=0, limit=5_000_000):
    rng = np.random.default_rng(seed)
    s = axiom
    for _ in range(n):
        out = []
        for ch in s:
            r = rules.get(ch)
            if r is None:
                out.append(ch)
            elif isinstance(r, str):
                out.append(r)
            else:
                ps = np.array([p for p, _ in r], float)
                out.append(r[rng.choice(len(r), p=ps / ps.sum())][1])
        s = "".join(out)
        if len(s) > limit:
            raise ValueError(f"string over {limit} symbols; lower n")
    return s


def turtle(s, angle, draw="FG", move="f", heading=0.0):
    """2D turtle: draw symbols go forward 1 with a line, `move` without; + left, - right, | turn around,
    [ ] push and pop. Returns segments (k, 4) and the visited vertices."""
    x = y = 0.0
    hd = math.radians(heading)
    da = math.radians(angle)
    stack, segs, verts = [], [], [(0.0, 0.0)]
    for ch in s:
        if ch in draw or ch in move:
            nx, ny = x + math.cos(hd), y + math.sin(hd)
            if ch in draw:
                segs.append((x, y, nx, ny))
            x, y = nx, ny
            verts.append((x, y))
        elif ch == "+":
            hd += da
        elif ch == "-":
            hd -= da
        elif ch == "|":
            hd += math.pi
        elif ch == "[":
            stack.append((x, y, hd))
        elif ch == "]":
            x, y, hd = stack.pop()
    return np.array(segs, float).reshape(-1, 4), np.array(verts)


def _frame(segs, w, h, pad=0.04):
    xs, ys = segs[:, [0, 2]], segs[:, [1, 3]]
    lo = np.array([xs.min(), ys.min()])
    span = max(xs.max() - lo[0], ys.max() - lo[1]) or 1.0
    sc = min(w, h) * (1 - 2 * pad) / span
    off = np.array([(w - (xs.max() - lo[0]) * sc) / 2, (h - (ys.max() - lo[1]) * sc) / 2])
    return lo, sc, off


def segments_mask(segs, w, h):
    lo, sc, off = _frame(segs, w, h)
    p0 = (segs[:, :2] - lo) * sc + off
    p1 = (segs[:, 2:] - lo) * sc + off
    L = np.hypot(*(p1 - p0).T)
    k = np.maximum(np.ceil(L * 2).astype(int), 1)
    rep = np.repeat(np.arange(len(segs)), k + 1)
    t = (np.arange(rep.size) - np.repeat(np.cumsum(k + 1) - (k + 1), k + 1)) / np.repeat(k, k + 1)
    pts = p0[rep] + (p1[rep] - p0[rep]) * t[:, None]
    u = np.clip(pts[:, 0].astype(int), 0, w - 1)
    v = np.clip((h - 1 - pts[:, 1]).astype(int), 0, h - 1)
    m = np.zeros((h, w), bool)
    m[v, u] = True
    return m


def segments_svg(segs, path, w, h, stroke="#1b1b1b", width=1.0):
    lo, sc, off = _frame(segs, w, h)
    p0 = (segs[:, :2] - lo) * sc + off
    p1 = (segs[:, 2:] - lo) * sc + off
    d, last = [], None
    for (a, b), (c, e) in zip(p0, p1):
        if last is None or abs(last[0] - a) > 1e-6 or abs(last[1] - b) > 1e-6:
            d.append(f"M{a:.2f} {h - b:.2f}")
        d.append(f"L{c:.2f} {h - e:.2f}")
        last = (c, e)
    Path(path).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<rect width="100%" height="100%" fill="#ffffff"/><path d="{" ".join(d)}" fill="none" '
        f'stroke="{stroke}" stroke-width="{width}" stroke-linecap="round"/></svg>\n', encoding="utf-8")
    return path


def lsystem_build(spec, n=None, seed=0):
    s = lsystem_expand(spec["axiom"], spec["rules"], spec["n"] if n is None else n, seed)
    return turtle(s, spec["angle"], spec.get("draw", "FG"), spec.get("move", "f"), spec.get("heading", 0.0))


def cmd_lsystem(a):
    if a.preset.endswith(".json"):
        rec = json.loads(Path(a.preset).read_text(encoding="utf-8"))
        spec, name, seed = rec["params"]["lsystem"], rec.get("formula", "custom"), rec.get("seed", 0)
    else:
        spec, name, seed = dict(LSYSTEMS[a.preset]), a.preset, a.seed
    if a.n is not None:
        spec["n"] = a.n
    segs, _ = lsystem_build(spec, seed=seed)
    w, h = (int(v) for v in a.size.split("x"))
    m = segments_mask(segs, w, h)
    _fw().write_png(a.out, arr=np.where(m, 27, 255).astype(np.uint8))
    svg = segments_svg(segs, str(a.out).rsplit(".", 1)[0] + ".svg", w, h)
    rec = {"fractalwright": _fw().VERSION, "family": "lsystem", "formula": name,
           "params": {"lsystem": spec, "size": f"{w}x{h}"}, "seed": seed, "render": {"route": "numpy"}, "ai_pass": None}
    print(f"wrote {a.out}, {svg} and {_write_recipe(a.out, rec)} ({len(segs)} segments)")
    return 0


# ================================================================ attractors
def clifford_step(p):
    a, b, c, d = p
    return lambda x, y: (np.sin(a * y) + c * np.cos(a * x), np.sin(b * x) + d * np.cos(b * y))


def dejong_step(p):
    a, b, c, d = p
    return lambda x, y: (np.sin(a * y) - np.cos(b * x), np.sin(c * x) - np.cos(d * y))


def icon_step(p):
    """Field and Golubitsky symmetric icon: z' = (l + a|z|^2 + b Re(z^n) + i w) z + g conj(z)^(n-1)."""
    lam, al, be, ga, om, n = p
    n = int(n)

    def f(x, y):
        z = x + 1j * y
        zn = z ** n
        z2 = (z * np.conj(z)).real
        z1 = (lam + al * z2 + be * zn.real + 1j * om) * z + ga * np.conj(z) ** (n - 1)
        return z1.real, z1.imag
    return f


ATTRACTORS = {
    # Bourke [S3], [S4] in references/05 section 4
    "clifford": {"step": clifford_step, "params": [-1.4, 1.6, 1.0, 0.7]},
    "dejong": {"step": dejong_step, "params": [1.641, 1.902, 0.316, 1.525]},
    # icon sets recalled from common icon galleries citing Field and Golubitsky (1992); checked bounded and
    # symmetric by tests, not checked against the book (references/05 open question)
    "icon": {"step": icon_step, "params": [-2.08, 1.0, -0.1, 0.167, 0.0, 7]},
    "icon-3": {"step": icon_step, "params": [1.56, -1.0, 0.1, -0.82, 0.0, 3]},
    "lorenz": {"params": [10.0, 28.0, 8.0 / 3.0]},
}


def map_points(step, n=1_000_000, seed=0, walkers=1024, warm=200):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-0.1, 0.1, walkers)
    y = rng.uniform(-0.1, 0.1, walkers)
    steps = -(-n // walkers)
    X, Y = np.empty((steps, walkers)), np.empty((steps, walkers))
    for s in range(steps + warm):
        x, y = step(x, y)
        if s >= warm:
            X[s - warm], Y[s - warm] = x, y
    X, Y = X.ravel()[:n], Y.ravel()[:n]
    ok = np.isfinite(X) & np.isfinite(Y) & (np.abs(X) < 1e6) & (np.abs(Y) < 1e6)
    return np.column_stack([X[ok], Y[ok]])


def lorenz(n=100000, dt=0.01, p=(10.0, 28.0, 8.0 / 3.0), warm=2000, start=(1.0, 1.0, 1.0)):
    """RK4 integration; returns (n, 3) points after `warm` transient steps."""
    s, r, b = p

    def f(v):
        x, y, z = v
        return np.array([s * (y - x), x * (r - z) - y, x * y - b * z])
    v = np.array(start, float)
    out = np.empty((n, 3))
    for i in range(n + warm):
        k1 = f(v)
        k2 = f(v + dt / 2 * k1)
        k3 = f(v + dt / 2 * k2)
        k4 = f(v + dt * k3)
        v = v + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        if i >= warm:
            out[i - warm] = v
    return out


def density_png(pts, path, w=600, h=600, palette="fire", gamma=2.2):
    """Log-density shading through a palette on black."""
    lo, hi = pts.min(0), pts.max(0)
    span = (hi - lo).max() * 1.05 or 1.0
    c = (lo + hi) / 2
    u = ((pts[:, 0] - c[0]) / span * min(w, h) + w / 2).astype(int)
    v = (h / 2 - (pts[:, 1] - c[1]) / span * min(w, h)).astype(int)
    ok = (u >= 0) & (u < w) & (v >= 0) & (v < h)
    cnt = np.bincount(v[ok] * w + u[ok], minlength=w * h).reshape(h, w).astype(float)
    t = np.log1p(cnt) / max(np.log1p(cnt.max()), 1e-9)
    rgb = _fw().palette_rgb(_palette(palette), 0.15 + 0.7 * t) * (t ** (1 / gamma))[..., None]
    img = (np.clip(rgb, 0, 1) * 255 + 0.5).astype(np.uint8)
    _fw().write_png(path, arr=img)
    return img, cnt


def attractor_search2(kind, hits=3, seed=0, n=11000, max_tries=400):
    """Random Clifford/de Jong parameters in [-2.5, 2.5]; Sprott tests and ranking from fw_extra."""
    rng = np.random.default_rng(seed)
    found, tries = [], 0
    stepf = ATTRACTORS[kind]["step"]
    while len(found) < hits and tries < max_tries:
        tries += 1
        p = [round(float(v), 3) for v in rng.uniform(-2.5, 2.5, 4)]
        st = stepf(p)
        lyap, pts = fx.orbit_lyapunov(lambda x, y: tuple(float(v) for v in st(x, y)), n=n)
        if lyap is None or lyap <= 0.005:
            continue
        d2 = fx.correlation_dimension(pts)
        found.append({"params": p, "lyapunov_bits": round(lyap, 4), "d2": round(d2, 3),
                      "score": round(fx.preference_score(d2, lyap), 4)})
    found.sort(key=lambda h: h["score"])
    return found, tries


def cmd_attractor(a):
    kind = a.kind
    params = [float(v) for v in a.params.split(",")] if a.params else list(ATTRACTORS[kind]["params"])
    if a.search:
        if kind not in ("clifford", "dejong"):
            print("search: clifford or dejong")
            return 2
        hits, tries = attractor_search2(kind, a.hits, a.seed)
        print(f"{len(hits)} {kind} attractors in {tries} tries (Sprott ranking: D2 1.1-1.5, small L)")
        for h in hits:
            print(f"  {h['params']}  L {h['lyapunov_bits']} bits/iter  D2 {h['d2']}  score {h['score']}")
        if not hits:
            return 1
        params = hits[0]["params"]
    w, h = (int(v) for v in a.size.split("x"))
    if kind == "lorenz":
        pts3 = lorenz(a.points // 4, p=params)
        pts = pts3[:, [0, 2]]
    else:
        pts = map_points(ATTRACTORS[kind]["step"](params), a.points, a.seed)
    _, cnt = density_png(pts, a.out, w, h, a.palette)
    rec = {"fractalwright": _fw().VERSION, "family": "attractor", "formula": kind,
           "params": {"coefficients": params, "points": a.points, "size": f"{w}x{h}", "palette": a.palette,
                      "projection": "x,z" if kind == "lorenz" else "x,y"},
           "seed": a.seed, "render": {"route": "numpy"}, "ai_pass": None}
    print(f"wrote {a.out} and {_write_recipe(a.out, rec)} (coverage {float((cnt > 0).mean()):.3f})")
    return 0


# ================================================================ registration
EXPLAIN_GEN = {
    "flame": "Fractal flame (Draves and Reckase): chaos game over xforms (affine then a weighted sum of variations), "
             "colour index averaged with each xform's colour, log-density histogram, gamma with vibrancy, "
             "supersampling and density estimation. `fw.py flame [preset|recipe.json]`; no preset = seeded random "
             "flame kept only if its coverage score passes.",
    "lsystem": "L-system: parallel string rewriting (bracketed, stochastic with a seed) drawn by a 2D turtle. "
               "Presets: Koch, snowflake, dragon, Hilbert, Sierpinski arrowhead, ABOP plants. PNG + SVG.",
    "attractor": "Strange attractors: Clifford, de Jong, symmetric icons (Field and Golubitsky), Lorenz (RK4, x-z "
                 "projection), log-density shading. `--search` ranks random Clifford/de Jong sets by Sprott's rule.",
}


def register(sub, explain):
    explain.update(EXPLAIN_GEN)
    s = sub.add_parser("flame", help="fractal flame: preset, recipe JSON, or seeded random (scored)")
    s.add_argument("recipe", nargs="?", help=f"preset ({', '.join(FLAME_PRESETS)}) or recipe.json; omit for random")
    s.add_argument("-o", "--out", default="flame.png")
    s.add_argument("--size")
    s.add_argument("--points", type=int)
    s.add_argument("--supersample", type=int)
    s.add_argument("--gamma", type=float)
    s.add_argument("--vibrancy", type=float)
    s.add_argument("--palette")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--tries", type=int, default=24, help="random: candidates scored")
    s.set_defaults(fn=cmd_flame)
    s = sub.add_parser("lsystem", help="L-system turtle drawing -> PNG + SVG + recipe")
    s.add_argument("preset", help=f"{', '.join(LSYSTEMS)} or recipe.json")
    s.add_argument("-o", "--out", default="lsystem.png")
    s.add_argument("--n", type=int, help="iterations (default per preset)")
    s.add_argument("--size", default="800x800")
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cmd_lsystem)
    s = sub.add_parser("attractor", help="Clifford, de Jong, icon, Lorenz with density shading; --search")
    s.add_argument("kind", choices=list(ATTRACTORS))
    s.add_argument("-o", "--out", default="attractor.png")
    s.add_argument("--params", help="comma separated coefficients")
    s.add_argument("--points", type=int, default=1_000_000)
    s.add_argument("--size", default="600x600")
    s.add_argument("--palette", default="fire")
    s.add_argument("--search", action="store_true")
    s.add_argument("--hits", type=int, default=3)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cmd_attractor)
