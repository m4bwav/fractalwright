"""fractalwright deep zoom: perturbation rendering for the Mandelbrot set and quadratic Julia sets.

One reference orbit at the view centre in arbitrary precision (stdlib
`decimal`; mpmath is not needed), then every pixel iterates only its float64
offset from that orbit:

    dz' = 2 Z[m] dz + dz^2 + dc,   z = Z[m+1] + dz

Julia (z^2 + c, c fixed): the reference orbit starts at Z[0] = view centre, every
pixel's dz starts at its offset from the centre, and dc = 0.

Glitches are handled by rebasing (Zhuoran 2021, references/03 section 2.3):
when |z - Z[0]| < |dz|, or the reference orbit runs out, the pixel restarts
against the same reference from iteration 0 with dz = z - Z[0] (Z[0] = 0 for
Mandelbrot, so this is the published |z| < |dz| test). The counter reports how many
pixels were rebased. float64 deltas hold down to widths near 1e-290; past
that a floatexp delta would be needed (not built).

Smooth colouring and palettes come from fw.py, so a deep render matches the
plain path pixel for pixel where float64 is exact.
"""
import math
from decimal import Decimal, localcontext

import numpy as np

DEEP_WIDTH = Decimal("1e-12")  # fw.py render routes here below this width
MIN_WIDTH = Decimal("1e-290")
FORMULAS = ("mandelbrot", "julia")


def _prec(width):
    w = Decimal(width)
    return max(30, -w.adjusted() + 25)


def reference_orbit(cx, cy, max_iter, bailout2, prec, z0=None):
    """Decimal orbit z <- z^2 + c with c = (cx, cy), rounded to float64. Returns (Zr, Zi);
    Z[0] = z0 (default 0, Mandelbrot), ends at max_iter or one step past escape."""
    with localcontext() as ctx:
        ctx.prec = prec
        cr, ci = Decimal(cx), Decimal(cy)
        zr, zi = (Decimal(0), Decimal(0)) if z0 is None else (Decimal(z0[0]), Decimal(z0[1]))
        out_r, out_i = [float(zr)], [float(zi)]
        big = Decimal(1e10)
        for _ in range(max_iter):
            zr, zi = zr * zr - zi * zi + cr, 2 * zr * zi + ci
            fr, fi = float(zr), float(zi)
            out_r.append(fr)
            out_i.append(fi)
            if fr * fr + fi * fi > bailout2 or abs(zr) > big:
                break
    return np.array(out_r), np.array(out_i)


def _offsets(r):
    w, h = r["size"]["w"], r["size"]["h"]
    ss = int(r["size"].get("supersample", 1) or 1)
    W, H = w * ss, h * ss
    px = float(Decimal(r["view"]["width"]) / W)
    dx = (np.arange(W) + 0.5 - W / 2) * px
    dy = (H / 2 - (np.arange(H) + 0.5)) * px
    DX, DY = np.meshgrid(dx, dy)
    rot = math.radians(float(r["view"].get("rotation_deg", 0) or 0))
    if rot:
        DX, DY = DX * math.cos(rot) - DY * math.sin(rot), DX * math.sin(rot) + DY * math.cos(rot)
    return DX, DY, ss


def series_skip(Zr, Zi, dcmax, probes, tol=1e-9, check=1e-6, R2=65536.0):
    """Series approximation (Martin 2013; references/03 section 2.5): dz_n ~= A dc + B dc^2 + C dc^3 with
    A' = 2ZA + 1, B' = 2ZB + A^2, C' = 2ZC + 2AB from 0. Picks the last n where the cubic term stays under
    tol of the linear one at the corner |dc|, then verifies against plain perturbation at the probe offsets
    (complex dc) and halves n until every probe agrees within `check` (relative) and none has escaped.
    Returns (n, A, B, C) at n; n = 0 means no skip."""
    Z = Zr + 1j * Zi
    A = B = C = 0j
    coef = [(0j, 0j, 0j)]
    for k in range(len(Z) - 1):
        A, B, C = 2 * Z[k] * A + 1, 2 * Z[k] * B + A * A, 2 * Z[k] * C + 2 * A * B
        if not (abs(C) * dcmax ** 3 < tol * abs(A) * dcmax) or not np.isfinite(abs(C)):
            break
        coef.append((A, B, C))
    n = len(coef) - 1
    probes = np.asarray(probes, complex)
    while n > 0:
        dz = np.zeros_like(probes)
        ok = True
        for k in range(n):
            dz = 2 * Z[k] * dz + dz * dz + probes
            if (np.abs(Z[k + 1] + dz) ** 2 > R2).any():
                ok = False
                break
        if ok:
            a, b, c = coef[n]
            sa = a * probes + b * probes ** 2 + c * probes ** 3
            if (np.abs(sa - dz) <= check * np.maximum(np.abs(dz), 1e-300)).all():
                return (n,) + coef[n]
        n //= 2
    return 0, 0j, 0j, 0j


