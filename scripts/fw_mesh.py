"""fractalwright 3D to printable mesh: `fw.py 3d mesh <formula|recipe.json> -o out.stl`.

Samples the same distance estimators as scripts/page/fractal3d.frag (ported to NumPy) on a grid, keeps
the one connected solid that holds the deepest interior point, pads the grid so the surface closes, and
extracts the iso surface DE = iso (half a voxel by default, which thickens hair-thin parts). Marching cubes
comes from scikit-image when it is installed; otherwise a NumPy marching-tetrahedra pass (Kuhn split, six
tetrahedra per cube) runs, which needs nothing else and welds vertices by grid edge, so the result is
watertight by construction. Output: binary STL in millimetres (longest side --size-mm), outward normals.
"""
import itertools
import json
import struct
import time
from pathlib import Path

import numpy as np

# half-extent of the sampled cube per formula (the set fits inside with a margin)
BOUNDS = {"mandelbulb": 1.25, "mandelbox": 6.2, "quatjulia": 1.6, "menger": 1.04, "hybrid": 1.3}
MESH_ITER = {"menger": 3}
MESH_RES = {"menger": 136}  # keeps Menger under polywright's 1M-triangle FDM budget; others 200  # level-3 holes are 1/81 of the size: 0.7 mm at 60 mm; level 4 would not print


def de(formula, P, prm):
    """Distance estimate for points P (..., 3), ported from fractal3d.frag."""
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    it = int(prm.get("iter", 10))
    if formula in ("mandelbulb", "hybrid"):
        s = float(prm.get("scale", 2.5)) if formula == "hybrid" else 1.0
        c = P * s
        zz = c.copy(); dr = np.ones(x.shape); alive = np.ones(x.shape, bool)
        pw = float(prm.get("power", 8.0))
        for _ in range(it):
            if formula == "hybrid":
                zz = np.where(alive[..., None], np.clip(zz, -1, 1) * 2 - zz, zz)
            r = np.linalg.norm(zz, axis=-1)
            alive &= r <= 2.0
            if not alive.any():
                break
            rs = np.maximum(r, 1e-12)
            th = np.arccos(np.clip(zz[..., 2] / rs, -1, 1)) * pw
            ph = np.arctan2(zz[..., 1], zz[..., 0]) * pw
            dr = np.where(alive, pw * rs ** (pw - 1) * dr + 1, dr)
            rp = rs ** pw
            nz = np.stack([rp * np.sin(th) * np.cos(ph), rp * np.sin(th) * np.sin(ph), rp * np.cos(th)], -1) + c
            zz = np.where(alive[..., None], nz, zz)
        r = np.linalg.norm(zz, axis=-1)
        return 0.5 * np.log(np.maximum(r, 1e-6)) * r / dr / s
    if formula == "mandelbox":
        sc = float(prm.get("scale", 2.0))
        zz = P.copy(); dr = np.ones(x.shape); alive = np.ones(x.shape, bool)
        for _ in range(it):
            nz = np.clip(zz, -1, 1) * 2 - zz
            r2 = (nz ** 2).sum(-1)
            f = np.where(r2 < 0.25, 4.0, np.where(r2 < 1.0, 1 / np.maximum(r2, 1e-12), 1.0))
            nz = nz * f[..., None] * sc + P
            ndr = dr * f * abs(sc) + 1
            zz = np.where(alive[..., None], nz, zz); dr = np.where(alive, ndr, dr)
            alive &= (zz ** 2).sum(-1) <= 1e4
        return np.linalg.norm(zz, axis=-1) / np.abs(dr)
    if formula == "quatjulia":
        jc = np.array(prm.get("c", [-0.2, 0.6, 0.2, 0.0]), float)
        q = np.concatenate([P, np.zeros(x.shape + (1,))], -1); dq = np.ones(x.shape); alive = np.ones(x.shape, bool)
        for _ in range(it):
            n = np.linalg.norm(q, axis=-1)
            a, v = q[..., :1], q[..., 1:]
            nq = np.concatenate([a * a - (v * v).sum(-1, keepdims=True), 2 * a * v], -1) + jc
            dq = np.where(alive, 2 * n * dq, dq); q = np.where(alive[..., None], nq, q)
            alive &= (q ** 2).sum(-1) <= 256
        r = np.linalg.norm(q, axis=-1)
        return 0.5 * r * np.log(np.maximum(r, 1e-6)) / dq
    if formula == "menger":
        qb = np.abs(P) - 1.0
        d = np.linalg.norm(np.maximum(qb, 0), axis=-1) + np.minimum(qb.max(-1), 0)
        cell = 2.0
        for _ in range(it):
            a = np.abs(np.mod(P + 1.0, cell) - 0.5 * cell)
            h = cell / 6.0
            hole = np.minimum(np.maximum(a[..., 1], a[..., 2]),
                              np.minimum(np.maximum(a[..., 0], a[..., 2]), np.maximum(a[..., 0], a[..., 1]))) - h
            d = np.maximum(d, -hole)
            cell /= 3.0
        return d
    raise SystemExit(f"3d mesh: unknown formula {formula}")


