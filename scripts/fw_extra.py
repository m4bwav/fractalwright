"""fw_extra: book-derived tools for fw.py (logistic map, attractor search, IFS, terrain, fractal interpolation).

Registered by fw.py main() through register(). Mariani-Silver, grey-level IFS and the multi-scroll attractor
were tried and left out (ai-docs/log.md, 2026-11-14 books batch).
Sources and proof bars: CHANGELOG C-20261114-7, TESTS T-20261114-7.
"""
import math
import sys

import numpy as np


def _fw():
    m = sys.modules.get("fw")
    if m is None or not hasattr(m, "write_png"):
        m = sys.modules.get("__main__")
    if m is None or not hasattr(m, "write_png"):
        import fw as m  # noqa: F811
    return m


# ---------------------------------------------------------------- explain additions
EXPLAIN_EXTRA = {
    "logistic": ("x <- r x (1 - x), x in [0, 1], r in [0, 4]",
                 "Start here. Teaching order: iterate a 1D map by hand, draw the cobweb, find fixed points and their "
                 "stability, then period doubling on the bifurcation diagram, then sensitive dependence and the "
                 "Lyapunov exponent (r = 4 gives 1 bit per iteration = ln 2 nats), then 2D maps and attractors, "
                 "then escape-time sets. Plots: explain logistic --plot cobweb|bifurcation -o out.png. Shadowing: a "
                 "float orbit of a chaotic map leaves the true orbit within ~50 steps, yet stays close to some true "
                 "orbit, so pictures and statistics are right even when single orbits are not.",
                 "references/05-lsystems-attractors.md#4-strange-attractors-equations-and-known-good-parameters"),
    "coastline": ("L(e) ~ e^(1 - D): measured length grows as the ruler e shrinks",
                  "Richardson measured frontiers and coasts with shorter and shorter rulers and found length keeps "
                  "growing on a log-log line; Mandelbrot (1967) read the slope as 1 - D. Length is finite only in "
                  "dimension D, so a coast has no single length. fw.py measure box gives D with its fit range.",
                  "references/01-history.md#timeline"),
}


# ---------------------------------------------------------------- logistic map
def logistic_attractor(r, n_keep=256, warm=2000, x0=0.5):
    x = x0
    for _ in range(warm):
        x = r * x * (1 - x)
    out = np.empty(n_keep)
    for i in range(n_keep):
        x = r * x * (1 - x)
        out[i] = x
    return out


def logistic_branches(r, tol=1e-6):
    v = np.sort(logistic_attractor(r))
    return int(1 + np.count_nonzero(np.diff(v) > tol))


def logistic_lyapunov(r, n=100000, warm=1000, x0=0.3, bits=True):
    """Mean log|f'(x)| along the orbit; bits per iteration by default (nats with bits=False)."""
    x = x0
    for _ in range(warm):
        x = r * x * (1 - x)
    s = 0.0
    for _ in range(n):
        x = r * x * (1 - x)
        s += math.log(abs(r * (1 - 2 * x)) + 1e-300)
    lam = s / n
    return lam / math.log(2) if bits else lam


def _canvas(w, h):
    return np.full((h, w, 3), 255, np.uint8)


def _line(img, x0, y0, x1, y1, col):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    xs = np.clip(np.round(np.linspace(x0, x1, n)).astype(int), 0, img.shape[1] - 1)
    ys = np.clip(np.round(np.linspace(y0, y1, n)).astype(int), 0, img.shape[0] - 1)
    img[ys, xs] = col


def cobweb_png(r, path, size=512, x0=0.1, steps=60):
    img = _canvas(size, size)
    s = size - 1
    P = lambda x, y: (x * s, (1 - y) * s)  # noqa: E731
    _line(img, *P(0, 0), *P(1, 1), (160, 160, 160))
    xs = np.linspace(0, 1, size * 2)
    ys = r * xs * (1 - xs)
    for i in range(xs.size - 1):
        _line(img, *P(xs[i], ys[i]), *P(xs[i + 1], ys[i + 1]), (30, 60, 200))
    x = x0
    for _ in range(steps):
        y = r * x * (1 - x)
        _line(img, *P(x, x), *P(x, y), (200, 40, 40))
        _line(img, *P(x, y), *P(y, y), (200, 40, 40))
        x = y
    return _fw().write_png(path, arr=img)


