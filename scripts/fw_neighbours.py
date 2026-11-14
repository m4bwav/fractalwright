"""fw_neighbours: the fractal neighbours Mark put in scope: reaction-diffusion (Gray-Scott),
cellular automata (elementary 1D and Life-like 2D), tilings (regular and Penrose P3) and
Kleinian limit sets (Apollonian gasket by Descartes circles, two-generator groups by inverse
iteration with the Indra's Pearls "Grandma's recipe").

Registered by fw.py main() through register(). Every command writes a PNG and a recipe JSON
next to it. Sources: references/12-neighbours.md. Proof bars: tests/test_neighbours.py,
TESTS.md T-20261114-12.
"""
import cmath
import json
import math
from pathlib import Path

import numpy as np

NB_VERSION = 1  # recipe schema of this module


def _fw():
    import fw
    return fw


def _write_recipe(png, rec):
    p = Path(str(png).rsplit(".", 1)[0] + ".json")
    p.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    return p


def _size(s):
    w, h = (int(v) for v in str(s).split("x"))
    return w, h


def _recipe(family, formula, params, seed=0):
    return {"fractalwright": _fw().VERSION, "neighbours": NB_VERSION, "family": family, "formula": formula,
            "params": params, "seed": seed, "render": {"route": "numpy"}, "ai_pass": None}


def _load(arg, family):
    """Preset name or a recipe JSON of this family -> (formula, params, seed) or None."""
    if str(arg).endswith(".json"):
        rec = json.loads(Path(arg).read_text(encoding="utf-8"))
        if rec.get("family") != family:
            raise SystemExit(f"{arg} is a {rec.get('family')} recipe, not {family}")
        return rec["formula"], rec["params"], rec.get("seed", 0)
    return None


# ================================================================ reaction-diffusion
# Gray-Scott as on Karl Sims' tutorial (fetched 2026-11-14): DA 1.0, DB 0.5, dt 1.0,
# 3x3 Laplacian centre -1, edge neighbours 0.2, diagonals 0.05.
RD_PRESETS = {
    "default": {"f": 0.055, "k": 0.062},
    "coral": {"f": 0.0545, "k": 0.062},
    "mitosis": {"f": 0.0367, "k": 0.0649},
}
RD_DA, RD_DB, RD_DT = 1.0, 0.5, 1.0


def _lap(a):
    n = (np.roll(a, 1, 0) + np.roll(a, -1, 0) + np.roll(a, 1, 1) + np.roll(a, -1, 1))
    d = (np.roll(np.roll(a, 1, 0), 1, 1) + np.roll(np.roll(a, 1, 0), -1, 1)
         + np.roll(np.roll(a, -1, 0), 1, 1) + np.roll(np.roll(a, -1, 0), -1, 1))
    return 0.2 * n + 0.05 * d - a


