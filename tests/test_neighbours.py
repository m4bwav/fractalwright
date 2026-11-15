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

    def test_size_accepts_bare_int(self):
        # `fw.py rd --size 64` crashed with ValueError before 0.3.0
        self.assertEqual(n._size("64"), (64, 64))
        self.assertEqual(n._size("48x32"), (48, 32))
        for bad in ("abc", "0", "4x4x4", "-3"):
            with self.assertRaises(SystemExit):
                n._size(bad)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "s.png")
            res = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "rd", "mitosis", "-o", str(p),
                                  "--size", "40", "--steps", "50"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(int.from_bytes(p.read_bytes()[16:24], "big"), (40 << 32) | 40)  # PNG IHDR w, h

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


class ReactionDiffusionVideo(unittest.TestCase):
    """Palette and --video (0.2.1). 96 px, 1000 steps: B max 0.375 (64 px dies out: B max 2e-33 at 600 steps)."""

    def test_palette_colours_and_grey_default_unchanged(self):
        B = n.gray_scott(0.055, 0.062, 96, 96, 1000, seed=0)
        grey = n.rd_rgb(B)
        self.assertEqual(grey.ndim, 2)
        self.assertTrue((grey == np.clip(255 - B / B.max() * 255, 0, 255).astype(np.uint8)).all())
        fire = n.rd_rgb(B, "fire")
        self.assertEqual(fire.shape, (96, 96, 3))
        self.assertFalse((fire[..., 0] == fire[..., 2]).all())
        self.assertFalse((n.rd_rgb(B, "ocean") == fire).all())

    def test_video_frames_and_determinism(self):
        if not fw.shutil.which("ffmpeg"):
            self.skipTest("ffmpeg missing")
        run = [sys.executable, str(ROOT / "scripts" / "fw.py"), "rd", "default", "--size", "96x96", "--steps", "1000",
               "--palette", "fire", "--frames", "10", "--fps", "10", "--seed", "3"]
        with tempfile.TemporaryDirectory() as d:
            v1, v2 = Path(d, "a.mp4"), Path(d, "b.mp4")
            for v in (v1, v2):
                r = subprocess.run(run + ["--video", str(v)], capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertIn("flashcheck", r.stdout)
            self.assertEqual(fw.probe_video(v1)["frames"], 10)
            rec = json.loads(v1.with_suffix(".json").read_text())
            self.assertEqual(rec["params"]["palette"], "fire")
            self.assertEqual(rec["animation"]["frames"], 10)
            self.assertTrue(rec["animation"]["flash"]["pass"])
            for i in range(10):
                f = f"f_{i:05d}.png"
                self.assertEqual(Path(d, "a_frames", f).read_bytes(), Path(d, "b_frames", f).read_bytes())


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