def sample(formula, prm, res, bound):
    ax = np.linspace(-bound, bound, res)
    F = np.empty((res, res, res))
    for i in range(res):  # slab by slab keeps memory at res^2 points
        X, Y = np.meshgrid(ax, ax, indexing="ij")
        P = np.stack([np.full_like(X, ax[i]), X, Y], -1)
        F[i] = de(formula, P, prm)
    return F, ax[1] - ax[0]


def keep_main_solid(inside, F):
    """Keep only the connected inside region (6-neighbour) that holds the deepest point; returns the mask."""
    try:
        from scipy import ndimage
        lab, n = ndimage.label(inside)
        if n <= 1:
            return inside, n
        seed = lab[np.unravel_index(np.argmin(np.where(inside, F, np.inf)), F.shape)]
        return lab == seed, n
    except ImportError:
        pass
    seed = np.unravel_index(np.argmin(np.where(inside, F, np.inf)), F.shape)
    m = np.zeros_like(inside); m[seed] = True
    while True:  # flood fill by repeated 6-neighbour dilation inside the mask
        g = m.copy()
        g[1:] |= m[:-1]; g[:-1] |= m[1:]; g[:, 1:] |= m[:, :-1]; g[:, :-1] |= m[:, 1:]
        g[:, :, 1:] |= m[:, :, :-1]; g[:, :, :-1] |= m[:, :, 1:]
        g &= inside
        if g.sum() == m.sum():
            break
        m = g
    return m, (2 if m.sum() < inside.sum() else 1)


def _kuhn():
    """Kuhn split: the six tetrahedra of a cube, one per axis order, all sharing the main diagonal."""
    tets = []
    for perm in itertools.permutations(range(3)):
        v = [0, 0, 0]; t = [tuple(v)]
        for a in perm:
            v[a] = 1; t.append(tuple(v))
        tets.append(t)
    return tets