def gray_scott(f, k, w=256, h=256, steps=5000, seed=0, seeds=12, da=RD_DA, db=RD_DB, dt=RD_DT):
    """Wrapping grid, A=1 B=0, one centre square plus `seeds` random squares perturbed.
    Returns B (float64, h x w). Same arguments -> same array."""
    rng = np.random.default_rng(seed)
    A = np.ones((h, w))
    B = np.zeros((h, w))
    s = max(3, min(w, h) // 20)
    sq = [(h // 2 - s, w // 2 - s, 2 * s)] + [(int(rng.integers(0, h - s)), int(rng.integers(0, w - s)), s)
                                               for _ in range(seeds)]
    for y, x, e in sq:  # seeded squares at A 0.5, B 0.25 (Pearson's perturbation, recalled): B 1 can blow up
        A[y:y + e, x:x + e] = 0.5
        B[y:y + e, x:x + e] = 0.25
    for _ in range(steps):
        abb = A * B * B
        A, B = (A + (da * _lap(A) - abb + f * (1 - A)) * dt,
                B + (db * _lap(B) + abb - (k + f) * B) * dt)
    return B


def cmd_rd(a):
    got = _load(a.preset, "reaction-diffusion")
    if got:
        name, p, seed = got
    else:
        if a.preset not in RD_PRESETS:
            raise SystemExit(f"unknown preset {a.preset}; have {', '.join(RD_PRESETS)}")
        name, seed = a.preset, a.seed
        w, h = _size(a.size)
        p = dict(RD_PRESETS[a.preset], w=w, h=h, steps=a.steps, seeds=12, da=RD_DA, db=RD_DB, dt=RD_DT)
        if a.f is not None:
            p["f"] = a.f
        if a.k is not None:
            p["k"] = a.k
    B = gray_scott(p["f"], p["k"], p["w"], p["h"], p["steps"], seed, p["seeds"], p["da"], p["db"], p["dt"])
    img = np.clip(255 - B / max(B.max(), 1e-9) * 255, 0, 255).astype(np.uint8)
    _fw().write_png(a.out, arr=img)
    rec = _recipe("reaction-diffusion", name, p, seed)
    print(f"wrote {a.out} and {_write_recipe(a.out, rec)} (B max {B.max():.3f})")
    return 0


# ================================================================ cellular automata
def elementary(rule, steps=255, width=None, init="single", seed=0):
    """Wolfram elementary CA. Rows are time; width defaults to 2*steps+1. Zero boundary."""
    width = width or 2 * steps + 1
    table = np.array([(rule >> i) & 1 for i in range(8)], np.uint8)
    row = np.zeros(width, np.uint8)
    if init == "single":
        row[width // 2] = 1
    else:
        row = np.random.default_rng(seed).integers(0, 2, width).astype(np.uint8)
    out = np.zeros((steps + 1, width), bool)
    out[0] = row
    for t in range(steps):
        l, r = np.pad(row, 1)[:-2], np.pad(row, 1)[2:]
        row = table[(l << 2) | (row << 1) | r]
        out[t + 1] = row
    return out


def parse_bs(rule):
    """'B3/S23' -> (birth set, survive set)."""
    b, s = set(), set()
    for part in rule.upper().replace(" ", "").split("/"):
        if part.startswith("B"):
            b = {int(c) for c in part[1:]}
        elif part.startswith("S"):
            s = {int(c) for c in part[1:]}
        else:
            raise ValueError(f"bad rule part {part!r}; want e.g. B3/S23")
    return b, s


def lifelike(rule="B3/S23", w=200, h=200, steps=200, density=0.3, seed=0):
    """Life-like CA on a torus from a seeded random soup; returns the final state."""
    b, s = parse_bs(rule)
    g = np.random.default_rng(seed).random((h, w)) < density
    bm, sm = np.zeros(9, bool), np.zeros(9, bool)
    bm[list(b)] = True
    sm[list(s)] = True
    for _ in range(steps):
        n = sum(np.roll(np.roll(g, dy, 0), dx, 1).astype(np.int8)
                for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
        g = np.where(g, sm[n], bm[n])
    return g


def cmd_ca(a):
    if a.rule.isdigit():
        r = int(a.rule)
        if not 0 <= r <= 255:
            raise SystemExit("elementary rule must be 0..255")
        m = elementary(r, a.steps, a.width, a.init, a.seed)
        p = {"kind": "elementary", "rule": r, "steps": a.steps, "width": m.shape[1], "init": a.init}
    else:
        w, h = _size(a.size)
        m = lifelike(a.rule, w, h, a.steps, a.density, a.seed)
        p = {"kind": "lifelike", "rule": a.rule.upper(), "w": w, "h": h, "steps": a.steps, "density": a.density}
    _fw().write_png(a.out, arr=np.where(m, 27, 255).astype(np.uint8))
    rec = _recipe("cellular-automaton", f"rule-{a.rule}", p, a.seed)
    print(f"wrote {a.out} and {_write_recipe(a.out, rec)} ({int(m.sum())} live cells)")
    return 0


# ================================================================ tilings
PHI = (1 + 5 ** 0.5) / 2


def regular_segments(kind="square", n=8):
    """Edges of a regular tiling covering about n x n tiles of unit edge."""
    segs = []
    if kind == "square":
        for i in range(n + 1):
            segs += [(i, 0, i, n), (0, i, n, i)]
    elif kind == "triangle":
        hgt = 3 ** 0.5 / 2
        for j in range(n):
            for i in range(n):
                x0, y0 = i + 0.5 * (j % 2), j * hgt
                p, q, r = (x0, y0), (x0 + 1, y0), (x0 + 0.5, y0 + hgt)
                segs += [(*p, *q), (*q, *r), (*r, *p)]
                if i < n - 1 or j % 2 == 0:
                    s_ = (x0 + 1.5, y0 + hgt)
                    segs += [(*q, *s_), (*r, *s_)]
    elif kind == "hex":
        for q in range(n):
            for r in range(n):
                cx, cy = 1.5 * q, 3 ** 0.5 * (r + 0.5 * (q % 2))
                pts = [(cx + math.cos(math.pi / 3 * j), cy + math.sin(math.pi / 3 * j)) for j in range(7)]
                segs += [(*pts[j], *pts[j + 1]) for j in range(6)]
    else:
        raise ValueError(kind)
    return np.array(segs, float)


def penrose_triangles(n=6):
    """P3 rhomb tiling by Robinson-triangle substitution from a 10-triangle sun."""
    tris = []
    for i in range(10):
        b = cmath.rect(1, (2 * i - 1) * math.pi / 10)
        c = cmath.rect(1, (2 * i + 1) * math.pi / 10)
        if i % 2 == 0:
            b, c = c, b
        tris.append((0, 0j, b, c))
    for _ in range(n):
        new = []
        for col, A, B, C in tris:
            if col == 0:
                P = A + (B - A) / PHI
                new += [(0, C, P, B), (1, P, C, A)]
            else:
                Q = B + (A - B) / PHI
                R = B + (C - B) / PHI
                new += [(1, R, C, A), (1, Q, R, B), (0, R, Q, A)]
        tris = new
    return tris


def penrose_segments(n=6):
    """Rhomb edges only: each Robinson triangle draws A-B and A-C, never the base B-C
    (the base is the rhomb diagonal shared with its mirror twin)."""
    segs = []
    for _, A, B, C in penrose_triangles(n):
        segs += [(A.real, A.imag, B.real, B.imag), (A.real, A.imag, C.real, C.imag)]
    return np.array(segs, float)


def tiling_mask(kind, n, w, h):
    import fw_gen
    segs = penrose_segments(n) if kind == "penrose" else regular_segments(kind, n)
    return fw_gen.segments_mask(segs, w, h), segs


def cmd_tiling(a):
    w, h = _size(a.size)
    n = a.n if a.n is not None else (6 if a.kind == "penrose" else 8)
    m, segs = tiling_mask(a.kind, n, w, h)
    _fw().write_png(a.out, arr=np.where(m, 27, 255).astype(np.uint8))
    rec = _recipe("tiling", a.kind, {"n": n, "w": w, "h": h}, 0)
    print(f"wrote {a.out} and {_write_recipe(a.out, rec)} ({len(segs)} edges). "
          "A tiling is not a fractal: fw.py measure box on it should not say fractal-like.")
    return 0


# ================================================================ Kleinian limit sets
def apollonian_circles(min_r=1e-3):
    """Descartes reflection: replacing circle i of a tangent quadruple gives
    k_i' = 2 (sum of other k) - k_i, same for k*z. Returns [(z, r)] including the outer circle."""
    r = 2 * 3 ** 0.5 - 3
    inner = [(1 / r, cmath.rect(1 - r, math.pi / 2 + j * 2 * math.pi / 3)) for j in range(3)]
    quad = [(-1.0, 0j)] + inner
    q = [(k, k * z) for k, z in quad]
    out = [(0j, 1.0)] + [(z, 1 / k) for k, z in inner]

    def flip(qd, i):
        ks = sum(x[0] for j, x in enumerate(qd) if j != i)
        kz = sum(x[1] for j, x in enumerate(qd) if j != i)
        return (2 * ks - qd[i][0], 2 * kz - qd[i][1])
    stack = []
    for i in range(4):
        c = flip(q, i)
        nq = list(q)
        nq[i] = c
        stack.append((nq, i))
    while stack:
        qd, i = stack.pop()
        k, kz = qd[i]
        if k <= 0 or 1 / k < min_r:
            continue
        out.append((kz / k, 1 / k))
        for j in range(4):
            if j != i:
                nq = list(qd)
                nq[j] = flip(qd, j)
                stack.append((nq, j))
    return out


def circles_mask(circles, size):
    """Outline of each circle sampled at two points per pixel of circumference."""
    sc = (size - 1) / 2.0
    zs = np.array([c[0] for c in circles])
    rs = np.array([c[1] for c in circles])
    n = np.maximum(np.ceil(2 * math.pi * rs * sc * 2).astype(int), 8)
    idx = np.repeat(np.arange(len(rs)), n)
    start = np.repeat(np.cumsum(n) - n, n)
    t = (np.arange(idx.size) - start) / n[idx] * 2 * math.pi
    pts = zs[idx] + rs[idx] * np.exp(1j * t)
    u = np.clip(np.round((pts.real + 1) * sc).astype(int), 0, size - 1)
    v = np.clip(np.round((1 - pts.imag) * sc).astype(int), 0, size - 1)
    m = np.zeros((size, size), bool)
    m[v, u] = True
    return m


def grandma(ta, tb, plus=False):
    """Indra's Pearls 'Grandma's recipe' (recalled from the book, Mumford, Series, Wright 2002):
    generators a, b with trace a = ta, trace b = tb and commutator trace -2 (parabolic).
    ta = tb = 2 gives the Apollonian gasket group."""
    s = cmath.sqrt(ta * ta * tb * tb - 4 * (ta * ta + tb * tb))
    tab = (ta * tb + s) / 2 if plus else (ta * tb - s) / 2
    z0 = (tab - 2) * tb / (tb * tab - 2 * ta + 2j * tab)
    a = np.array([[ta / 2, (ta * tab - 2 * tb + 4j) / ((2 * tab + 4) * z0)],
                  [(ta * tab - 2 * tb - 4j) * z0 / (2 * tab - 4), ta / 2]], complex)
    b = np.array([[(tb - 2j) / 2, tb / 2], [tb / 2, (tb + 2j) / 2]], complex)
    return a, b


def _inv(m):
    return np.array([[m[1, 1], -m[0, 1]], [-m[1, 0], m[0, 0]]]) / (m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0])


def limit_points(ta, tb, points=300_000, seed=0, walkers=2000):
    """Inverse iteration: random reduced words (never a generator right after its inverse)
    applied to a start point; walkers run in parallel. Returns complex points."""
    a, b = grandma(complex(ta), complex(tb))
    gens = [a, b, _inv(a), _inv(b)]  # inverse of gens[i] is gens[(i + 2) % 4]
    rng = np.random.default_rng(seed)
    z = np.full(walkers, 0.1 + 0.05j)
    last = rng.integers(0, 4, walkers)
    out = []
    steps = max(1, points // walkers) + 30
    for t in range(steps):
        ch = rng.integers(0, 3, walkers)
        g = (last + 3 + ch) % 4  # one of the three letters that do not cancel `last`
        G = np.array(gens)[g]
        z = (G[:, 0, 0] * z + G[:, 0, 1]) / (G[:, 1, 0] * z + G[:, 1, 1])
        last = g
        if t >= 30:
            out.append(z.copy())
    return np.concatenate(out)


def points_mask(pts, size, centre=0j, width=2.5):
    pts = pts[np.isfinite(pts)]
    sc = (size - 1) / width
    u = np.round((pts.real - centre.real + width / 2) * sc).astype(int)
    v = np.round((centre.imag + width / 2 - pts.imag) * sc).astype(int)
    ok = (u >= 0) & (u < size) & (v >= 0) & (v < size)
    m = np.zeros((size, size), bool)
    m[v[ok], u[ok]] = True
    return m


def cmd_kleinian(a):
    if a.kind == "apollonian":
        circ = apollonian_circles(min_r=a.min_r if a.min_r else 0.5 / a.size)
        m = circles_mask(circ, a.size)
        p = {"kind": "apollonian", "size": a.size, "min_r": a.min_r or 0.5 / a.size, "circles": len(circ)}
    else:
        pts = limit_points(complex(a.ta), complex(a.tb), a.points, a.seed)
        m = points_mask(pts, a.size, width=a.width)
        p = {"kind": "grandma", "ta": a.ta, "tb": a.tb, "points": a.points, "size": a.size, "width": a.width}
    _fw().write_png(a.out, arr=np.where(m, 27, 255).astype(np.uint8))
    rec = _recipe("kleinian", a.kind, p, a.seed)
    print(f"wrote {a.out} and {_write_recipe(a.out, rec)}")
    return 0


REF = "references/12-neighbours.md"
EXPLAIN_NB = {
    "rd": ("A' = A + (DA lap A - AB^2 + f(1-A)) dt, B' = B + (DB lap B + AB^2 - (k+f)B) dt",
           "Gray-Scott reaction-diffusion, DA 1, DB 0.5, dt 1, Sims' 3x3 Laplacian. Not a fractal: one "
           "characteristic length. `fw.py rd coral|mitosis|default`.", REF + "#reaction-diffusion"),
    "ca": ("cell(t+1, x) = rule bit of (left, self, right); Life-like B/S counts of 8 neighbours",
           "Elementary rule 0-255 (Rule 90 from one cell draws the Sierpinski triangle, D = log3/log2) or a "
           "Life-like rule on a torus. `fw.py ca 90`, `fw.py ca B3/S23`.", REF + "#cellular-automata"),
    "tiling": ("Robinson triangle substitution, scale 1/phi per step",
               "Regular (square, triangle, hex) and Penrose P3 rhombs. Not fractal: box counting drifts from "
               "slope 1 (edges) to 2 (plane). `fw.py tiling penrose`.", REF + "#tilings"),
    "kleinian": ("k' = 2(k1+k2+k3) - k4 (Descartes); z -> (az+b)/(cz+d) words in a, b, A, B",
                 "Apollonian gasket by Descartes reflection (D ~ 1.3057) or a two-generator group from "
                 "Grandma's recipe by inverse iteration. `fw.py kleinian apollonian|grandma`.", REF + "#kleinian"),
}


def register(sub, explain):
    explain.update(EXPLAIN_NB)
    s = sub.add_parser("rd", help="Gray-Scott reaction-diffusion -> PNG + recipe")
    s.add_argument("preset", help=f"{', '.join(RD_PRESETS)} or recipe.json")
    s.add_argument("-o", "--out", default="rd.png")
    s.add_argument("--size", default="256x256")
    s.add_argument("--steps", type=int, default=5000)
    s.add_argument("--f", type=float)
    s.add_argument("--k", type=float)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cmd_rd)
    s = sub.add_parser("ca", help="cellular automaton: elementary rule 0-255 or Life-like B/S rule")
    s.add_argument("rule", help="e.g. 90, 30, B3/S23, B36/S23")
    s.add_argument("-o", "--out", default="ca.png")
    s.add_argument("--steps", type=int, default=255)
    s.add_argument("--width", type=int, help="elementary: cells per row (default 2*steps+1)")
    s.add_argument("--init", choices=["single", "random"], default="single")
    s.add_argument("--size", default="200x200", help="Life-like grid")
    s.add_argument("--density", type=float, default=0.3)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cmd_ca)
    s = sub.add_parser("tiling", help="regular or Penrose P3 tiling edges -> PNG + recipe")
    s.add_argument("kind", choices=["square", "triangle", "hex", "penrose"])
    s.add_argument("-o", "--out", default="tiling.png")
    s.add_argument("--n", type=int, help="tiles across (regular) or substitution steps (penrose)")
    s.add_argument("--size", default="800x800")
    s.set_defaults(fn=cmd_tiling)
    s = sub.add_parser("kleinian", help="Kleinian limit set: Apollonian gasket or Grandma's two-generator recipe")
    s.add_argument("kind", choices=["apollonian", "grandma"])
    s.add_argument("-o", "--out", default="kleinian.png")
    s.add_argument("--size", type=int, default=1024)
    s.add_argument("--min-r", type=float, help="apollonian: smallest radius (default half a pixel)")
    s.add_argument("--ta", default="2", help="grandma: trace of a (complex, e.g. 1.87+0.1j)")
    s.add_argument("--tb", default="2")
    s.add_argument("--points", type=int, default=400_000)
    s.add_argument("--width", type=float, default=2.5)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cmd_kleinian)
