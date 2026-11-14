"""Proof bars for fw_gen.py (flame, lsystem, attractor). Run: python -m unittest discover -s tests -v

Measured on 2026-11-14 (numpy 2.5.2, Python 3.14.6); numbers in TESTS.md T-20261114-8.
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
import fw_extra as fx  # noqa: E402
import fw_gen as g  # noqa: E402


class Flame(unittest.TestCase):
    def test_determinism(self):
        # same seed: identical pixels; another seed differs
        fl = g.FLAME_PRESETS["swirl-sierpinski"]
        a, _, _ = g.flame_render(fl, 64, 64, 40000, seed=3, supersample=2)
        b, _, _ = g.flame_render(fl, 64, 64, 40000, seed=3, supersample=2)
        c, _, _ = g.flame_render(fl, 64, 64, 40000, seed=4, supersample=2)
        self.assertTrue((a == b).all())
        self.assertFalse((a == c).all())

    def test_sierpinski_dimension(self):
        # 3 linear xforms, 3M points, 1024 px: measured D - log3/log2 = -0.021 (bar 0.05)
        fl = g.FLAME_PRESETS["sierpinski"]
        _, raw, _ = g.flame_render(fl, 1024, 1024, 3_000_000, 0, 1, view={"centre": ["0.5", "0.433"], "width": "1.0"},
                                   density=False)
        D = fw.box_analysis(raw > 0)["dimension"]
        self.assertAlmostEqual(D, math.log(3) / math.log(2), delta=0.05)

    def test_all_variations_finite(self):
        rng = np.random.default_rng(0)
        x, y = rng.uniform(-2, 2, 500), rng.uniform(-2, 2, 500)
        self.assertGreaterEqual(len(g.VARIATIONS), 11)
        for name in g.VARIATIONS:
            fl = {"xforms": [{"affine": [0.5, 0, 0, 0.5, 0, 0], "variations": {name: 1.0}}]}
            px, py, pc = g.flame_points(fl, 4096, 0, walkers=512)
            self.assertGreater(len(px), 3000, name)

    def test_random_search_keeps_good(self):
        best = g.flame_search(seed=0, tries=12)
        self.assertTrue(best)
        sc, cov, _ = best[0]
        self.assertGreater(sc, 0)
        self.assertTrue(0.02 <= cov <= 1.0)
        # a blank histogram scores zero
        self.assertEqual(g.flame_score(np.zeros((32, 32)))[0], 0.0)

    def test_cli_recipe_redraws(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "f.png"
            run = [sys.executable, str(ROOT / "scripts" / "fw.py"), "flame"]
            subprocess.run(run + ["swirl-sierpinski", "-o", str(out), "--size", "64x64", "--points", "30000"],
                           check=True, capture_output=True)
            rec = json.loads(out.with_suffix(".json").read_text())
            self.assertEqual(rec["family"], "flame")
            out2 = Path(d) / "g.png"
            subprocess.run(run + [str(out.with_suffix(".json")), "-o", str(out2)], check=True, capture_output=True)
            self.assertEqual(out.read_bytes(), out2.read_bytes())


class LSystem(unittest.TestCase):
    def test_koch_dimension(self):
        # n 7 (16384 segments) at 2048 px: measured D - log4/log3 = -0.022 (bar 0.05)
        segs, _ = g.lsystem_build(g.LSYSTEMS["koch"], n=7)
        D = fw.box_analysis(g.segments_mask(segs, 2048, 2048))["dimension"]
        self.assertAlmostEqual(D, math.log(4) / math.log(3), delta=0.05)

    def test_hilbert_visits_each_cell_once(self):
        for n in (2, 3, 4, 5):
            _, v = g.lsystem_build(g.LSYSTEMS["hilbert"], n=n)
            v = np.round(v).astype(int)
            v -= v.min(0)
            self.assertEqual(len(v), 4 ** n)
            self.assertEqual(len(set(map(tuple, v))), 4 ** n)
            self.assertEqual(v.max(0).tolist(), [2 ** n - 1] * 2)

    def test_stochastic_seeded(self):
        sp = g.LSYSTEMS["plant-stochastic"]
        a = g.lsystem_expand(sp["axiom"], sp["rules"], 4, seed=1)
        self.assertEqual(a, g.lsystem_expand(sp["axiom"], sp["rules"], 4, seed=1))
        self.assertNotEqual(a, g.lsystem_expand(sp["axiom"], sp["rules"], 4, seed=2))

    def test_cli_png_svg(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "p.png"
            subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "lsystem", "plant-a", "-o", str(out),
                            "--size", "128x128", "--n", "3"], check=True, capture_output=True)
            self.assertTrue(out.with_suffix(".svg").read_text().startswith("<svg"))
            self.assertTrue(out.with_suffix(".json").exists())


class Attractors(unittest.TestCase):
    def test_lorenz_correlation_dimension(self):
        # 60k RK4 points (dt 0.01), 3000-point subset, fit 0.01-0.1 of size: measured 2.045, 2.047 (bar 2.05 +- 0.1)
        p = g.lorenz(60000)
        for s in (0, 1):
            self.assertAlmostEqual(fx.correlation_dimension(p, n=3000, seed=s, lo=0.01, hi=0.1), 2.05, delta=0.1)

    def test_clifford_not_blank_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            step = g.ATTRACTORS["clifford"]["step"](g.ATTRACTORS["clifford"]["params"])
            a, cnt = g.density_png(g.map_points(step, 100000, 0), Path(d) / "a.png", 128, 128)
            b, _ = g.density_png(g.map_points(step, 100000, 0), Path(d) / "b.png", 128, 128)
            self.assertTrue((a == b).all())
            self.assertGreater((cnt > 0).mean(), 0.1)

    def test_maps_bounded(self):
        for k in ("clifford", "dejong", "icon", "icon-3"):
            pts = g.map_points(g.ATTRACTORS[k]["step"](g.ATTRACTORS[k]["params"]), 50000)
            self.assertEqual(len(pts), 50000, k)

    def test_search_uses_sprott_ranking(self):
        hits, _ = g.attractor_search2("clifford", hits=2, seed=0)
        self.assertTrue(hits)
        self.assertEqual([h["score"] for h in hits], sorted(h["score"] for h in hits))
        self.assertTrue(all(h["lyapunov_bits"] > 0 for h in hits))


if __name__ == "__main__":
    unittest.main()
