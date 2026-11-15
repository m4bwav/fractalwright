"""Proof bars for the explorer (fw_serve.py, scripts/page/). Run: python -m unittest discover -s tests -v

Browser tests need Playwright and system Edge (or Chrome); they skip cleanly without them.
Measured 2026-11-14 (numpy 2.5.2, Python 3.14.6, Edge headless on ANGLE D3D11), see TESTS.md T-20261114-6:
browser route vs NumPy, 320x240 full views, 300 iterations, mean abs diff per channel:
mandelbrot 0.144, julia 0.023, burning-ship 2.726 (NumPy float32 itself: 2.628), tricorn 0.052,
multibrot-3 0.148 (bar 1.0; burning ship 3.0). Page zoomed by script, exported, rendered by NumPy
from the recipe: 0.251 (bar 1.5).
"""
import base64
import io
import json
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fw  # noqa: E402
import fw_serve  # noqa: E402

FULL = {
    "mandelbrot": "f=mandelbrot&cx=-0.75&cy=0&w=3.5&rot=0&it=300&bail=256&den=0.02&ph=0&pa=0.5,0.5,0.5,0.5,0.5,0.5,1,1,1,0,0.33,0.67&sz=320x240",
    "julia": "f=julia&cx=0&cy=0&w=3.2&rot=0&it=300&bail=256&kr=-0.123&ki=0.745&den=0.02&ph=0&pa=0.5,0.3,0.1,0.5,0.4,0.2,1,1,1,0,0.1,0.2&sz=320x240",
    "burning-ship": "f=burning-ship&cx=-0.45&cy=-0.5&w=3.6&rot=0&it=300&bail=256&den=0.02&ph=0&pa=0.5,0.5,0.5,0.5,0.5,0.5,1,1,1,0,0.33,0.67&sz=320x240",
    "tricorn": "f=tricorn&cx=-0.3&cy=0&w=4&rot=0&it=300&bail=256&den=0.02&ph=0&pa=0.2,0.4,0.6,0.2,0.3,0.4,1,1,1,0.3,0.2,0.1&sz=320x240",
    "multibrot": "f=multibrot&cx=0&cy=0&w=3.2&rot=0&it=300&bail=256&pw=3&den=0.02&ph=0&pa=0.5,0.5,0.5,0.5,0.5,0.5,1,1,1,0,0.33,0.67&sz=320x240",
}
BROWSER_BAR = 1.0   # design.md pass bar for any GPU route
# Burning ship: abs() folds amplify float32 rounding. NumPy run in float32 differs from
# NumPy float64 by 2.63 on this view, the GPU by 2.73: a precision limit, not a shader error.
SHIP_BAR = 3.0
PAGE_BAR = 1.5


def _browser_ok():
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    ok, _ = fw_serve.probe_browser()
    return ok


BROWSER = _browser_ok()


def diff(a, b):
    return float(np.abs(a.astype(int) - b.astype(int)).mean())