def escape_perturb(r, stats=None):
    """(nu, inside) like fw.escape_numpy, by perturbation. Mandelbrot and quadratic Julia."""
    if r["formula"] not in FORMULAS:
        raise ValueError(f"deep path supports {', '.join(FORMULAS)} only")
    julia = r["formula"] == "julia"
    width = Decimal(r["view"]["width"])
    if width < MIN_WIDTH:
        raise ValueError(f"width {width} is below float64 delta range ({MIN_WIDTH}); floatexp not built")
    p = r["params"]
    maxit, R2 = int(p["max_iter"]), float(p["bailout"]) ** 2
    cx, cy = r["view"]["centre"]
    if julia:
        Zr, Zi = reference_orbit(p["c"][0], p["c"][1], maxit, R2, _prec(width), z0=(cx, cy))
    else:
        Zr, Zi = reference_orbit(cx, cy, maxit, R2, _prec(width))
    Z0r, Z0i = Zr[0], Zi[0]
    last = len(Zr) - 1
    DX, DY, _ = _offsets(r)
    shape = DX.shape
    N = DX.size
    if julia:
        dzr, dzi = DX.ravel().copy(), DY.ravel().copy()
        dcr, dci = np.zeros(N), np.zeros(N)
    else:
        dcr, dci = DX.ravel().copy(), DY.ravel().copy()
        dzr, dzi = np.zeros(N), np.zeros(N)
    m = np.zeros(N, np.int64)
    skip = 0
    if p.get("series") and not julia:
        corners = np.array([complex(DX.flat[i], DY.flat[i]) for i in (0, shape[1] - 1, N - shape[1], N - 1)])
        probes = np.concatenate([corners, corners / 2, [complex(DX.flat[N // 2], DY.flat[N // 2])]])
        skip, sA, sB, sC = series_skip(Zr, Zi, float(np.abs(corners).max()), probes, R2=R2)
        if skip:
            dc = dcr + 1j * dci
            dz = sA * dc + sB * dc * dc + sC * dc ** 3
            dzr, dzi = dz.real.copy(), dz.imag.copy()
            m[:] = skip
    idx = np.arange(N)
    n_out = np.full(N, -1, np.int64)
    m_out = np.zeros(N)
    rebased = np.zeros(N, bool)
    rebases = 0
    for n in range(skip, maxit):
        Zmr, Zmi = Zr[m], Zi[m]
        dzr, dzi = (2 * (Zmr * dzr - Zmi * dzi) + dzr * dzr - dzi * dzi + dcr,
                    2 * (Zmr * dzi + Zmi * dzr) + 2 * dzr * dzi + dci)
        m += 1
        zr, zi = Zr[m] + dzr, Zi[m] + dzi
        mag = zr * zr + zi * zi
        esc = mag > R2
        if esc.any():
            n_out[idx[esc]] = n + 1
            m_out[idx[esc]] = mag[esc]
            keep = ~esc
            dzr, dzi, dcr, dci, m, idx, zr, zi, mag = (a[keep] for a in (dzr, dzi, dcr, dci, m, idx, zr, zi, mag))
            if idx.size == 0:
                break
        rb = ((zr - Z0r) ** 2 + (zi - Z0i) ** 2 < dzr * dzr + dzi * dzi) | (m >= last)
        if rb.any():
            rebases += int(rb.sum())
            rebased[idx[rb]] = True
            dzr[rb], dzi[rb], m[rb] = zr[rb] - Z0r, zi[rb] - Z0i, 0
    inside = n_out < 0
    nu = np.zeros(N)
    e = ~inside
    nu[e] = n_out[e] + 1 - np.log(np.log(m_out[e]) / 2) / math.log(2)
    if stats is not None:
        stats.update(rebased_pixels=int(rebased.sum()), rebases=rebases,
                     ref_len=last, prec_digits=_prec(width), series_skip=skip)
    return nu.reshape(shape), inside.reshape(shape), n_out.reshape(shape)


def render_array(r, stats=None):
    """Recipe -> uint8 HxWx3 by perturbation (same colouring as fw.render_array)."""
    import fw
    r = fw.normalise(r)
    nu, inside, _ = escape_perturb(r, stats)
    rgb = fw.colour(r, nu, inside)
    ss = int(r["size"].get("supersample", 1) or 1)
    if ss > 1:
        h, w = r["size"]["h"], r["size"]["w"]
        rgb = rgb.reshape(h, ss, w, ss, 3).mean(axis=(1, 3))
    return np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)


def direct_counts(r, prec=None):
    """Slow proof reference: per-pixel Decimal iteration. Returns int counts (-1 inside).
    Mandelbrot (z0 = 0, c = pixel) or Julia (z0 = pixel, c = params.c)."""
    w, h = r["size"]["w"], r["size"]["h"]
    width = Decimal(r["view"]["width"])
    prec = prec or _prec(width)
    maxit, R2 = int(r["params"]["max_iter"]), Decimal(r["params"]["bailout"]) ** 2
    out = np.full((h, w), -1, np.int64)
    with localcontext() as ctx:
        ctx.prec = prec
        cx, cy = Decimal(r["view"]["centre"][0]), Decimal(r["view"]["centre"][1])
        px = width / w
        julia = r["formula"] == "julia"
        if julia:
            kr, ki = Decimal(r["params"]["c"][0]), Decimal(r["params"]["c"][1])
        for j in range(h):
            ci = cy + (Decimal(h) / 2 - (j + Decimal("0.5"))) * px
            for i in range(w):
                cr = cx + (i + Decimal("0.5") - Decimal(w) / 2) * px
                zr = zi = Decimal(0)
                if julia:
                    zr, zi, cr, ci_ = cr, ci, kr, ki
                else:
                    ci_ = ci
                for n in range(maxit):
                    zr2, zi2 = zr * zr, zi * zi
                    if n and zr2 + zi2 > R2:
                        out[j, i] = n
                        break
                    zr, zi = zr2 - zi2 + cr, 2 * zr * zi + ci_
                else:
                    if zr * zr + zi * zi > R2:
                        out[j, i] = maxit
    return out
