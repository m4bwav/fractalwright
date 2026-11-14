"""fractalwright deep zoom: perturbation rendering for the Mandelbrot set.

One reference orbit at the view centre in arbitrary precision (stdlib
`decimal`; mpmath is not needed), then every pixel iterates only its float64
offset from that orbit:

    dz' = 2 Z[m] dz + dz^2 + dc,   z = Z[m+1] + dz

Glitches are handled by rebasing (Zhuoran 2021, references/03 section 2.3):
when |z| < |dz|, or the reference orbit runs out, the pixel restarts against
the same reference from iteration 0 with dz = z. The counter reports how many
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


def _prec(width):
    w = Decimal(width)
    return max(30, -w.adjusted() + 25)


def reference_orbit(cx, cy, max_iter, bailout2, prec):
    """Decimal orbit of the centre, rounded to float64. Returns (Zr, Zi);
    Z[0] = 0, ends at max_iter or one step past escape."""
    with localcontext() as ctx:
        ctx.prec = prec
        cr, ci = Decimal(cx), Decimal(cy)
        zr = zi = Decimal(0)
        out_r, out_i = [0.0], [0.0]
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


def escape_perturb(r, stats=None):
    """(nu, inside) like fw.escape_numpy, by perturbation. Mandelbrot only."""
    if r["formula"] != "mandelbrot":
        raise ValueError("deep path supports formula 'mandelbrot' only")
    width = Decimal(r["view"]["width"])
    if width < MIN_WIDTH:
        raise ValueError(f"width {width} is below float64 delta range ({MIN_WIDTH}); floatexp not built")
    p = r["params"]
    maxit, R2 = int(p["max_iter"]), float(p["bailout"]) ** 2
    cx, cy = r["view"]["centre"]
    Zr, Zi = reference_orbit(cx, cy, maxit, R2, _prec(width))
    last = len(Zr) - 1
    DX, DY, _ = _offsets(r)
    shape = DX.shape
    dcr, dci = DX.ravel().copy(), DY.ravel().copy()
    N = dcr.size
    dzr, dzi = np.zeros(N), np.zeros(N)
    m = np.zeros(N, np.int64)
    idx = np.arange(N)
    n_out = np.full(N, -1, np.int64)
    m_out = np.zeros(N)
    rebased = np.zeros(N, bool)
    rebases = 0
    for n in range(maxit):
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
        rb = (mag < dzr * dzr + dzi * dzi) | (m >= last)
        if rb.any():
            rebases += int(rb.sum())
            rebased[idx[rb]] = True
            dzr[rb], dzi[rb], m[rb] = zr[rb], zi[rb], 0
    inside = n_out < 0
    nu = np.zeros(N)
    e = ~inside
    nu[e] = n_out[e] + 1 - np.log(np.log(m_out[e]) / 2) / math.log(2)
    if stats is not None:
        stats.update(rebased_pixels=int(rebased.sum()), rebases=rebases,
                     ref_len=last, prec_digits=_prec(width))
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
    """Slow proof reference: per-pixel Decimal iteration. Returns int counts (-1 inside)."""
    w, h = r["size"]["w"], r["size"]["h"]
    width = Decimal(r["view"]["width"])
    prec = prec or _prec(width)
    maxit, R2 = int(r["params"]["max_iter"]), Decimal(r["params"]["bailout"]) ** 2
    out = np.full((h, w), -1, np.int64)
    with localcontext() as ctx:
        ctx.prec = prec
        cx, cy = Decimal(r["view"]["centre"][0]), Decimal(r["view"]["centre"][1])
        px = width / w
        for j in range(h):
            ci = cy + (Decimal(h) / 2 - (j + Decimal("0.5"))) * px
            for i in range(w):
                cr = cx + (i + Decimal("0.5") - Decimal(w) / 2) * px
                zr = zi = Decimal(0)
                for n in range(maxit):
                    zr2, zi2 = zr * zr, zi * zi
                    if n and zr2 + zi2 > R2:
                        out[j, i] = n
                        break
                    zr, zi = zr2 - zi2 + cr, 2 * zr * zi + ci
                else:
                    if zr * zr + zi * zi > R2:
                        out[j, i] = maxit
    return out
