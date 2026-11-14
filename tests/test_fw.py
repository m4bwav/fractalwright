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


# ---------------------------------------------------------------- batch 2 (measure v2, identify)
# Measured 2026-11-14 (numpy 2.5.2, Python 3.14.6). Every tolerance below is the
# measured error with headroom; the numbers are repeated in TESTS.md T-20261114-3.

def spiral(n=1024, turns=40):
    th = np.linspace(0, turns * 2 * math.pi, 400000)
    rr = th / th.max() * 0.48
    m = np.zeros((n, n), bool)
    m[((0.5 + rr * np.sin(th)) * (n - 1)).astype(int), ((0.5 + rr * np.cos(th)) * (n - 1)).astype(int)] = True
    return m


def random_discs(n=1024, k=300, rad=12, seed=1):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:n, 0:n]
    m = np.zeros((n, n), bool)
    for cx, cy in rng.uniform(0, n, (k, 2)):
        m |= (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad
    return m


def julia_recipe(c):
    return fw.normalise(fw._merge(fw.default_recipe(), {"formula": "julia", "params": {"c": list(c)}}))


class BoxAnalysis(unittest.TestCase):
    def test_koch_fractal_verdict(self):
        # measured: D error -0.0025, 2.23 decades, local-slope spread 0.058 (4096 px)
        r = fw.box_analysis(koch(4096, 8))
        self.assertAlmostEqual(r["dimension"], KOCH, delta=0.02)
        self.assertGreaterEqual(len(r["sizes"]), 15)
        self.assertTrue(r["verdict"].startswith("fractal-like"), r["verdict"])

    def test_under_two_decades_refuses_fractal(self):
        # measured: Koch at 2048 px fits 1.93 decades (D error -0.0037): descriptor only
        r = fw.box_analysis(koch(2048))
        self.assertLess(r["decades"], 2)
        self.assertTrue(r["verdict"].startswith("descriptor only"), r["verdict"])

    def test_chaos_sierpinski_offsets(self):
        # measured: -0.0146 at 2048 px with 8 seeded offsets, spread 0.080
        m = sierpinski_chaos(2048)
        r = fw.box_analysis(m)
        self.assertAlmostEqual(r["dimension"], SIERPINSKI, delta=0.03)
        self.assertEqual(r, fw.box_analysis(m))  # seeded offsets: repeatable

    def test_spiral_decoy(self):
        # measured: local slope 0.95..1.96 (spread 1.017) at 2048 px, 80 turns
        r = fw.box_analysis(spiral(2048, 80))
        self.assertGreater(r["decades"], 2)
        self.assertTrue(r["verdict"].startswith("not fractal"), r["verdict"])

    def test_random_disc_decoy(self):
        # measured: local slope 1.25..1.78 (spread 0.529) at 2048 px, 1200 discs of radius 12
        r = fw.box_analysis(random_discs(2048, 1200, 12))
        self.assertGreater(r["decades"], 2)
        self.assertTrue(r["verdict"].startswith("not fractal"), r["verdict"])

    def test_line_is_ordinary(self):
        # measured: D 0.931 (coarse-box bias), spread 0.280: ordinary set
        r = fw.box_analysis(np.eye(1024, dtype=bool))
        self.assertTrue(r["verdict"].startswith("ordinary"), r["verdict"])

    def test_specks_removed_with_warning(self):
        # measured: 3000 specks drop D to 1.176; the filter removes 2917 and returns 1.2589 (clean 1.2581)
        clean = koch(2048)
        k = clean.copy()
        rng = np.random.default_rng(3)
        k[rng.integers(0, k.shape[0], 3000), rng.integers(0, k.shape[1], 3000)] = True
        r = fw.box_analysis(k)
        self.assertGreater(r["specks_removed"], 2500)
        self.assertTrue(any("specks" in w for w in r["warnings"]))
        self.assertAlmostEqual(r["dimension"], fw.box_analysis(clean)["dimension"], delta=0.005)
        self.assertLess(fw.box_analysis(k, specks=False)["dimension"], KOCH - 0.05)

    def test_dust_keeps_its_points(self):
        # Cantor dust is all isolated pixels at the finest level: not noise
        r = fw.box_analysis(fw.kronecker_mask(fw.KRONECKER["cantor-dust"], 6))
        self.assertEqual(r["specks_removed"], 0)
        self.assertTrue(any("dust" in w for w in r["warnings"]))


class Kronecker(unittest.TestCase):
    def test_exact_with_k_adic_boxes(self):
        # boxes 3^j on a 3^7 grid match the mask exactly
        for name in ("carpet", "vicsek", "cantor-dust"):
            rows = fw.KRONECKER[name]
            m = fw.kronecker_mask(rows, 7)
            r = fw.box_analysis(m, sizes=[3 ** j for j in range(1, 6)], offsets=1, specks=False)
            self.assertAlmostEqual(r["dimension"], fw.kronecker_dimension(rows), delta=1e-9, msg=name)

    def test_general_boxes_bias(self):
        # measured with 16 geometric sizes and offsets (power 7): carpet -0.061, Vicsek -0.053,
        # dust -0.058. Log-periodic lattice bias: grid fractals read low on non-k-adic boxes.
        for name in ("carpet", "vicsek", "cantor-dust"):
            rows = fw.KRONECKER[name]
            D = fw.box_analysis(fw.kronecker_mask(rows, 7))["dimension"]
            self.assertAlmostEqual(D, fw.kronecker_dimension(rows), delta=0.08, msg=name)

    def test_render_preset(self):
        img = fw.render_array(fw.load_recipe("kronecker-carpet"))
        self.assertEqual(img.shape, (729, 729, 3))
        self.assertTrue(np.array_equal(img[..., 0] == 0, fw.kronecker_mask(fw.KRONECKER["carpet"], 6)))

    def test_python_fallback_matches(self):
        r = fw.load_recipe("kronecker-vicsek")
        r["params"]["power"] = 3
        a = fw.render_array(json.loads(json.dumps(r)))
        b = np.frombuffer(b"".join(fw.render_rows_py(json.loads(json.dumps(r)))), np.uint8).reshape(a.shape)
        self.assertTrue(np.array_equal(a, b))


class Lacunarity(unittest.TestCase):
    BIG = ["11111", "10001", "10001", "10001", "11111"]        # one 3x3 hole, 16 ones
    SCATTER = ["01010", "11111", "01010", "11111", "01010"]    # nine single holes, 16 ones

    def test_same_d_different_lacunarity(self):
        # measured (5^5 px): box D 1.656 vs 1.681 (both log16/log5 = 1.7227);
        # Lambda big-hole / scattered at r = 32, 64, 128, 256: 1.14, 1.14, 1.20, 1.32
        a = fw.kronecker_mask(self.BIG, 5)
        b = fw.kronecker_mask(self.SCATTER, 5)
        self.assertEqual(fw.kronecker_dimension(self.BIG), fw.kronecker_dimension(self.SCATTER))
        self.assertAlmostEqual(fw.box_analysis(a)["dimension"], fw.box_analysis(b)["dimension"], delta=0.05)
        la, lb = dict(fw.lacunarity(a)), dict(fw.lacunarity(b))
        for r in (32, 64, 128, 256):
            self.assertGreater(la[r] / lb[r], 1.10, r)
        self.assertGreater(la[256] / lb[256], 1.25)

    def test_filled_square_is_one(self):
        self.assertTrue(all(abs(v - 1) < 1e-12 for _, v in fw.lacunarity(np.ones((256, 256), bool))))


class Similarity(unittest.TestCase):
    def test_moran(self):
        # bisection error about 3e-13
        self.assertAlmostEqual(fw.similarity_dimension([0.5] * 3), SIERPINSKI, delta=1e-9)
        self.assertAlmostEqual(fw.similarity_dimension([0.5, 0.25]), math.log((1 + 5 ** 0.5) / 2) / math.log(2), delta=1e-9)
        self.assertAlmostEqual(fw.similarity_dimension([1 / 3] * 8), math.log(8) / math.log(3), delta=1e-9)


class SelfAffine(unittest.TestCase):
    # Davies-Harte fBm, 2^16 steps, 10 seeds: max |H error| spectral 0.033, semivariogram 0.055
    def test_profile_recovers_h(self):
        for H in (0.3, 0.5, 0.7, 0.8):
            p = fw.profile_analysis(fw.synth_fbm1d(2 ** 16, H, seed=0))
            self.assertAlmostEqual(p["H_spectral"], H, delta=0.045, msg=H)
            self.assertAlmostEqual(p["H_semivariogram"], H, delta=0.07, msg=H)
            self.assertAlmostEqual(p["D_spectral"], 2 - H, delta=0.045, msg=H)

    def test_surface_relations(self):
        # spectral synthesis 1024^2, 4 seeds: radial H max error 0.015, profile cuts 0.021;
        # radial beta minus profile beta = 1 (settles references/06 section 7)
        for H in (0.3, 0.8):
            r = fw.heightmap_analysis(fw.synth_fbm2d(1024, H, seed=0))
            self.assertAlmostEqual(r["H_radial"], H, delta=0.025, msg=H)
            self.assertAlmostEqual(r["H_profiles"], H, delta=0.03, msg=H)
            self.assertAlmostEqual(r["radial_minus_profile"], 1.0, delta=0.06, msg=H)
            self.assertAlmostEqual(r["D_surface"], 3 - H, delta=0.025, msg=H)

    def test_katz_koch_polyline(self):
        # Katz is exact on a Koch polyline (n = 4^L steps, d/L = (3/4)^L); about 1.03 on fBm
        pts = np.array([0.0 + 0j, 1.0 + 0j])
        rot = np.exp(1j * math.pi / 3)
        for _ in range(6):
            a, b = pts[:-1], pts[1:]
            d = (b - a) / 3
            new = np.empty(len(a) * 4 + 1, complex)
            new[0:-1:4], new[1::4], new[2::4], new[3::4] = a, a + d, a + d + d * rot, a + 2 * d
            new[-1] = pts[-1]
            pts = new
        self.assertAlmostEqual(fw.katz_dimension(pts.real, pts.imag), KOCH, delta=1e-9)
        self.assertAlmostEqual(fw.katz_dimension(np.arange(100.0), np.arange(100.0)), 1.0, delta=1e-9)

    def test_box_refused_on_profile(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.txt"
            np.savetxt(f, fw.synth_fbm1d(1024, 0.5))
            out = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "measure", "box", str(f)],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 2)
            self.assertIn("measure profile", out.stderr)