def bifurcation_png(path, w=800, h=500, rmin=2.5, rmax=4.0, n_keep=200, warm=500):
    img = _canvas(w, h)
    r = np.linspace(rmin, rmax, w)
    x = np.full(w, 0.5)
    for _ in range(warm):
        x = r * x * (1 - x)
    cols = np.arange(w)
    for _ in range(n_keep):
        x = r * x * (1 - x)
        img[np.clip(((1 - x) * (h - 1)).astype(int), 0, h - 1), cols] = (20, 20, 20)
    return _fw().write_png(path, arr=img)


# ---------------------------------------------------------------- 2D maps, Lyapunov, D2, Sprott search
SPROTT_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXY"


def sprott_decode(code):
    """'E' + 12 letters (A..Y = -1.2..1.2): general 2D quadratic map coefficients."""
    code = code.strip().upper()
    if len(code) != 13 or code[0] != "E":
        raise ValueError("Sprott 2D quadratic codes are E plus 12 letters A..Y")
    return [round(-1.2 + 0.1 * SPROTT_LETTERS.index(ch), 1) for ch in code[1:]]


def sprott_encode(a):
    return "E" + "".join(SPROTT_LETTERS[int(round((v + 1.2) * 10))] for v in a)


def quad_step(a, x, y):
    return (a[0] + a[1] * x + a[2] * x * x + a[3] * x * y + a[4] * y + a[5] * y * y,
            a[6] + a[7] * x + a[8] * x * x + a[9] * x * y + a[10] * y + a[11] * y * y)


def henon_step(x, y, a=1.4, b=0.3):
    return 1 - a * x * x + y, b * x


def orbit_lyapunov(step, x=0.05, y=0.05, n=11000, warm=1000, d0=1e-6):
    """Largest Lyapunov exponent by the renormalised-neighbour method (Sprott). Returns (bits/iter, points)
    or (None, None) when the orbit is unbounded or settles on a fixed point."""
    xe, ye = x + d0, y
    pts = np.empty((n, 2))
    s = 0.0
    for i in range(n + warm):
        x1, y1 = step(x, y)
        if abs(x1) > 1e6 or abs(y1) > 1e6 or not math.isfinite(x1 + y1):
            return None, None
        if abs(x1 - x) + abs(y1 - y) < 1e-10:
            return None, None
        xe, ye = step(xe, ye)
        dx, dy = xe - x1, ye - y1
        d = math.hypot(dx, dy) or 1e-300
        if i >= warm:
            s += math.log(d / d0)
            pts[i - warm] = (x1, y1)
        xe, ye = x1 + d0 * dx / d, y1 + d0 * dy / d
        x, y = x1, y1
    return s / n / math.log(2), pts


def correlation_dimension(pts, n=2500, seed=0, lo=0.02, hi=0.25):
    """Grassberger-Procaccia D2 on a random subset; slope of log C(e) over e in [lo, hi] x the cloud's size."""
    rng = np.random.default_rng(seed)
    p = pts[rng.choice(len(pts), min(n, len(pts)), replace=False)]
    d = np.sqrt(((p[:, None, :] - p[None, :, :]) ** 2).sum(-1))[np.triu_indices(len(p), 1)]
    size = np.ptp(p, axis=0).max()
    eps = size * np.geomspace(lo, hi, 12)
    C = np.array([np.count_nonzero(d < e) for e in eps], float)
    ok = C > 0
    return float(np.polyfit(np.log(eps[ok]), np.log(C[ok]), 1)[0])


def preference_score(d2, lyap, window=(1.1, 1.5)):
    """Distance from Sprott's preferred window (D2 1.1-1.5, small positive L); lower is better. Book rule."""
    return max(0.0, window[0] - d2, d2 - window[1]) + 0.1 * max(0.0, lyap)


def attractor_search(hits=5, seed=0, n=11000, max_tries=20000):
    rng = np.random.default_rng(seed)
    found, tries = [], 0
    while len(found) < hits and tries < max_tries:
        tries += 1
        a = list(np.round(rng.integers(0, 25, 12) * 0.1 - 1.2, 1))
        lyap, pts = orbit_lyapunov(lambda x, y: quad_step(a, x, y), n=n)
        if lyap is None or lyap <= 0.005:
            continue
        d2 = correlation_dimension(pts)
        found.append({"code": sprott_encode(a), "lyapunov_bits": round(lyap, 4), "d2": round(d2, 3),
                      "score": round(preference_score(d2, lyap), 4)})
    found.sort(key=lambda h: h["score"])
    return found, tries