class ServerTests(unittest.TestCase):
    def test_refuses_non_loopback(self):
        for host in ("0.0.0.0", "192.168.1.5", "example.com", ""):
            with self.assertRaises(ValueError):
                fw_serve.make_server(host, 0)
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "serve", "--host", "0.0.0.0", "--port", "0"],
                           capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 2)
        self.assertIn("refusing", r.stderr)

    def test_serves_page_and_export(self):
        with tempfile.TemporaryDirectory() as d:
            srv = fw_serve.make_server("127.0.0.1", 0, d)
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            try:
                base = f"http://127.0.0.1:{srv.server_address[1]}"
                html = urllib.request.urlopen(base + "/").read().decode("utf-8")
                self.assertIn("webgl2", html)
                self.assertIn("uniform int u_formula", html)  # shader inlined
                self.assertNotIn("/*FRAG*/", html)
                req = urllib.request.Request(base + "/export", json.dumps({"hash": FULL["julia"]}).encode(),
                                             {"Content-Type": "application/json"})
                p = Path(json.loads(urllib.request.urlopen(req).read())["path"])
                self.assertEqual(p.parent, Path(d))
                self.assertEqual(fw_serve.recipe_to_hash(json.loads(p.read_text(encoding="utf-8"))), FULL["julia"])
                small = FULL["mandelbrot"].replace("320x240", "64x48")
                req = urllib.request.Request(base + "/render", json.dumps({"hash": small}).encode(),
                                             {"Content-Type": "application/json"})
                res = urllib.request.urlopen(req)
                self.assertEqual(res.headers["X-Route"], "numpy")
                self.assertEqual(res.read()[:8], b"\x89PNG\r\n\x1a\n")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_hash_round_trip(self):
        deep = ("f=mandelbrot&cx=-0.743643887037158704752191506114774&cy=0.131825904205311970493132056385139"
                "&w=1e-7&rot=12.5&it=2000&bail=256&den=0.00001&ph=0.25&pa=0.5,0.5,0.5,0.5,0.5,0.5,1,1,1,0,0.33,0.67&sz=1920x1080")
        for h in list(FULL.values()) + [deep]:
            r = fw_serve.hash_to_recipe("http://127.0.0.1:8765/#" + h)
            self.assertEqual(fw_serve.recipe_to_hash(r), h)
            again = json.loads(json.dumps(r))  # through a JSON file and back
            self.assertEqual(fw_serve.recipe_to_hash(again), h)
        self.assertEqual(fw_serve.hash_to_recipe(deep)["view"]["centre"][0], "-0.743643887037158704752191506114774")

    def test_export_cli(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.json"
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "export", "#" + FULL["tricorn"], "-o", str(out)],
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(fw_serve.recipe_to_hash(json.loads(out.read_text(encoding="utf-8"))), FULL["tricorn"])
            bad = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "export", "#f=nope&cx=0"],
                                 capture_output=True, text=True, timeout=60)
            self.assertEqual(bad.returncode, 2)

    def test_precision_routing(self):
        r = fw.normalise(fw_serve.hash_to_recipe(FULL["mandelbrot"]))
        self.assertTrue(fw_serve.float32_ok(r))
        r = fw.load_recipe("seahorse")  # width 1e-4
        r["size"]["w"], r["size"]["h"] = 320, 240
        self.assertFalse(fw_serve.float32_ok(fw.normalise(r)))


@unittest.skipUnless(BROWSER, "Playwright with msedge or chrome not available")
class BrowserTests(unittest.TestCase):
    def test_browser_route_matches_numpy(self):
        b = fw_serve.Browser()
        try:
            for name, h in FULL.items():
                r = fw.normalise(fw_serve.hash_to_recipe(h))
                d = diff(b.render(r), fw.render_array(r))
                print(f"\n  browser vs numpy {name}: {d:.3f}", end="")
                self.assertLess(d, SHIP_BAR if name == "burning-ship" else BROWSER_BAR, name)
        finally:
            b.close()

    def test_deep_view_routes_to_gpu_perturbation(self):
        # 0.3.0: a Mandelbrot view too deep for plain float32 goes to GPU perturbation, not numpy
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "s.png"
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "render", "seahorse", "--route", "browser",
                                "--size", "96x64", "--iter", "300", "-o", str(out)], capture_output=True, text=True, timeout=300)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("browser deep route", r.stdout)
            rec = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(rec["render"]["route"], "browser-perturbation")
            out2 = Path(d) / "m.png"
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "render", "mandelbrot-full", "--route", "browser",
                                "--size", "96x64", "-o", str(out2)], capture_output=True, text=True, timeout=300)
            self.assertEqual(json.loads(out2.with_suffix(".json").read_text(encoding="utf-8"))["render"]["route"], "browser")

    def test_page_zoom_export_render(self):
        from PIL import Image
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as d:
            srv = fw_serve.make_server("127.0.0.1", 0, d)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            pw = sync_playwright().start()
            try:
                br = None
                for ch in ("msedge", "chrome"):
                    try:
                        br = pw.chromium.launch(channel=ch, headless=True, args=fw_serve.BROWSER_ARGS)
                        break
                    except Exception:  # noqa: BLE001
                        pass
                page = br.new_page()
                page.goto(f"http://127.0.0.1:{srv.server_address[1]}/#" + FULL["mandelbrot"])
                page.wait_for_function("window.fw !== undefined")
                page.evaluate("fw.zoomAt(200, 90, 0.25); fw.pan(-30, 12); fw.setHash('#' + fw.hashOf())")
                h = page.evaluate("location.hash")
                self.assertNotEqual(h[1:], FULL["mandelbrot"])
                path = Path(page.evaluate("fw.exportRecipe().then(j => j.path)"))
                canvas = page.evaluate("document.getElementById('cv').toDataURL('image/png')")
                shot = np.asarray(Image.open(io.BytesIO(base64.b64decode(canvas.split(",", 1)[1]))).convert("RGB"))
                rec = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(fw_serve.recipe_to_hash(rec), h[1:])
                out = Path(d) / "from_recipe.png"
                r = subprocess.run([sys.executable, str(ROOT / "scripts" / "fw.py"), "render", str(path), "-o", str(out)],
                                   capture_output=True, text=True, timeout=300)
                self.assertEqual(r.returncode, 0, r.stderr)
                img = np.asarray(Image.open(out).convert("RGB"))
                self.assertEqual(img.shape, shot.shape)
                dd = diff(img, shot)
                print(f"\n  page canvas vs numpy from exported recipe: {dd:.3f}", end="")
                self.assertLess(dd, PAGE_BAR)
                br.close()
            finally:
                pw.stop()
                srv.shutdown()
                srv.server_close()


