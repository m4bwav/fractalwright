"""Proof bars for fw_extra.py (book-derived tools). Run: python -m unittest discover -s tests -v

Measured on 2026-11-14 (numpy 2.5.2, Python 3.14.6); numbers in TESTS.md T-20261114-7.
"""
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


class Logistic(unittest.TestCase):
    def test_period_doubling(self):
        # measured: 1, 2, 4, 8 branches at r 2.8, 3.2, 3.5, 3.56
        self.assertEqual([fx.logistic_branches(r) for r in (2.8, 3.2, 3.5, 3.56)], [1, 2, 4, 8])

    def test_lyapunov_units(self):
        # r = 4: exactly 1 bit = ln 2 nats per iteration; measured 0.9999995 bits
        self.assertAlmostEqual(fx.logistic_lyapunov(4.0), 1.0, delta=0.01)
        self.assertAlmostEqual(fx.logistic_lyapunov(4.0, bits=False), math.log(2), delta=0.01)
        self.assertLess(fx.logistic_lyapunov(3.2), 0)

    def test_explain_plots(self):
        with tempfile.TemporaryDirectory() as t:
            for kind in ("cobweb", "bifurcation"):
                out = Path(t) / f"{kind}.png"
                self.assertEqual(fw.main(["explain", "logistic", "--plot", kind, "-o", str(out)]), 0)
                self.assertTrue(out.read_bytes().startswith(b"\x89PNG"))
        self.assertEqual(fw.main(["explain", "coastline"]), 0)


class Attractors(unittest.TestCase):
    def test_henon_known_values(self):
        # Henon (1.4, 0.3): L 0.603 bits (0.419 nats), D2 ~1.21. Measured 0.6036 bits, D2 1.201 / 1.195.
        lyap, pts = fx.orbit_lyapunov(lambda x, y: fx.henon_step(x, y), x=0.1, y=0.1, n=50000)
        self.assertAlmostEqual(lyap, 0.603, delta=0.02)
        self.assertAlmostEqual(fx.correlation_dimension(pts), 1.21, delta=0.05)

    def test_search_ranked(self):
        hits, tries = fx.attractor_search(3, seed=0, n=5000)
        self.assertEqual(len(hits), 3)
        self.assertEqual([h["score"] for h in hits], sorted(h["score"] for h in hits))
        self.assertTrue(all(h["lyapunov_bits"] > 0 for h in hits))
        self.assertEqual(fx.sprott_encode(fx.sprott_decode(hits[0]["code"])), hits[0]["code"])


class IFS(unittest.TestCase):
    def test_det_probabilities_flatten_density(self):
        # four unequal tiles of the unit square: 8x8 histogram cv 0.014 with |det|, 1.049 with equal p
        m = fx.IFS_PRESETS["unequal-tiles"]
        cv = []
        for probs in (None, [1] * 4):
            p = fx.chaos_game(m, 400000, probs)
            h, _, _ = np.histogram2d(p[:, 0], p[:, 1], 8, [[0, 1], [0, 1]])
            cv.append(h.std() / h.mean())
        self.assertLess(cv[0], 0.05)
        self.assertGreater(cv[1], 0.5)
        self.assertGreater(fx.ifs_probabilities(fx.IFS_PRESETS["fern"])[0], 0)  # zero-det stem keeps a floor

    def test_envelope_contains_attractor(self):
        # Canright-style ball: every chaos-game point inside on the presets and 20 random 3-map IFS;
        # measured max distance / R: 1.0 (Sierpinski vertices on the ball), fern 0.973, random 0.995
        for name, m in fx.IFS_PRESETS.items():
            c, R = fx.ifs_envelope(m)
            p = fx.chaos_game(m, 100000)
            self.assertLessEqual(np.hypot(p[:, 0] - c[0], p[:, 1] - c[1]).max(), R * (1 + 1e-9), name)
        rng = np.random.default_rng(3)
        for t in range(20):
            m = [list(rng.uniform(-0.6, 0.6, 4)) + list(rng.uniform(-1, 1, 2)) for _ in range(3)]
            try:
                c, R = fx.ifs_envelope(m)
            except ValueError:
                continue
            p = fx.chaos_game(m, 20000, seed=t)
            self.assertLessEqual(np.hypot(p[:, 0] - c[0], p[:, 1] - c[1]).max(), R * (1 + 1e-9))

    def test_discard(self):
        # start far away: 8 of the first 50 points lie outside the envelope without the discard, none with 20
        m = fx.IFS_PRESETS["sierpinski"]
        c, R = fx.ifs_envelope(m)
        out = lambda p: np.sum(np.hypot(p[:, 0] - c[0], p[:, 1] - c[1]) > R * 1.0001)  # noqa: E731
        self.assertGreater(out(fx.chaos_game(m, 50, discard=0, start=(50.0, 50.0))), 0)
        self.assertEqual(out(fx.chaos_game(m, 50, discard=20, start=(50.0, 50.0))), 0)


class Terrain(unittest.TestCase):
    def test_creases(self):
        # crease ratio at 513 / 512 px, 3 seeds: diamond-square 1.17-1.19, spectral 0.98-1.00
        for s in range(3):
            self.assertGreater(fx.crease_ratio(fx.diamond_square(9, 0.8, s)), 1.10)
            self.assertAlmostEqual(fx.crease_ratio(fw.synth_fbm2d(512, 0.8, s)), 1.0, delta=0.04)

    def test_command_default_spectral(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "t.png"
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "terrain", "-o", str(out), "--k", "7"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("spectral", r.stdout)
            self.assertEqual(np.load(Path(t) / "t.npy").shape, (128, 128))


class FIF(unittest.TestCase):
    P = [(0, 0), (1, 1), (2, 0.3), (3, 0.8), (4, 0)]

    def test_pass_through_and_zero_scaling(self):
        x, y = fx.fif(self.P, [0, 0, 0, 0])
        lin = np.interp(x, [p[0] for p in self.P], [p[1] for p in self.P])
        self.assertLess(np.abs(y - lin).max(), 1e-12)
        x, y = fx.fif(self.P, [0.5, -0.5, 0.5, -0.5])
        for px, py in self.P:
            self.assertAlmostEqual(np.interp(px, x, y), py, places=12)

    def test_dimension(self):
        # semivariogram D vs 1 + log(sum|d|)/log N at 4^8 + 1 samples: errors 0.024, 0.028, 0.035, 0.002
        for d in ([0.5, -0.5, 0.5, -0.5], [0.6, 0.6, -0.6, 0.6], [0.4, 0.4, 0.4, 0.4], [0.7, -0.7, 0.7, -0.7]):
            x, y = fx.fif(self.P, d, depth=8)
            got = fw.profile_analysis(y)["D_semivariogram"]
            self.assertAlmostEqual(got, fx.fif_dimension(d), delta=0.05, msg=str(d))


if __name__ == "__main__":
    unittest.main()
