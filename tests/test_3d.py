"""Proof bars for fw.py 3d (fw_3d.py, scripts/page/fractal3d.frag). Run: python -m unittest discover -s tests -v

Browser tests need Playwright and system Edge (or Chrome); they skip cleanly without them.
The DE sanity test runs the same Mandelbulb formula in NumPy (float64) and checks it as a lower bound:
march rays by the estimate and sample the inside test along every step; points found inside the set
before the march stops are overshoots. Measured 2026-11-14 (TESTS.md T-20261114-10): see the bar below.
"""
import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fw_3d  # noqa: E402

OVERSHOOT_BAR = 0.01   # fraction of sampled step points inside the set


def bulb(p, iters=10, power=8.0):
    """Vectorised Mandelbulb: -> (DE, inside). Same formula as deBulb in fractal3d.frag."""
    c = p.copy()
    z = p.copy()
    dr = np.ones(len(p))
    alive = np.ones(len(p), bool)
    for _ in range(iters):
        r = np.linalg.norm(z, axis=1)
        alive &= r <= 2.0
        a = alive
        if not a.any():
            break
        ra = np.maximum(r[a], 1e-12)
        th = np.arccos(np.clip(z[a, 2] / ra, -1, 1)) * power
        ph = np.arctan2(z[a, 1], z[a, 0]) * power
        dr[a] = power * ra ** (power - 1) * dr[a] + 1.0
        rp = ra ** power
        z[a] = rp[:, None] * np.stack([np.sin(th) * np.cos(ph), np.sin(th) * np.sin(ph), np.cos(th)], 1) + c[a]
    r = np.maximum(np.linalg.norm(z, axis=1), 1e-12)
    return 0.5 * np.log(r) * r / dr, alive & (r <= 2.0)


def inside(p, iters=24):
    return bulb(p, iters)[1]


class RecipeTests(unittest.TestCase):
    def test_round_trip(self):
        for f in fw_3d.FORMULAS3D:
            for v in ("whole", "close"):
                r = fw_3d.default_recipe(f, v)
                r["remedies"].update({"camera": True, "ao": True})
                n = fw_3d.normalise(r)
                back = fw_3d.normalise(json.loads(json.dumps(n)))
                self.assertEqual(n, back)
                self.assertEqual(fw_3d.uniforms(n), fw_3d.uniforms(back))

    def test_composed_camera(self):
        r = fw_3d.normalise({"formula": "mandelbulb", "remedies": {"camera": True}})
        cam = r["camera"]
        self.assertTrue(35 <= 12 / np.tan(np.radians(cam["fov_deg"] / 2)) <= 50)   # 35-50 mm band
        self.assertLess(cam["eye"][1], 0)          # low angle: eye below the subject, looking up
        lazy = fw_3d.normalise({"formula": "mandelbulb"})["camera"]
        self.assertEqual(lazy["fov_deg"], fw_3d.LAZY_FOV)

    def test_bad_names(self):
        with self.assertRaises(ValueError):
            fw_3d.normalise({"formula": "nope"})
        with self.assertRaises(ValueError):
            fw_3d.normalise({"formula": "menger", "remedies": {"bloom": True}})


class DESanity(unittest.TestCase):
    def test_mandelbulb_de_is_lower_bound(self):
        rng = np.random.default_rng(1)
        n = 400
        d = rng.normal(size=(n, 3))
        d /= np.linalg.norm(d, axis=1)[:, None]
        ro = -2.5 * d + rng.uniform(-0.3, 0.3, (n, 3))
        t = np.zeros(n)
        live = np.ones(n, bool)
        bad = total = 0
        for _ in range(200):
            p = ro + d * t[:, None]
            de, _ = bulb(p)
            live &= (de > 1e-4) & (t < 6)
            if not live.any():
                break
            step = np.where(live, de, 0)
            fr = np.linspace(0.1, 1.0, 6)
            pts = (p[live, None, :] + d[live, None, :] * (step[live, None, None] * fr[None, :, None])).reshape(-1, 3)
            ins = inside(pts)
            bad += int(ins.sum())
            total += len(pts)
            t += step
        rate = bad / total
        print(f"\nmandelbulb DE overshoot: {bad}/{total} = {rate:.5f}")
        self.assertLess(rate, OVERSHOOT_BAR)


def _browser():
    try:
        import playwright  # noqa: F401
    except ImportError:
        return None
    try:
        return fw_3d.Browser3D()
    except Exception:  # noqa: BLE001
        return None


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = _browser()

    @classmethod
    def tearDownClass(cls):
        if cls.b:
            cls.b.close()

    def setUp(self):
        if not self.b:
            self.skipTest("no Playwright + Edge/Chrome")

    def test_deterministic(self):
        for f in fw_3d.FORMULAS3D:
            r = fw_3d.normalise({"formula": f, "size": {"w": 96, "h": 64}, "remedies": {k: True for k in fw_3d.REMEDIES}})
            a, _ = self.b.render(r)
            self.b.render(fw_3d.normalise({"formula": "menger", "size": {"w": 64, "h": 48}}))  # disturb state
            c, _ = self.b.render(json.loads(json.dumps(r)))
            self.assertTrue(np.array_equal(a, c), f)
            self.assertGreater(a.std(), 5, f)        # not a blank frame


if __name__ == "__main__":
    unittest.main()
