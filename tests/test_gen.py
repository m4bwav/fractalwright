"""Proof bars for fw_gen.py (flame, lsystem, attractor). Run: python -m unittest discover -s tests -v

Measured on 2026-11-14 (numpy 2.5.2, Python 3.14.6); numbers in TESTS.md T-20261114-8.
"""
import json
import math
import re
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

    def test_lorenz_cli_states_d2_and_fit(self):
        # default fit g.LORENZ_D2_FIT (0.01-0.1) printed with the value; measured 2.045 at 60k points seed 0
        self.assertEqual(g.LORENZ_D2_FIT, (0.01, 0.1))
        with tempfile.TemporaryDirectory() as d:
            res = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "attractor", "lorenz", "-o",
                                  str(Path(d) / "l.png"), "--size", "64x48"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            m = re.search(r"Lorenz D2 ([0-9.]+) .*fit range 0.01-0.1", res.stdout)
            self.assertIsNotNone(m, res.stdout)
            self.assertAlmostEqual(float(m.group(1)), 2.05, delta=0.1)

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


class PublishedParameterTests(unittest.TestCase):
    """0.7.0 paper checks (references/05 sections 4b, 4c)."""

    def test_icon_sets_match_symmetry_in_chaos_table_a1(self):
        table = {  # Field and Golubitsky, Symmetry in Chaos 2nd ed., Table A.1: lambda, alpha, beta, gamma, omega, n
            "icon": [-2.08, 1.0, -0.1, 0.167, 0.0, 7], "icon-3": [1.56, -1.0, 0.1, -0.82, 0.0, 3],
            "icon-halloween": [-2.7, 5.0, 1.5, 1.0, 0.0, 6], "icon-clam": [1.56, -1.0, 0.1, -0.82, 0.12, 3],
            "icon-streamers": [-1.86, 2.0, 0.0, 1.0, 0.1, 4], "icon-flower": [-2.5, 5.0, -1.9, 1.0, 0.188, 5]}
        rng = np.random.default_rng(1)
        x, y = rng.uniform(-0.5, 0.5, 200), rng.uniform(-0.5, 0.5, 200)
        for k, p in table.items():
            self.assertEqual(g.ATTRACTORS[k]["params"], p, k)
            f, n = g.icon_step(p), int(p[5])
            u, v = f(x, y)
            w = np.exp(2j * np.pi / n)  # Z_n: f(wz) = w f(z)
            ru, rv = f((w * (x + 1j * y)).real, (w * (x + 1j * y)).imag)
            self.assertTrue(np.allclose(ru + 1j * rv, w * (u + 1j * v)), k)
            cu, cv = f(x, -y)  # D_n (omega = 0) adds the reflection f(conj z) = conj f(z)
            self.assertEqual(bool(np.allclose(cu + 1j * cv, u - 1j * v)), p[4] == 0.0, k)
            self.assertEqual(len(g.map_points(f, 20000)), 20000, k)

    def test_flow_equations_and_parameters_match_papers(self):
        self.assertEqual(g.ATTRACTORS["chen"]["params"], [35.0, 3.0, 28.0])   # Chen and Ueta 1999
        self.assertEqual(g.ATTRACTORS["lu"]["params"], [36.0, 3.0, 20.0])     # Lu and Chen 2002
        x, y, z = 1.3, -0.7, 2.1
        self.assertEqual(g.flow_rhs("chen", [35, 3, 28])(x, y, z),
                         (35 * (y - x), (28 - 35) * x - x * z + 28 * y, x * y - 3 * z))
        self.assertEqual(g.flow_rhs("lu", [36, 3, 20])(x, y, z), (36 * (y - x), -x * z + 20 * y, x * y - 3 * z))
        for k in ("chen", "lu"):
            p = g.flow(k, 20000, dt=0.002)
            self.assertTrue(np.isfinite(p).all() and np.abs(p).max() < 100, k)
            self.assertTrue((p[:, 0] > 5).any() and (p[:, 0] < -5).any(), k)  # both wings

    def test_yalcin_multiscroll_has_mx_plus_nx_plus_one_scrolls(self):
        # Yalcin et al. 2002 eq. (3)-(4): Mx = 0, Nx = 4, a = 0.4 gives equilibria x = 0..4 and five scrolls (Fig. 3)
        th = [0.5, 1.5, 2.5, 3.5]
        self.assertEqual([g.yalcin_f1(x, th) for x in (0.0, 1.0, 2.0, 3.0, 4.0)], [0, 1, 2, 3, 4])
        self.assertEqual(g.yalcin_g(-0.7, -0.5), -1.0)
        self.assertEqual(g.yalcin_g(-0.2, -0.5), 0.0)
        p = g.flow("multiscroll", 40000, dt=0.05)
        visits = [int((np.abs(p[:, 0] - e) < 0.25).sum()) for e in range(5)]
        self.assertTrue(all(v > 200 for v in visits), visits)
        self.assertTrue(np.abs(p).max() < 6)


if __name__ == "__main__":
    unittest.main()