def points_png(pts, path, w=600, h=600, frame=None):
    if frame is None:
        lo, hi = pts.min(0), pts.max(0)
    else:
        lo, hi = np.array(frame[0], float), np.array(frame[1], float)
    span = (hi - lo).max() * 1.05 or 1.0
    c = (lo + hi) / 2
    u = ((pts[:, 0] - c[0]) / span + 0.5) * (w - 1)
    v = (0.5 - (pts[:, 1] - c[1]) / span) * (h - 1)
    ok = (u >= 0) & (u < w) & (v >= 0) & (v < h)
    hist = np.zeros((h, w))
    np.add.at(hist, (v[ok].astype(int), u[ok].astype(int)), 1)
    g = 255 - (255 * np.log1p(hist) / max(np.log1p(hist).max(), 1e-9)).astype(np.uint8)
    return _fw().write_png(path, arr=g.astype(np.uint8))


# ---------------------------------------------------------------- IFS: |det| probabilities, discard, ball cover
IFS_PRESETS = {
    # each map: [a, b, c, d, e, f] for (x, y) -> (a x + b y + e, c x + d y + f)
    "sierpinski": [[0.5, 0, 0, 0.5, 0, 0], [0.5, 0, 0, 0.5, 0.5, 0], [0.5, 0, 0, 0.5, 0.25, 0.433]],
    "fern": [[0, 0, 0, 0.16, 0, 0], [0.85, 0.04, -0.04, 0.85, 0, 1.6],
             [0.2, -0.26, 0.23, 0.22, 0, 1.6], [-0.15, 0.28, 0.26, 0.24, 0, 0.44]],
    # unit square cut into four unequal rectangles: |det| weights give a flat density
    "unequal-tiles": [[0.25, 0, 0, 0.5, 0, 0], [0.25, 0, 0, 0.5, 0, 0.5],
                      [0.75, 0, 0, 0.5, 0.25, 0], [0.75, 0, 0, 0.5, 0.25, 0.5]],
}


def ifs_probabilities(maps, floor=0.01):
    """p_i proportional to |det| of the linear part; zero-det maps get `floor` before normalising."""
    det = np.array([abs(m[0] * m[3] - m[1] * m[2]) for m in maps])
    det = np.maximum(det / det.sum() if det.sum() else np.ones(len(maps)), floor)
    return det / det.sum()


def chaos_game(maps, n=200000, probs=None, discard=20, seed=0, start=(0.0, 0.0)):
    M = np.array(maps, float)
    p = ifs_probabilities(maps) if probs is None else np.asarray(probs, float) / np.sum(probs)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(M), n + discard, p=p)
    out = np.empty((n + discard, 2))
    x, y = start
    for k, i in enumerate(idx):
        a, b, c, d, e, f = M[i]
        x, y = a * x + b * y + e, c * x + d * y + f
        out[k] = x, y
    return out[discard:]


def ifs_envelope(maps, iters=50):
    """Ball B(c, R) every map sends into itself: R = max |f_i(c) - c| / (1 - s_i), s_i the largest singular
    value. The attractor lies inside it (Canright-style a-priori framing). Centre refined by a few steps."""
    M = np.array(maps, float)
    s = np.array([np.linalg.svd(m[:4].reshape(2, 2), compute_uv=False)[0] for m in M])
    if (s >= 1).any():
        raise ValueError("a map is not contractive (largest singular value >= 1)")
    fixed = []
    for m in M:
        A = m[:4].reshape(2, 2)
        fixed.append(np.linalg.solve(np.eye(2) - A, m[4:]))
    c = np.mean(fixed, 0)

    def radius(c):
        return max(np.linalg.norm(m[:4].reshape(2, 2) @ c + m[4:] - c) / (1 - si) for m, si in zip(M, s))
    R = radius(c)
    step = R / 4
    for _ in range(iters):  # pattern search on the centre
        best = (R, c)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cc = c + step * np.array([dx, dy])
            rr = radius(cc)
            if rr < best[0]:
                best = (rr, cc)
        if best[0] < R:
            R, c = best
        else:
            step /= 2
    return c, float(R)


# ---------------------------------------------------------------- terrain: spectral vs midpoint
def diamond_square(k, H=0.8, seed=0):
    """(2^k + 1)^2 heightfield by diamond-square, amplitude x 2^-H per level (Fournier et al. 1982)."""
    rng = np.random.default_rng(seed)
    n = 2 ** k
    z = np.zeros((n + 1, n + 1))
    z[::n, ::n] = rng.normal(size=(2, 2))
    step, amp = n, 1.0
    while step > 1:
        h = step // 2
        amp *= 2 ** -H
        c = (z[0:-1:step, 0:-1:step] + z[step::step, 0:-1:step] + z[0:-1:step, step::step] + z[step::step, step::step]) / 4
        z[h::step, h::step] = c + amp * rng.normal(size=c.shape)
        for oy, ox in ((0, h), (h, 0)):
            ys, xs = np.mgrid[oy:n + 1:step, ox:n + 1:step]
            acc = np.zeros(ys.shape)
            cnt = np.zeros(ys.shape)
            for dy, dx in ((-h, 0), (h, 0), (0, -h), (0, h)):
                yy, xx = ys + dy, xs + dx
                ok = (yy >= 0) & (yy <= n) & (xx >= 0) & (xx <= n)
                acc[ok] += z[yy[ok], xx[ok]]
                cnt[ok] += 1
            z[ys, xs] = acc / cnt + amp * rng.normal(size=ys.shape)
        step = h
    return z


