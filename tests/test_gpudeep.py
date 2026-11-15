"""Proof bars for fw_gpudeep.py (GPU perturbation, browser route). Run: python -m unittest discover -s tests -v

Browser tests skip cleanly without Playwright and a system Edge or Chrome.
Measured 2026-11-14 on an RTX 5060 Ti (ANGLE D3D11), see TESTS.md T-20261114-16. The GPU deltas are
float32, so escape counts of chaotic boundary pixels drift from the float64 CPU route; a NumPy float32
copy of the same algorithm drifts from CPU float64 by the same amount, so the drift is float32 rounding,
not a shader error. It is scattered noise: the largest connected block of mismatched pixels stays small.
0.5.0 (T-20261114-17): double-float deltas (deep_df.frag) are the default and cut the mismatch 10-40x;
float32 stays behind --gpu-precision float32 and is tested in Float32Gpu.
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
from test_deep import DEEP30, JDEEP30, jrecipe, largest_blob, recipe  # noqa: E402

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

    def test_df_split(self):
        hi, lo = fw_gpudeep._df(0.1)
        self.assertEqual(hi + lo, float(np.float32(hi)) + float(np.float32(lo)))
        self.assertLess(abs((hi + lo) - 0.1), 1e-15)

    def test_df_uniforms(self):
        r = recipe(DEEP50[0], DEEP50[1], 16, 8, 500)
        u, f = fw_gpudeep.uniforms(r, "df"), fw_gpudeep.uniforms(r, "float32")
        self.assertEqual(u["tile"], fw_gpudeep.TILE_ROWS_DF)
        self.assertGreater(u["T"], f["T"])           # converts at 1e-20 instead of 1e-30
        self.assertLessEqual(u["T"], fw_gpudeep.W_MAX)
        orb = np.frombuffer(__import__("base64").b64decode(u["orbit"]), np.float32).reshape(-1, 4)
        self.assertEqual(len(orb), u["last"] + 1)
        self.assertTrue(np.all(np.abs(orb[1:, 2]) <= np.abs(orb[1:, 0]) * 2.0 ** -23 + 1e-45))
        with self.assertRaises(ValueError):
            fw_gpudeep.frag_source("half")

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

    # double-float (default): measured 64 px mismatch 0.05% / 0.27% / 0.49% / Julia 1.03%, blobs 1
    def test_1e6_matches_cpu(self):
        frac, blob, rgb = self._vs_cpu(recipe(SHALLOW, "1e-6", 64, 64, 2000))
        self.assertLess(frac, 0.01)
        self.assertLessEqual(blob, 3)
        self.assertLess(rgb, 1.0)

    def test_1e30_matches_cpu(self):
        frac, blob, rgb = self._vs_cpu(recipe(DEEP30[0], DEEP30[1], 64, 64, 3000))
        self.assertLess(frac, 0.015)  # float32 deltas: 0.087
        self.assertLessEqual(blob, 3)
        self.assertLess(rgb, 1.5)

    def test_1e50_scaled_delta(self):
        frac, blob, rgb = self._vs_cpu(recipe(DEEP50[0], DEEP50[1], 64, 64, 5000))
        self.assertLess(frac, 0.02)   # float32 deltas: 0.120
        self.assertLessEqual(blob, 3)
        self.assertLess(rgb, 2.0)

    def test_julia_1e30(self):
        frac, blob, _ = self._vs_cpu(jrecipe(JDEEP30[0], JDEEP30[1], 64, 64, 3000))
        self.assertLess(frac, 0.03)   # float32 deltas: 0.186
        self.assertLessEqual(blob, 4)

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
            self.assertEqual(rec["render"]["precision"], "decimal+double-float")
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


@unittest.skipUnless(BROWSER, "Playwright with msedge or chrome not available")
class Float32Gpu(unittest.TestCase):
    """--gpu-precision float32 (0.3.0 shader): faster, float32 noise, no glitch blobs."""

    def test_1e30_float32_flag(self):
        import fw_deep
        r = recipe(DEEP30[0], DEEP30[1], 64, 64, 3000)
        g = fw_gpudeep.GpuDeep("float32")
        try:
            _, _, ng, _ = g.escape(r)
        finally:
            g.close()
        _, _, nc = fw_deep.escape_perturb(r, {})
        wrong = nc != ng
        self.assertLess(wrong.mean(), 0.15)  # measured 0.087, blob 6 (64 px)
        self.assertLessEqual(largest_blob(wrong), 12)

    def test_cli_float32_flag(self):
        with tempfile.TemporaryDirectory() as d:
            src, out = Path(d, "in.json"), Path(d, "o.png")
            src.write_text(json.dumps(recipe(DEEP30[0], DEEP30[1], 32, 24, 3000)), encoding="utf-8")
            res = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "render", str(src), "-o", str(out),
                                  "--deep", "--route", "browser", "--gpu-precision", "float32"], capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads(out.with_suffix(".json").read_text())["render"]["precision"], "decimal+float32")


if __name__ == "__main__":
    unittest.main()
