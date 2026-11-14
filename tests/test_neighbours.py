"""Proof bars for fw_neighbours.py (rd, ca, tiling, kleinian). Run: python -m unittest discover -s tests -v

Measured on 2026-11-14 (numpy 2.5.2, Python 3.14.6); numbers in TESTS.md T-20261114-12.
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
import fw_neighbours as n  # noqa: E402


class ReactionDiffusion(unittest.TestCase):
    def test_same_seed_same_pixels(self):
        a = n.gray_scott(0.0545, 0.062, 64, 64, 600, seed=1)
        b = n.gray_scott(0.0545, 0.062, 64, 64, 600, seed=1)
        c = n.gray_scott(0.0545, 0.062, 64, 64, 600, seed=2)
        self.assertTrue((a == b).all())
        self.assertFalse((a == c).all())
        self.assertTrue(np.isfinite(a).all())

    def test_presets_form_patterns(self):
        # 128 px, 5000 steps: measured B std 0.142 (coral), 0.117 (mitosis), 0.143 (default); bar > 0.05, no NaN
        for name, p in n.RD_PRESETS.items():
            B = n.gray_scott(p["f"], p["k"], 128, 128, 5000, seed=0)
            self.assertTrue(np.isfinite(B).all(), name)
            self.assertGreater(B.std(), 0.05, name)

    def test_cli_recipe_redraws(self):
        with tempfile.TemporaryDirectory() as d:
            p1, p2 = Path(d, "a.png"), Path(d, "b.png")
            run = [sys.executable, str(ROOT / "scripts" / "fw.py")]
            subprocess.run(run + ["rd", "mitosis", "-o", str(p1), "--size", "48x48", "--steps", "300"], check=True,
                           capture_output=True)
            rec = p1.with_suffix(".json")
            self.assertEqual(json.loads(rec.read_text())["params"]["f"], 0.0367)
            subprocess.run(run + ["rd", str(rec), "-o", str(p2)], check=True, capture_output=True)
            self.assertEqual(p1.read_bytes(), p2.read_bytes())


class CellularAutomata(unittest.TestCase):
    def test_rule90_sierpinski(self):
        # 1023 steps: measured D - log3/log2 = -0.044 over 2.11 decades (bar 0.06)
        r = fw.box_analysis(n.elementary(90, 1023))
        self.assertAlmostEqual(r["dimension"], math.log(3) / math.log(2), delta=0.06)
        self.assertIn("fractal-like", r["verdict"])

    def test_rule90_cell_count(self):
        # Rule 90 from one cell: 3^k live cells in the first 2^k rows (Gould's sequence sum)
        self.assertEqual(int(n.elementary(90, 255).sum()), 3 ** 8)

    def test_life_blinker(self):
        self.assertEqual(n.parse_bs("B3/S23"), ({3}, {2, 3}))
        g = np.zeros((5, 5), bool)
        g[2, 1:4] = True
        b, s = n.parse_bs("B3/S23")
        bm, sm = np.zeros(9, bool), np.zeros(9, bool)
        bm[list(b)] = True
        sm[list(s)] = True
        for _ in range(2):
            k = sum(np.roll(np.roll(g, dy, 0), dx, 1).astype(np.int8)
                    for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dy or dx)
            g = np.where(g, sm[k], bm[k])
        self.assertTrue(g[2, 1:4].all() and g.sum() == 3)
        a = n.lifelike("B3/S23", 40, 40, 20, seed=5)
        self.assertTrue((a == n.lifelike("B3/S23", 40, 40, 20, seed=5)).all())


class Tiling(unittest.TestCase):
    def test_not_fractal(self):
        # measured local-slope spread 0.65 (square) .. 0.79 (penrose), drift ~1.0 -> 1.7-1.9; bar 0.30
        for kind, k in (("square", 8), ("hex", 8), ("triangle", 8), ("penrose", 6)):
            m, _ = n.tiling_mask(kind, k, 1024, 1024)
            r = fw.box_analysis(m)
            self.assertNotIn("fractal-like", r["verdict"], kind)
            self.assertIn("not fractal", r["verdict"], kind)

    def test_penrose_rhomb_ratio(self):
        # thick:thin rhomb count tends to the golden ratio; Robinson colours 1:0 count ratio
        t = n.penrose_triangles(8)
        ones = sum(1 for c, *_ in t if c == 1)
        self.assertAlmostEqual(ones / (len(t) - ones), n.PHI, delta=0.01)


class Kleinian(unittest.TestCase):
    def test_apollonian_dimension(self):
        # 2048 px, circles to half a pixel: measured D - 1.3056867 = +0.0010 (1024 px: +0.0016); bar 0.01
        m = n.circles_mask(n.apollonian_circles(0.5 / 2048), 2048)
        r = fw.box_analysis(m)
        self.assertAlmostEqual(r["dimension"], 1.3056867, delta=0.01)

    def test_descartes_tangency(self):
        c = n.apollonian_circles(0.05)
        for z, r in c[1:40]:
            self.assertLessEqual(abs(z) + r, 1 + 1e-9)

    def test_grandma_parabolic(self):
        a, b = n.grandma(2, 2)
        comm = a @ b @ n._inv(a) @ n._inv(b)
        self.assertAlmostEqual(complex(np.trace(comm)), -2, places=9)
        p = n.limit_points(2, 2, 20000, seed=0)
        self.assertTrue(np.isfinite(p).all())
        self.assertTrue((p == n.limit_points(2, 2, 20000, seed=0)).all())


if __name__ == "__main__":
    unittest.main()
