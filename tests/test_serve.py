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
import urllib.error
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
# 0.5.0 GPU deep in the explorer: Mandelbrot 1e-30 (tests/test_deep.py DEEP30)
DEEP_HASH = ("f=mandelbrot&cx=-0.74365672019314946715627157509078125&cy=0.13182842578661420159801990936546875"
             "&w=1e-30&rot=0&it=3000&bail=256&den=0.02&ph=0&pa=0.5,0.5,0.5,0.5,0.5,0.5,1,1,1,0,0.33,0.67&sz=64x48")

# 0.11.0 progressive preview: the 1e-30 view at 320x240 (bars set from measurement below)
PREVIEW_HASH = DEEP_HASH.replace("sz=64x48", "sz=320x240")
# Measured 2026-11-15 (Edge, 1e-10 and 1e-30, pan 24x16 px and zoom x0.5): coarse preview vs exact over
# the exact frame block-sampled 1.03-1.04 (so the coarse error is the downsampling alone); full-res
# preview (old orbit, offset) vs exact mean 0.188-0.232 levels, 0.23-0.28% pixels off by > 8 levels.
PREVIEW_COARSE_BAR = 1.25
PREVIEW_FULL_BAR = 0.5


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

    def test_orbit_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            srv = fw_serve.make_server("127.0.0.1", 0, d)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            try:
                def post(h):
                    req = urllib.request.Request(base + "/orbit", json.dumps({"hash": h}).encode(),
                                                 {"Content-Type": "application/json"})
                    return urllib.request.urlopen(req, timeout=60)
                u = json.loads(post(DEEP_HASH).read())
                self.assertEqual((u["w"], u["h"], u["precision"], u["julia"]), (64, 48, "df", 0))
                self.assertEqual(len(base64.b64decode(u["orbit"])), 16 * (u["last"] + 1))
                for bad in (DEEP_HASH.replace("f=mandelbrot", "f=tricorn"), DEEP_HASH.replace("w=1e-30", "w=1e-70"),
                            DEEP_HASH.replace("it=3000", "it=900000")):
                    with self.assertRaises(urllib.error.HTTPError) as cm:
                        post(bad)
                    self.assertEqual(cm.exception.code, 400)
            finally:
                srv.shutdown()
                srv.server_close()
        self.assertNotIn("/*DEEPFRAG*/", fw_serve.page_html())

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

    def test_page_gpu_deep(self):
        from decimal import Decimal, getcontext
        from PIL import Image
        from playwright.sync_api import sync_playwright
        import fw_gpudeep
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
                page.goto(f"http://127.0.0.1:{srv.server_address[1]}/#" + DEEP_HASH)
                page.wait_for_function("window.fw !== undefined && fw.deep.draws >= 1 && !fw.deep.busy", timeout=60000)
                self.assertTrue(page.evaluate("fw.deep.ok"))
                self.assertIn("GPU deep", page.evaluate("document.getElementById('prec').textContent"))
                canvas = page.evaluate("document.getElementById('cv').toDataURL('image/png')")
                shot = np.asarray(Image.open(io.BytesIO(base64.b64decode(canvas.split(",", 1)[1]))).convert("RGB"))
                # zoom by script: the centre keeps exact decimal digits and the deep shader redraws
                page.evaluate("fw.zoomAt(10, 20, 0.5); fw.setHash('#' + fw.hashOf())")
                page.wait_for_function("fw.deep.draws >= 2 && !fw.deep.busy && fw.deep.hash === fw.hashOf()", timeout=60000)
                st = page.evaluate("fw.state")
                br.close()
            finally:
                pw.stop()
                srv.shutdown()
                srv.server_close()
        ref = fw_gpudeep.render_array(fw.normalise(fw_serve.hash_to_recipe(DEEP_HASH)))
        self.assertEqual(shot.shape, ref.shape)
        dd = diff(shot, ref)
        print(f" page GPU deep vs fw_gpudeep: {dd:.3f}", end="")
        self.assertLess(dd, 0.5)
        getcontext().prec = 80
        w = Decimal("1e-30")
        ex = Decimal("-0.74365672019314946715627157509078125") + (Decimal(10) + Decimal("0.5") - 32) * w / 64 * Decimal("0.5")
        ey = Decimal("0.13182842578661420159801990936546875") + (24 - Decimal(20) - Decimal("0.5")) * w / 64 * Decimal("0.5")
        self.assertLess(abs(Decimal(st["cx"]) - ex), w * Decimal("1e-12"))
        self.assertLess(abs(Decimal(st["cy"]) - ey), w * Decimal("1e-12"))
        self.assertEqual(Decimal(st["w"]), Decimal("5e-31"))
        getcontext().prec = 28


    def test_page_progressive_preview(self):
        # 0.11.0: a deep pan or zoom redraws at once from the previous reference orbit (coarse, one pixel
        # per 4x4 block), then the exact orbit swaps in; a second move while one is pending aborts it.
        from playwright.sync_api import sync_playwright
        hashes = {"1e-10": PREVIEW_HASH.replace("w=1e-30", "w=1e-10"), "1e-30": PREVIEW_HASH}
        moves = {"pan": "fw.pan(24, -16)", "zoom": "fw.zoomAt(200, 150, 0.5)"}
        res = {}
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
                exact = "fw.deep.draws >= %d && !fw.deep.busy && fw.deep.hash === fw.hashOf()"

                def move(h, js, div):
                    """From the exact view h, apply js; return (preview pixels, preview ms, exact pixels, exact ms)."""
                    page.evaluate("fw.deep.noPreview = %s; fw.deep.previewDiv = %d; fw.setHash('#%s')"
                                  % ("true" if div == 0 else "false", max(div, 1), h))
                    page.wait_for_function(exact % (page.evaluate("fw.deep.draws") + 0) + " && fw.hashOf() === '%s'" % h,
                                           timeout=60000)
                    n = page.evaluate("fw.deep.draws")
                    pv = page.evaluate("() => { %s; fw.setHash('#' + fw.hashOf());"
                                       " return { px: fw.pixels(), t: fw.deep.tPreview }; }" % js)
                    page.wait_for_function(exact % (n + 1), timeout=60000)
                    ex = page.evaluate("({ px: fw.pixels(), t: fw.deep.tExact })")
                    a, b = (np.frombuffer(base64.b64decode(x["px"]), np.uint8).reshape(-1, 4)[:, :3] for x in (pv, ex))
                    return a, pv["t"], b, ex["t"]

                for depth, h in hashes.items():
                    page.goto(f"http://127.0.0.1:{srv.server_address[1]}/#" + h)
                    page.wait_for_function("window.fw !== undefined && " + exact % 1, timeout=60000)
                    for name, js in moves.items():
                        _, _, _, before = move(h, js, 0)        # preview off: first pixel = exact draw
                        a4, after, b, _ = move(h, js, 4)        # default coarse preview
                        a1, after1, b1, _ = move(h, js, 1)      # full resolution preview
                        self.assertGreater(after, 0, f"no preview drawn at {depth} {name}")
                        # floor for a 4x4-block preview: the exact frame sampled at block centres, upscaled
                        e = b.reshape(240, 320, 3)
                        blk = np.repeat(np.repeat(e[1::4, 1::4], 4, 0), 4, 1).reshape(-1, 3)
                        res[(depth, name)] = (before, after, after1, diff(a4, b) / diff(blk, b), diff(a1, b1),
                                              float((np.abs(a1.astype(int) - b1.astype(int)).max(1) > 8).mean()))
                    # cancel: two moves back to back; the first request is aborted and the view ends exact
                    page.evaluate("fw.setHash('#%s')" % h)
                    page.wait_for_function(exact % 1 + " && fw.hashOf() === '%s'" % h, timeout=60000)
                    n, ab = page.evaluate("[fw.deep.draws, fw.deep.aborted]")
                    page.evaluate("() => { fw.pan(3, 0); fw.setHash('#' + fw.hashOf());"
                                  " fw.pan(3, 0); fw.setHash('#' + fw.hashOf()); }")
                    page.wait_for_function(exact % (n + 1), timeout=60000)
                    self.assertEqual(page.evaluate("fw.deep.aborted"), ab + 1)
                    self.assertEqual(page.evaluate("fw.deep.draws"), n + 1)
                br.close()
            finally:
                pw.stop()
                srv.shutdown()
                srv.server_close()
        for (depth, name), (before, after, after1, d4, d1, far) in res.items():
            print(f" | {depth} {name}: first pixel {before:.0f} -> {after:.0f} ms (full-res preview {after1:.0f}),"
                  f" coarse diff / block floor {d4:.2f} full {d1:.3f}, full >8 levels {far:.2%}", end="")
        for (depth, name), (before, after, after1, d4, d1, far) in res.items():
            self.assertLess(after, before)
            self.assertLess(d4, PREVIEW_COARSE_BAR)
            self.assertLess(d1, PREVIEW_FULL_BAR)

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


