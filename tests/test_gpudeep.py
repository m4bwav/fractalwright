"""Proof bars for fw_gpudeep.py (GPU perturbation, browser route). Run: python -m unittest discover -s tests -v

Browser tests skip cleanly without Playwright and a system Edge or Chrome.
Measured 2026-11-14 on an RTX 5060 Ti (ANGLE D3D11), see TESTS.md T-20261114-16. The GPU deltas are
float32, so escape counts of chaotic boundary pixels drift from the float64 CPU route; a NumPy float32
copy of the same algorithm drifts from CPU float64 by the same amount, so the drift is float32 rounding,
not a shader error. It is scattered noise: the largest connected block of mismatched pixels stays small.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fw  # noqa: E402
import fw_gpudeep  # noqa: E402
from test_deep import DEEP30, largest_blob, recipe  # noqa: E402

# Found from DEEP30 by the same 10x-per-step walk towards a 90th-percentile escaping pixel.
DEEP50 = (["-0.743656720193149467156271575090551166063968938893196875",
           "0.131828425786614201598019909365989389326445833333328125"], "1e-50")
SHALLOW = ["-0.743643887037158704752191506114774", "0.131825904205311970493132056385139"]


def _browser_ok():
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    try:
        fw_gpudeep.GpuDeep().close()
        return True
    except Exception:  # noqa: BLE001
        return False


BROWSER = _browser_ok()


class Pure(unittest.TestCase):
    def test_pow2_split(self):
        for s in (1e-3, 1e-33, 1e-62, 3e-69):
            s1, s2 = fw_gpudeep._pow2_split(s)
            self.assertAlmostEqual(s1 * s2 / s, 1.0, places=6)
            self.assertGreater(min(s1, s2), 1.2e-38)  # both normal float32

    def test_supported(self):
        self.assertTrue(fw_gpudeep.supported(recipe(DEEP50[0], DEEP50[1], 8, 8, 100)))
        self.assertFalse(fw_gpudeep.supported(recipe(DEEP50[0], "1e-61", 8, 8, 100)))
        r = recipe(SHALLOW, "1e-6", 8, 8, 100)
        r["formula"] = "burning-ship"
        self.assertFalse(fw_gpudeep.supported(r))


@unittest.skipUnless(BROWSER, "Playwright with msedge or chrome not available")
class Gpu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = fw_gpudeep.GpuDeep()

    @classmethod
    def tearDownClass(cls):
        cls.g.close()

    def _vs_cpu(self, r):
        import fw_deep
        _, _, nc = fw_deep.escape_perturb(r, {})
        _, _, ng, _ = self.g.escape(r)
        wrong = nc != ng
        rgb = np.abs(fw_deep.render_array(r).astype(int) - self.g.render(r)).mean()
        return wrong.mean(), largest_blob(wrong), rgb

    def test_1e6_matches_cpu(self):
        frac, blob, rgb = self._vs_cpu(recipe(SHALLOW, "1e-6", 64, 64, 2000))
        self.assertLess(frac, 0.06)   # measured 0.034, largest blob 5, mean RGB diff 2.34 (64 px)
        self.assertLessEqual(blob, 12)
        self.assertLess(rgb, 4.0)

    def test_1e30_matches_cpu(self):
        frac, blob, rgb = self._vs_cpu(recipe(DEEP30[0], DEEP30[1], 64, 64, 3000))
        self.assertLess(frac, 0.15)   # measured 0.087, blob 6, RGB 5.70 (64 px); float32 NumPy copy 0.091 at 128 px
        self.assertLessEqual(blob, 12)  # noise, no glitch blob
        self.assertLess(rgb, 10.0)

    def test_1e50_scaled_delta(self):
        frac, blob, rgb = self._vs_cpu(recipe(DEEP50[0], DEEP50[1], 64, 64, 5000))
        self.assertLess(frac, 0.18)   # measured 0.120, blob 6, RGB 9.06 (64 px, counts 2781-3653)
        self.assertLessEqual(blob, 12)
        self.assertLess(rgb, 13.0)

    def test_same_recipe_same_pixels(self):
        r = recipe(DEEP30[0], DEEP30[1], 48, 32, 3000)
        self.assertTrue(np.array_equal(self.g.render(r), self.g.render(r)))

    def test_cli_render_deep_browser(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d, "in.json"), Path(d, "o.png")
            src.write_text(json.dumps(recipe(DEEP30[0], DEEP30[1], 32, 24, 3000)), encoding="utf-8")
            res = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "render", str(src), "-o", str(out),
                                  "--deep", "--route", "browser"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            rec = json.loads(out.with_suffix(".json").read_text())
            self.assertEqual(rec["render"]["route"], "browser-perturbation")
            self.assertEqual(Decimal(rec["view"]["width"]), Decimal("1e-30"))

    def test_cli_zoom_browser(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d, "in.json"), Path(d, "z.mp4")
            src.write_text(json.dumps(recipe(DEEP30[0], "1e-20", 32, 24, 3000)), encoding="utf-8")
            res = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "zoom", str(src), "-o", str(out),
                                  "--to-width", "1e-30", "--fps", "4", "--duration", "1", "--route", "browser"],
                                 capture_output=True, text=True)
            self.assertIn(res.returncode, (0, 4), res.stderr)
            self.assertEqual(len(list(Path(d, "z_frames").glob("*.png"))), 4)
            self.assertEqual(json.loads(out.with_suffix(".json").read_text())["animation"]["route"], "browser-perturbation")


if __name__ == "__main__":
    unittest.main()