def crease_ratio(z, levels=3):
    """Mean |second difference across| the coarse grid lines (multiples of n/2^levels) over the mean
    elsewhere, rows and columns pooled. ~1 for an isotropic field; > 1 means creases."""
    n = z.shape[0] - 1 if z.shape[0] % 2 else z.shape[0]
    d2r = np.abs(z[:-2] - 2 * z[1:-1] + z[2:])          # across rows, at row i+1
    d2c = np.abs(z[:, :-2] - 2 * z[:, 1:-1] + z[:, 2:])
    lines = np.arange(1, 2 ** levels) * (n // 2 ** levels)
    on = np.zeros(d2r.shape[0], bool)
    on[lines - 1] = True
    num = d2r[on].mean() + d2c[:, on].mean()
    den = d2r[~on].mean() + d2c[:, ~on].mean()
    return float(num / den)


def terrain(method="spectral", k=9, H=0.8, seed=0):
    fw = _fw()
    if method == "midpoint":
        return diamond_square(k, H, seed)
    return fw.synth_fbm2d(2 ** k, H, seed)


# ---------------------------------------------------------------- fractal interpolation (affine FIF)
def fif(points, d, depth=None, n=4097):
    """Affine fractal interpolation function through points (x_i, y_i) with vertical scalings d_i (|d_i| < 1).
    Returns (x, y) on a grid that the maps send onto itself when the points are equally spaced."""
    P = np.asarray(points, float)
    d = np.asarray(d, float)
    N = len(P) - 1
    if d.size != N or (np.abs(d) >= 1).any():
        raise ValueError("need one scaling per interval, each |d| < 1")
    x0, xN, y0, yN = P[0, 0], P[-1, 0], P[0, 1], P[-1, 1]
    L = xN - x0
    a = (P[1:, 0] - P[:-1, 0]) / L
    e = (xN * P[:-1, 0] - x0 * P[1:, 0]) / L
    c = (P[1:, 1] - P[:-1, 1] - d * (yN - y0)) / L
    f = (xN * P[:-1, 1] - x0 * P[1:, 1] - d * (xN * y0 - x0 * yN)) / L
    if depth is None:
        depth = max(1, int(round(math.log(n - 1) / math.log(N))))
    m = N ** depth + 1
    x = np.linspace(x0, xN, m)
    y = np.interp(x, P[:, 0], P[:, 1])
    for _ in range(200):
        y_new = np.empty_like(y)
        for i in range(N):
            sel = (x >= P[i, 0]) & (x <= P[i + 1, 0])
            u = (x[sel] - e[i]) / a[i]
            y_new[sel] = c[i] * u + d[i] * np.interp(u, x, y) + f[i]
        if np.max(np.abs(y_new - y)) < 1e-13:
            y = y_new
            break
        y = y_new
    return x, y


def fif_dimension(d):
    """Box dimension of an equally spaced affine FIF graph: 1 + log(sum|d|)/log N when sum|d| > 1, else 1."""
    s = float(np.sum(np.abs(d)))
    return 1 + math.log(s) / math.log(len(d)) if s > 1 else 1.0


# ---------------------------------------------------------------- commands
def cmd_explain_ext(a, orig):
    if getattr(a, "plot", None):
        if a.family.lower() != "logistic":
            print("--plot works with explain logistic", file=sys.stderr)
            return 2
        out = a.out or f"{a.plot}.png"
        if a.plot == "cobweb":
            cobweb_png(a.r, out)
        else:
            bifurcation_png(out)
        print(f"wrote {out}")
    return orig(a)


def cmd_attractor_search(a):
    hits, tries = attractor_search(a.hits, a.seed, a.iters)
    print(f"{len(hits)} attractors in {tries} tries (ranked by distance from D2 1.1-1.5, small L; book rule)")
    for h in hits:
        print(f"  {h['code']}  L {h['lyapunov_bits']} bits/iter  D2 {h['d2']}  score {h['score']}")
    if a.out and hits:
        coef = sprott_decode(hits[0]["code"])
        _, pts = orbit_lyapunov(lambda x, y: quad_step(coef, x, y), n=200000)
        points_png(pts, a.out)
        print(f"wrote {a.out} ({hits[0]['code']})")
    return 0


def cmd_ifs(a):
    maps = IFS_PRESETS[a.preset]
    probs = None if a.probs == "det" else [1.0] * len(maps)
    pts = chaos_game(maps, a.points, probs, a.discard, a.seed)
    c, R = ifs_envelope(maps)
    print(f"{a.preset}: p = {np.round(ifs_probabilities(maps) if probs is None else np.array(probs) / len(maps), 3).tolist()}"
          f", envelope centre ({c[0]:.4f}, {c[1]:.4f}) radius {R:.4f}")
    if a.out:
        frame = ((c[0] - R, c[1] - R), (c[0] + R, c[1] + R)) if a.frame == "envelope" else None
        points_png(pts, a.out, frame=frame)
        print(f"wrote {a.out}")
    return 0


def cmd_terrain(a):
    z = terrain(a.method, a.k, a.H, a.seed)
    g = ((z - z.min()) / (np.ptp(z) or 1) * 255).astype(np.uint8)
    _fw().write_png(a.out, arr=g)
    np.save(str(a.out).rsplit(".", 1)[0] + ".npy", z)
    print(f"wrote {a.out} ({a.method}, {z.shape[1]}x{z.shape[0]}, H {a.H}, crease ratio {crease_ratio(z):.3f})")
    return 0


def cmd_fif(a):
    pts = [tuple(float(v) for v in p.split(",")) for p in a.points.split(";")]
    d = [float(v) for v in a.d.split(",")]
    x, y = fif(pts, d)
    print(f"FIF through {len(pts)} points, sum|d| {sum(abs(v) for v in d):.3f}, graph dimension {fif_dimension(d):.4f}")
    if a.numbers:
        np.savetxt(a.numbers, y)
        print(f"wrote {a.numbers} (feed it to measure profile)")
    if a.out:
        points_png(np.column_stack([x, y]), a.out, 800, 400)
        print(f"wrote {a.out}")
    return 0


def register(sub, explain):
    """Called from fw.py main(): add explain entries and the book-derived commands."""
    explain.update(EXPLAIN_EXTRA)
    ex = sub.choices["explain"]
    ex.add_argument("--plot", choices=["cobweb", "bifurcation"], help="logistic: draw a PNG")
    ex.add_argument("--r", type=float, default=3.7, help="logistic r for the cobweb")
    ex.add_argument("-o", "--out")
    orig = ex.get_default("fn")
    ex.set_defaults(fn=lambda a: cmd_explain_ext(a, orig))
    s = sub.add_parser("attractor-search", help="Sprott quadratic-map search ranked by D2 1.1-1.5 and small L")
    s.add_argument("--hits", type=int, default=5)
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--iters", type=int, default=11000)
    s.add_argument("-o", "--out", help="PNG of the best hit")
    s.set_defaults(fn=cmd_attractor_search)
    s = sub.add_parser("ifs", help="chaos-game IFS preset (|det| probabilities, discard, envelope frame)")
    s.add_argument("preset", choices=list(IFS_PRESETS))
    s.add_argument("-o", "--out")
    s.add_argument("--probs", choices=["det", "equal"], default="det")
    s.add_argument("--discard", type=int, default=20)
    s.add_argument("--points", type=int, default=300000)
    s.add_argument("--frame", choices=["envelope", "points"], default="envelope")
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cmd_ifs)
    s = sub.add_parser("terrain", help="fBm heightfield: spectral (default) or midpoint (diamond-square)")
    s.add_argument("-o", "--out", default="terrain.png")
    s.add_argument("--method", choices=["spectral", "midpoint"], default="spectral")
    s.add_argument("--k", type=int, default=9, help="side 2^k")
    s.add_argument("--H", type=float, default=0.8)
    s.add_argument("--seed", type=int, default=0)
    s.set_defaults(fn=cmd_terrain)
    s = sub.add_parser("fif", help="fractal interpolation curve through points (vertical scalings d)")
    s.add_argument("--points", required=True, help="x,y;x,y;...")
    s.add_argument("--d", required=True, help="one scaling per interval, |d| < 1")
    s.add_argument("-o", "--out")
    s.add_argument("--numbers", help="write the y samples (one per line)")
    s.set_defaults(fn=cmd_fif)
