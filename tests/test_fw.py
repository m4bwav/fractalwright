"""Proof bars for fw.py. Run: python -m unittest discover -s tests -v

Measured on 2026-11-14 (numpy 2.5.2, Python 3.14.6); tolerances come from
these numbers with headroom, see ai-docs/log.md (2026-11-14 Step D).
"""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fw  # noqa: E402

SIERPINSKI = math.log(3) / math.log(2)
KOCH = math.log(4) / math.log(3)


def sierpinski(n=1024):
    """Pascal's triangle mod 2: pixel filled iff (x & y) == 0."""
    y, x = np.mgrid[0:n, 0:n]
    return (x & y) == 0


def sierpinski_chaos(n=1024, k=3_000_000, seed=0):
    """Chaos game on an equilateral triangle: not aligned to the box grid."""
    rng = np.random.default_rng(seed)
    V = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, math.sqrt(3) / 2]])
    b = V[rng.integers(0, 3, k)]
    pts = np.zeros((k, 2))
    for j in range(60):  # p_i = sum_j v_(i-j) / 2^(j+1); older terms are below float64 resolution
        pts[j:] += b[: k - j] / 2.0 ** (j + 1)
    pts = pts[60:]
    m = np.zeros((int(n * 0.87) + 1, n), bool)
    m[(pts[:, 1] * (n - 1)).astype(int), (pts[:, 0] * (n - 1)).astype(int)] = True
    return m


def koch(n=2048, level=7):
    """Koch curve rasterised by dense sampling of each segment."""
    pts = np.array([0.0 + 0j, 1.0 + 0j])
    rot = np.exp(1j * math.pi / 3)
    for _ in range(level):
        a, b = pts[:-1], pts[1:]
        d = (b - a) / 3
        p1, p2 = a + d, a + 2 * d
        peak = p1 + d * rot
        new = np.empty(len(a) * 4 + 1, complex)
        new[0:-1:4], new[1::4], new[2::4], new[3::4] = a, p1, peak, p2
        new[-1] = pts[-1]
        pts = new
    t = np.linspace(0, 1, 8, endpoint=False)
    seg = (pts[:-1, None] + (pts[1:] - pts[:-1])[:, None] * t).ravel()
    m = np.zeros((n // 3 + 2, n), bool)
    xi = np.clip((seg.real * (n - 1)).astype(int), 0, n - 1)
    yi = np.clip((seg.imag * (n - 1)).astype(int), 0, m.shape[0] - 1)
    m[yi, xi] = True
    return m


class Determinism(unittest.TestCase):
    def test_same_recipe_same_pixels(self):
        for preset in ("mandelbrot-full", "julia-rabbit", "burning-ship-full", "tricorn-full", "multibrot-3"):
            r = fw.load_recipe(preset)
            r["size"] = {"w": 160, "h": 120, "supersample": 1}
            a = fw.render_array(json.loads(json.dumps(r)))
            b = fw.render_array(json.loads(json.dumps(r)))
            self.assertTrue(np.array_equal(a, b), preset)

    def test_saved_recipe_redraws_identically(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "m.png"
            cmd = [sys.executable, str(ROOT / "scripts" / "fw.py"), "render", "seahorse", "-o", str(out), "--size", "120x90"]
            subprocess.run(cmd, check=True, capture_output=True)
            out2 = Path(d) / "m2.png"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "render", str(out.with_suffix(".json")), "-o", str(out2)],
                           check=True, capture_output=True)
            self.assertEqual(out.read_bytes(), out2.read_bytes())
            rec = json.loads(out.with_suffix(".json").read_text())
            self.assertEqual(rec["view"]["centre"], ["-0.7436447860", "0.1318252536"])

    def test_python_fallback_matches_numpy(self):
        r = fw.load_recipe("mandelbrot-full")
        r["size"] = {"w": 64, "h": 48, "supersample": 1}
        r["params"]["max_iter"] = 200
        a = fw.render_array(json.loads(json.dumps(r))).astype(int)
        rows = fw.render_rows_py(json.loads(json.dumps(r)))
        b = np.frombuffer(b"".join(rows), np.uint8).reshape(48, 64, 3).astype(int)
        self.assertLess(np.abs(a - b).mean(), 1.0)


class Symmetry(unittest.TestCase):
    def test_mandelbrot_mirror_real_axis(self):
        r = fw.load_recipe("mandelbrot-full")
        r["size"] = {"w": 320, "h": 240, "supersample": 1}
        img = fw.render_array(r)
        self.assertTrue(np.array_equal(img, img[::-1]))


class Dimensions(unittest.TestCase):
    def test_sierpinski_aligned(self):
        # measured error 4e-16: the lattice matches the power-of-two boxes exactly
        D, _ = fw.box_dimension(sierpinski(1024))
        self.assertAlmostEqual(D, SIERPINSKI, delta=1e-6)

    def test_sierpinski_chaos_game(self):
        # measured error +0.0087 at 1024 px (+0.0051 at 2048)
        D, _ = fw.box_dimension(sierpinski_chaos(1024))
        self.assertAlmostEqual(D, SIERPINSKI, delta=0.02)

    def test_koch(self):
        # measured error +0.0193 at 2048 px (+0.0245 at 1024, +0.0071 at 4096)
        D, _ = fw.box_dimension(koch(2048))
        self.assertAlmostEqual(D, KOCH, delta=0.04)


class Area(unittest.TestCase):
    def test_mandelbrot_area_1024(self):
        # measured +0.00018 at 1024 px / 10^4 iterations (+0.00050 at 512, +0.00035 at 2048)
        A = fw.mandelbrot_area(1024, 10000)
        self.assertAlmostEqual(A, 1.50659177, delta=0.002)


if __name__ == "__main__":
    unittest.main()