def marching_tets(V, level=0.0):
    """Iso surface V == level (inside V < level) by marching tetrahedra; returns verts (grid units), faces."""
    V = V - level
    nx, ny, nz = V.shape
    idx = np.arange(V.size).reshape(V.shape)
    tris_keys, tris_t, out_dir = [], [], []

    def corner(o):
        return (slice(o[0], nx - 1 + o[0]), slice(o[1], ny - 1 + o[1]), slice(o[2], nz - 1 + o[2]))

    for tet in _kuhn():
        vals = np.stack([V[corner(o)].ravel() for o in tet], -1)            # (cubes, 4)
        ids = np.stack([idx[corner(o)].ravel() for o in tet], -1)
        ins = vals < 0
        cnt = ins.sum(-1)
        act = (cnt > 0) & (cnt < 4)
        vals, ids, ins, cnt = vals[act], ids[act], ins[act], cnt[act]
        # order corners: inside first (stable), so the case is fixed by cnt
        order = np.argsort(~ins, axis=-1, kind="stable")
        vals = np.take_along_axis(vals, order, -1); ids = np.take_along_axis(ids, order, -1)
        for k, pairs in ((1, [[(0, 1), (0, 2), (0, 3)]]),
                         (3, [[(0, 3), (1, 3), (2, 3)]]),
                         (2, [[(0, 2), (0, 3), (1, 3)], [(0, 2), (1, 3), (1, 2)]])):
            sel = cnt == k
            if not sel.any():
                continue
            vs, is_ = vals[sel], ids[sel]
            cc = np.stack(np.unravel_index(is_, V.shape), -1).astype(float)     # (m, 4, 3) corners
            for tri in pairs:
                out_dir.append(cc[:, k:].mean(1) - cc[:, :k].mean(1))
                tris_keys.append(np.stack([np.stack([is_[:, a], is_[:, b]], -1) for a, b in tri], 1))  # (m,3,2)
                tris_t.append(np.stack([vs[:, a] / (vs[:, a] - vs[:, b]) for a, b in tri], 1))      # (m,3)
    if not tris_keys:
        return np.zeros((0, 3)), np.zeros((0, 3), int)
    K = np.concatenate(tris_keys); T = np.concatenate(tris_t)
    lo, hi = np.minimum(K[..., 0], K[..., 1]), np.maximum(K[..., 0], K[..., 1])
    # t is measured from K[...,0]; express the point from the lower id so equal edges give equal points
    t = np.where(K[..., 0] == lo, T, 1 - T)
    key = lo.astype(np.int64) * V.size + hi
    uk, inv = np.unique(key.ravel(), return_inverse=True)
    first = np.zeros(len(uk), int); first[inv[::-1]] = np.arange(inv.size)[::-1]
    a = np.stack(np.unravel_index(lo.ravel()[first], V.shape), -1).astype(float)
    b = np.stack(np.unravel_index(hi.ravel()[first], V.shape), -1).astype(float)
    tt = t.ravel()[first][:, None]
    verts = a + (b - a) * tt
    faces = inv.reshape(-1, 3)
    D = np.concatenate(out_dir)
    p = verts[faces]
    flip = np.einsum("ij,ij->i", np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), D) < 0
    faces[flip] = faces[flip][:, ::-1]                       # normals point from inside corners to outside ones
    faces = faces[(faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])]
    return verts, faces


