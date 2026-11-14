"""Proof bars for fw_deep.py (perturbation). Run: python -m unittest discover -s tests -v

Measured 2026-11-14 (numpy 2.5.2, Python 3.14.6), see TESTS.md T-20261114-5:
1e-6 view 96x64 mean diff 0.405 vs plain NumPy; 1e-20 and 1e-30 views 24x16
match direct Decimal iteration on 384/384 pixels (max count error 0).
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fw  # noqa: E402
import fw_deep  # noqa: E402

# Found by zooming 10x per step towards a 90th-percentile escaping pixel
# from the seahorse view; every pixel escapes, counts 1164-2815.
DEEP20 = (["-0.7436567201931494671546875", "0.1318284257866142015953125"], "1e-20")
DEEP30 = (["-0.74365672019314946715627157509078125", "0.13182842578661420159801990936546875"], "1e-30")


def recipe(centre, width, w, h, it):
    return fw.normalise(fw._merge(fw.default_recipe(), {
        "view": {"centre": centre, "width": width}, "size": {"w": w, "h": h}, "params": {"max_iter": it}}))


def largest_blob(mask):
    seen = np.zeros_like(mask)
    best = 0
    for y, x in zip(*np.nonzero(mask)):
        if seen[y, x]:
            continue
        stack, size = [(y, x)], 0
        seen[y, x] = True
        while stack:
            cy, cx = stack.pop()
            size += 1
            for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                if 0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    stack.append((ny, nx))
        best = max(best, size)
    return best


class TestDeep(unittest.TestCase):
    def test_matches_plain_at_moderate_zoom(self):
        r = recipe(["-0.743643887037158704752191506114774", "0.131825904205311970493132056385139"], "1e-6", 96, 64, 2000)
        diff = np.abs(fw.render_array(r).astype(int) - fw_deep.render_array(r)).mean()
        self.assertLess(diff, 1.0)  # measured 0.405

    def _deep_vs_direct(self, view):
        r = recipe(view[0], view[1], 24, 16, 3000)
        st = {}
        _, _, n = fw_deep.escape_perturb(r, st)
        d = fw_deep.direct_counts(r)
        wrong = n != d
        self.assertGreaterEqual(1 - wrong.mean(), 0.99)  # measured 1.0
        self.assertLessEqual(largest_blob(wrong), 4)
        self.assertGreater((n > 0).mean(), 0.9)  # not a trivial all-inside view
        return st

    def test_deep_1e20_matches_decimal(self):
        st = self._deep_vs_direct(DEEP20)
        # the reference escapes early (1358 < counts), so every pixel rebases
        self.assertEqual(st["rebased_pixels"], 384)
        self.assertGreater(st["rebases"], 0)

    def test_deep_1e30_matches_decimal(self):
        self._deep_vs_direct(DEEP30)

    def test_deterministic(self):
        r = recipe(DEEP20[0], DEEP20[1], 48, 32, 3000)
        self.assertTrue(np.array_equal(fw_deep.render_array(r), fw_deep.render_array(r)))

    def test_too_deep_refused(self):
        with self.assertRaises(ValueError):
            fw_deep.escape_perturb(recipe(["0", "0"], "1e-300", 4, 4, 10))

    def test_cli_routes_deep(self):
        with tempfile.TemporaryDirectory() as d:
            rp = Path(d) / "deep.json"
            rp.write_text(json.dumps(recipe(DEEP20[0], DEEP20[1], 32, 24, 3000)), encoding="utf-8")
            out = Path(d) / "o.png"
            res = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "render", str(rp), "-o", str(out)],
                                 capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("rebased 768 pixels", res.stdout)
            rec = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(rec["render"]["route"], "numpy-perturbation")


if __name__ == "__main__":
    unittest.main()