class StopPaletteHashTests(unittest.TestCase):
    """0.7.0: stop palettes and rotation travel through the share hash."""

    def test_stops_round_trip(self):
        h = ("f=mandelbrot&cx=-0.75&cy=0&w=3.5&rot=30&it=300&bail=256&den=0.02&ph=0"
             "&ps=0:000764,0.16:206bcb,0.42:edffff,1:000764&sz=320x240")
        r = fw_serve.hash_to_recipe(h)
        self.assertEqual(r["palette"]["type"], "stops")
        self.assertEqual(r["palette"]["stops"][1], [0.16, "#206bcb"])
        self.assertEqual(r["view"]["rotation_deg"], 30.0)
        self.assertEqual(fw_serve.recipe_to_hash(r), h)
        ultra = fw.normalise(fw.default_recipe())
        ultra["palette"] = "ultra"
        self.assertIn("&ps=0:000764,", fw_serve.recipe_to_hash(ultra))
        with self.assertRaises(ValueError):
            fw_serve.hash_to_recipe(h.replace("ps=0:000764,", "ps=0:07,"))

    @unittest.skipUnless(BROWSER, "Playwright with msedge or chrome not available")
    def test_page_draws_stop_palette_and_rotation_like_numpy(self):
        from PIL import Image
        from playwright.sync_api import sync_playwright
        h = ("f=mandelbrot&cx=-0.6&cy=0.1&w=2.8&rot=30&it=300&bail=256&den=0.02&ph=0"
             "&ps=0:000764,0.16:206bcb,0.42:edffff,0.64:ffaa00,0.86:000200,1:000764&sz=320x240")
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
                page.goto(f"http://127.0.0.1:{srv.server_address[1]}/#" + h)
                page.wait_for_function("window.fw !== undefined")
                page.wait_for_timeout(300)
                canvas = page.evaluate("document.getElementById('cv').toDataURL('image/png')")
                shot = np.asarray(Image.open(io.BytesIO(base64.b64decode(canvas.split(",", 1)[1]))).convert("RGB"))
                ref = fw.render_array(fw.normalise(fw_serve.hash_to_recipe(h)))
                dd = diff(ref, shot)
                print(f"  page stops+rot30 vs numpy: {dd:.3f}")
                self.assertLess(dd, PAGE_BAR)
                self.assertIn("ps=", page.evaluate("location.hash"))
                page.keyboard.press("]")
                page.wait_for_timeout(200)
                self.assertIn("rot=45", page.evaluate("location.hash"))
                self.assertEqual(page.evaluate("document.getElementById('rot').value"), "45")
                br.close()
            finally:
                pw.stop()
                srv.shutdown()
                srv.server_close()


if __name__ == "__main__":
    unittest.main()