def edge_check(faces):
    """Watertight check: every directed edge appears once and its reverse once."""
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    key = e[:, 0].astype(np.int64) * (faces.max() + 1) + e[:, 1]
    rkey = e[:, 1].astype(np.int64) * (faces.max() + 1) + e[:, 0]
    u, c = np.unique(key, return_counts=True)
    dup = int((c > 1).sum())
    unmatched = int((~np.isin(rkey, u)).sum())
    return {"edges": int(len(e) // 2), "duplicate_directed_edges": dup, "open_edges": unmatched,
            "watertight": dup == 0 and unmatched == 0}


def fill_voids(m):
    """Outside pockets sealed inside the solid become solid (they would print as trapped cavities)."""
    out = ~m
    try:
        from scipy import ndimage
        lab, _ = ndimage.label(np.pad(out, 1, constant_values=True))
        return ~(lab == lab[0, 0, 0])[1:-1, 1:-1, 1:-1]
    except ImportError:
        pass
    pad = np.pad(out, 1, constant_values=True)
    r = np.zeros_like(pad); r[0, 0, 0] = True
    while True:
        g = r.copy()
        g[1:] |= r[:-1]; g[:-1] |= r[1:]; g[:, 1:] |= r[:, :-1]; g[:, :-1] |= r[:, 1:]
        g[:, :, 1:] |= r[:, :, :-1]; g[:, :, :-1] |= r[:, :, 1:]
        g &= pad
        if g.sum() == r.sum():
            break
        r = g
    return ~r[1:-1, 1:-1, 1:-1]


def _labels(nv, faces):
    lab = np.arange(nv)
    while True:
        m = lab[faces].min(1)
        new = lab.copy()
        np.minimum.at(new, faces.ravel(), np.repeat(m, 3))
        new = new[new]
        if np.array_equal(new, lab):
            return lab
        lab = new


def largest_shell(nv, faces, verts):
    """Keep the face-connected shell with the largest enclosed volume (drops corner-touching specks)."""
    fl = _labels(nv, faces)[faces[:, 0]]
    u, inv = np.unique(fl, return_inverse=True)
    if len(u) == 1:
        return faces
    p = verts[faces]
    v = np.einsum("ij,ij->i", p[:, 0], np.cross(p[:, 1], p[:, 2]))
    vol = np.abs(np.bincount(inv, weights=v))
    return faces[inv == np.argmax(vol)]


def components(nv, faces):
    return int(len(np.unique(_labels(nv, faces)[faces[:, 0]])))


def volume(verts, faces):
    p = verts[faces]
    return float(np.einsum("ij,ij->i", p[:, 0], np.cross(p[:, 1], p[:, 2])).sum() / 6)


def write_stl(path, verts, faces):
    p = verts[faces].astype(np.float32)
    n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
    ln = np.linalg.norm(n, axis=-1, keepdims=True); ln[ln == 0] = 1
    rec = np.zeros(len(faces), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"] = n / ln; rec["v"] = p
    with open(path, "wb") as fh:
        fh.write(b"fractalwright mesh, millimetres".ljust(80, b" "))
        fh.write(struct.pack("<I", len(faces)))
        fh.write(rec.tobytes())


def build(formula, prm, res=200, size_mm=60.0, iso=None, engine="auto"):
    t0 = time.time()
    bound = BOUNDS[formula]
    F, h = sample(formula, prm, res, bound)
    iso = 0.5 * h if iso is None else iso
    inside = F < iso
    main, ncomp = keep_main_solid(inside, F)
    main = fill_voids(main)
    G = np.where(main, F, np.maximum(F, iso + h))        # drop the other islands
    G = np.pad(G, 1, constant_values=iso + bound)          # closed border: the surface cannot leave the grid
    t1 = time.time()
    used = engine
    if engine in ("auto", "skimage"):
        try:
            from skimage.measure import marching_cubes
            verts, faces, _, _ = marching_cubes(G, level=iso, allow_degenerate=False)
            used = "skimage"
        except ImportError:
            if engine == "skimage":
                raise SystemExit("3d mesh: --engine skimage needs scikit-image (pip install scikit-image)")
            used = "numpy"
    if used == "numpy":
        verts, faces = marching_tets(G, iso)
    nshell_before = components(len(verts), faces)
    faces = largest_shell(len(verts), faces, verts)
    if volume(verts, faces) < 0:                             # skimage winds by gradient; make normals outward
        faces = faces[:, ::-1].copy()
    # grid units -> model units -> millimetres, longest side size_mm, sitting on z = 0
    verts = (verts - 1) * h - bound
    ext = verts.max(0) - verts.min(0)
    s = size_mm / ext.max()
    verts = (verts - verts.min(0)) * s
    chk = edge_check(faces)
    info = {"formula": formula, "params": prm, "grid": res, "voxel_mm": round(h * s, 4), "iso": iso,
            "engine": used, "islands_dropped": max(0, ncomp - 1), "shells_dropped": int(nshell_before - 1), "triangles": int(len(faces)),
            "vertices": int(len(verts)), "size_mm": [round(float(v), 2) for v in verts.max(0)],
            "volume_mm3": round(volume(verts, faces), 1), "shells": components(len(verts), faces), **chk,
            "seconds": {"sample": round(t1 - t0, 2), "mesh": round(time.time() - t1, 2)}}
    return verts, faces, info


def cmd_mesh(a, recipe):
    formula = recipe["formula"]
    prm = dict(recipe["params"])
    if a.iter:
        prm["iter"] = a.iter
    elif formula in MESH_ITER:
        prm["iter"] = min(prm.get("iter", 99), MESH_ITER[formula])
    out = Path(a.out or f"{formula}.stl")
    verts, faces, info = build(formula, prm, res=a.res or MESH_RES.get(formula, 200), size_mm=a.size_mm or 60.0, engine=a.engine)
    write_stl(out, verts, faces)
    side = out.with_suffix(".json")
    side.write_text(json.dumps({"kind": "3d-mesh", "stl": out.name, **info}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out} and {side}: {info['triangles']} triangles, {info['size_mm']} mm, "
          f"{'watertight' if info['watertight'] else 'NOT watertight'}, {info['shells']} shell(s), "
          f"engine {info['engine']}, {sum(info['seconds'].values()):.1f} s")
    return 0 if info["watertight"] and info["shells"] == 1 else 3