STROBE_JS = """() => {
  const A = { formula: 0, cx: 10, cy: 0, w: 1, k: [0, 0], maxit: 50, phase: 0, density: 0.02 };   // escapes at once: bright
  const B = { formula: 0, cx: 0, cy: 0, w: 0.01, k: [0, 0], maxit: 50, phase: 0, density: 0.02 };  // inside the set: black
  const raw = [], lim = [];
  for (let i = 0; i < 300; i++) { draw(i % 2 ? A : B); raw.push(meanLum()); }
  for (let i = 0; i < 300; i++) { limitedDraw(i % 2 ? A : B, i * 1000 / 60); lim.push(meanLum()); }
  return { raw, lim, damped: FL.damped };
}"""


@unittest.skipUnless(BROWSER, "Playwright with msedge or chrome not available")
class TestAudioPageLimiter(unittest.TestCase):
    def test_js_limiter_holds_strobe_to_three_per_second(self):
        # Synthetic 30 Hz strobe (two parameter sets alternating every frame, 5 s at a simulated 60 fps) through
        # the page's own limitedDraw. Bar: <= 3 swings in any 1 s window of what was shown. T-20261114-13.
        from playwright.sync_api import sync_playwright
        with tempfile.TemporaryDirectory() as d, sync_playwright() as pw:
            p = Path(d) / "audio.html"
            p.write_text(fw_serve.audio_page_html(), encoding="utf-8")
            b = None
            for ch in ("msedge", "chrome"):
                try:
                    b = pw.chromium.launch(channel=ch, headless=True, args=fw_serve.BROWSER_ARGS)
                    break
                except Exception:  # noqa: BLE001
                    continue
            page = b.new_page()
            page.goto(p.as_uri())
            page.wait_for_function("typeof limitedDraw === 'function'")
            res = page.evaluate(STROBE_JS)
            b.close()
        raw, lim = np.array(res["raw"]), np.array(res["lim"])
        self.assertGreater(raw.max() - raw.min(), 0.1)    # the input really strobes
        per_s = lambda L: int(fw._per_second_max(fw.swing_walk(L)[:, None], 60)[0])
        self.assertGreater(per_s(raw), 3)                  # measured 60 (every frame swings)
        self.assertLessEqual(per_s(lim), 3)                # measured: see TESTS.md
        self.assertGreater(res["damped"], 0)
        print(f"js limiter: raw {per_s(raw)} swings/s, limited {per_s(lim)}, damped {res['damped']}")


if __name__ == "__main__":
    unittest.main()