class Identify(unittest.TestCase):
    def test_julia_connectedness(self):
        cases = {("-0.123", "0.745"): True, ("0", "1"): True, ("-1", "0"): True,
                 ("0.4", "0.3"): False, ("-0.8", "0.4"): False}
        for c, want in cases.items():
            self.assertEqual(fw.identify(julia_recipe(c))["features"]["julia_connected"], want, c)

    def test_cardioid_and_bulb_hints(self):
        for c, region in ((("0.1", "0.1"), "main cardioid"), (("-1", "0.1"), "period-2 bulb")):
            self.assertEqual(fw.identify(julia_recipe(c))["features"]["c_region"], region)

    def test_image_mirror_and_no_name_from_d(self):
        r = fw.load_recipe("mandelbrot-full")
        r["size"] = {"w": 320, "h": 240, "supersample": 1}
        out = fw.identify(None, fw.render_array(r))
        self.assertEqual(out["features"]["mirror"]["up-down"], 1.0)
        self.assertIn("box dimension is a descriptor here, not an identification", out["hints"])


class Video(unittest.TestCase):
    """Step D batch 3: sheet, zoom, morph, loop, flashcheck. Small sizes keep it fast."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        cls.env = dict(__import__("os").environ, FW_COMFY_HOSTS="")
        cls.julia = fw.normalise(fw.load_recipe("julia-rabbit"))
        cls.julia["size"] = {"w": 160, "h": 90, "supersample": 1}
        cls.julia["params"]["max_iter"] = 200

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_fw(self, *args):
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), *args],
                             capture_output=True, text=True, env=self.env)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        return out.stdout

    def test_same_recipe_identical_frames(self):
        frames = fw.loop_frames(self.julia, 12, circle=(-0.123, 0.745, 0.02), phase=True)
        a = [hash(fw.render_array(r).tobytes()) for r in frames]
        b = [hash(fw.render_array(r).tobytes()) for r in json.loads(json.dumps(frames))]
        self.assertEqual(a, b)

    def test_loop_seam(self):
        recs = fw.loop_frames(self.julia, 12, circle=(-0.123, 0.745, 0.02), phase=True)
        frames = [fw.render_array(r).astype(float) for r in recs]
        ratio, seam, med = fw.seam_ratio(frames)
        self.assertLessEqual(ratio, 1.25, (seam, med))

    def test_zoom_width_ratio_constant(self):
        base = fw.normalise(fw.load_recipe("mandelbrot-full"))
        recs = fw.zoom_frames(base, 3.5, 0.01, 12, centre_to=[-0.75, 0.1])
        w = [float(r["view"]["width"]) for r in recs]
        ratios = [w[i + 1] / w[i] for i in range(len(w) - 1)]
        self.assertLess(max(ratios) - min(ratios), 1e-9)
        self.assertAlmostEqual(w[-1], 0.01, places=12)

    def test_mp4_frames_fps_and_flashcheck(self):
        for kind, args in (("zoom", ["mandelbrot-full", "--to-width", "0.5", "--to-centre", "-0.75,0.1"]),
                           ("loop", ["julia-rabbit", "--circle", "-0.123,0.745,0.02", "--phase"]),
                           ("morph", ["julia-rabbit", "--path", "-0.123,0.745;-0.8,0.156"])):
            out = self.dir / f"{kind}.mp4"
            self.run_fw(kind, *args, "--size", "160x90", "--iter", "200", "--fps", "12", "--duration", "1",
                        "-o", str(out))
            info = fw.probe_video(out)
            self.assertEqual((info["frames"], info["fps"]), (12, 12.0), kind)
            rec = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(rec["animation"]["fps"], 12)
            self.assertEqual(rec["animation"]["duration_s"], 1.0)
            self.assertIn("no ComfyUI host", rec["notes"][0])
            for src in (out, out.with_name(f"{kind}_frames")):
                res = json.loads(self.run_fw("flashcheck", str(src), "--fps", "12", "--json"))
                self.assertTrue(res["pass"], (kind, src, res))

    def test_flashcheck_catches_strobe(self):
        black, white = np.zeros((9, 16, 3)), np.ones((9, 16, 3))
        res = fw.flash_check([black, white] * 12, 24)
        self.assertFalse(res["pass"])
        self.assertGreater(res["max_swings_per_s"], 3)

    def test_sheet_tiles_and_sidecar(self):
        out = self.dir / "sheet.png"
        self.run_fw("sheet", "julia-rabbit", "--vary", "params.c", "--values", "-0.123:0.745,-0.8:0.156,0:1",
                    "--tile", "160x90", "--iter", "200", "-o", str(out))
        side = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(len(side["tiles"]), 3)
        tile = fw.render_array(side["tiles"][1]["recipe"])
        from PIL import Image
        img = np.asarray(Image.open(out).convert("RGB"))
        self.assertTrue(np.array_equal(img[0:90, 160:320], tile))


if __name__ == "__main__":
    unittest.main()
