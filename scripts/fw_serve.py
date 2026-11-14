"""fractalwright explorer: the WebGL2 page, its 127.0.0.1 server, share hashes and the browser route.

`fw.py serve` and `fw.py export` call into this module, and `fw.py render --route browser`
uses `browser_render`. The page and the browser route load the same shader file,
scripts/page/fractal.frag, so what the page shows is what the route renders.
"""
import base64
import json
import math
import sys
import tempfile
import threading
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

import fw

PAGE_DIR = Path(__file__).resolve().parent / "page"
FRAG = PAGE_DIR / "fractal.frag"
PAGE = PAGE_DIR / "explorer.html"
LOOPBACK = ("127.0.0.1", "localhost", "::1")
# Hash keys in page order (explorer.html KEYS). kr, ki only for julia; pw only for multibrot.
HASH_KEYS = ("f", "cx", "cy", "w", "rot", "it", "bail", "pw", "kr", "ki", "den", "ph", "pa", "sz")
PAGE_FORMULAS = ("mandelbrot", "julia", "burning-ship", "tricorn", "multibrot")
# float32 plain iteration: pixel step relative to max(1, |centre|). Below this the
# picture blocks up (bench: 3.5e4 zoom at 1920 px, rel 5e-8, diff 21). Page uses the same limit.
F32_REL_LIMIT = 1e-6
# Iteration amplifies rounding near the boundary, so small images of deep views fail too:
# width relative to max(1, |centre|) under this goes to numpy (width 1e-4 does; bench diff 21 there).
F32_WIDTH_LIMIT = 1e-3
MAX_EXACT_PIXELS = 4_000_000


# ---------------------------------------------------------------- hash <-> recipe
def parse_hash(h):
    """A share URL, '#...' or bare 'k=v&...' -> ordered dict of the known keys (strings kept verbatim)."""
    h = h.strip()
    if "#" in h:
        h = h.split("#", 1)[1]
    out = {}
    for part in h.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k in HASH_KEYS:
                out[k] = unquote(v)
    if "f" not in out or out["f"] not in PAGE_FORMULAS:
        raise ValueError(f"hash needs f= one of {', '.join(PAGE_FORMULAS)}")
    for k in ("cx", "cy", "w"):
        if k not in out:
            raise ValueError(f"hash is missing {k}=")
    for k, v in out.items():
        if k in ("f", "pa", "sz"):
            continue
        try:
            Decimal(v)
        except InvalidOperation:
            raise ValueError(f"{k}={v!r} is not a number") from None
    return out


def hash_to_recipe(h):
    """Share hash -> recipe dict. Number strings are kept exactly as the page wrote them."""
    d = parse_hash(h)
    r = fw.default_recipe()
    r["formula"] = d["f"]
    r["view"] = {"centre": [d["cx"], d["cy"]], "width": d["w"], "rotation_deg": float(d.get("rot", "0"))}
    p = r["params"]
    p["max_iter"] = int(Decimal(d.get("it", "500")))
    p["bailout"] = float(d.get("bail", "256"))
    p["power"] = int(Decimal(d.get("pw", "2"))) if d["f"] == "multibrot" else 2
    if d["f"] == "julia":
        p["c"] = [d.get("kr", "-0.8"), d.get("ki", "0.156")]
    r["colouring"]["density"] = float(d.get("den", "0.02"))
    r["colouring"]["phase"] = float(d.get("ph", "0"))
    if "pa" in d:
        v = [float(x) for x in d["pa"].split(",")]
        if len(v) != 12:
            raise ValueError("pa= needs 12 numbers: a, b, c, d as r,g,b each")
        r["palette"] = {"type": "cosine", "a": v[0:3], "b": v[3:6], "c": v[6:9], "d": v[9:12]}
    if "sz" in d:
        w, hh = d["sz"].lower().split("x")
        r["size"] = {"w": int(w), "h": int(hh), "supersample": 1}
    r["render"] = {"route": "browser", "precision": "float32"}
    return r


def _js(x):
    """Number -> exactly the string JavaScript String(Number) gives (shortest round trip)."""
    x = float(x)
    if x == 0:
        return "0"
    sign = "-" if x < 0 else ""
    t = Decimal(repr(abs(x))).as_tuple()
    digits = "".join(map(str, t.digits)).rstrip("0") or "0"
    n = len(t.digits) + t.exponent  # value = 0.<digits> * 10**n
    k = len(digits)
    if k <= n <= 21:
        s = digits + "0" * (n - k)
    elif 0 < n <= 21:
        s = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        s = "0." + "0" * (-n) + digits
    else:
        e = n - 1
        s = digits[0] + ("." + digits[1:] if k > 1 else "") + "e" + ("+" if e > 0 else "-") + str(abs(e))
    return sign + s


def recipe_to_hash(r):
    """Recipe -> share hash (no leading '#'). Strings in view and c are used verbatim."""
    f = r["formula"]
    if f not in PAGE_FORMULAS:
        raise ValueError(f"the page draws {', '.join(PAGE_FORMULAS)}, not {f}")
    pal = r.get("palette") or {}
    if isinstance(pal, str):
        pal = fw.PALETTES[pal]
    if pal.get("type") != "cosine":
        raise ValueError("the page uses cosine palettes; this recipe has stops")
    p, c = r["params"], r["colouring"]
    vals = {
        "f": f, "cx": str(r["view"]["centre"][0]), "cy": str(r["view"]["centre"][1]), "w": str(r["view"]["width"]),
        "rot": _js(r["view"].get("rotation_deg", 0) or 0),
        "it": _js(p.get("max_iter", 500)), "bail": _js(p.get("bailout", 256)),
        "pw": _js(p.get("power", 2)),
        "kr": str(p.get("c", ["-0.8", "0.156"])[0]), "ki": str(p.get("c", ["-0.8", "0.156"])[1]),
        "den": _js(c.get("density", 0.02)), "ph": _js(c.get("phase", 0) or 0),
        "pa": ",".join(_js(v) for k in "abcd" for v in pal[k]),
        "sz": f"{r['size']['w']}x{r['size']['h']}",
    }
    keys = [k for k in HASH_KEYS if not ((k in ("kr", "ki") and f != "julia") or (k == "pw" and f != "multibrot"))]
    return "&".join(f"{k}={vals[k]}" for k in keys)


# ---------------------------------------------------------------- precision routing
def float32_rel(r):
    """Pixel step relative to the coordinate size; small means float32 cannot resolve it."""
    px = abs(Decimal(r["view"]["width"])) / (r["size"]["w"] * int(r["size"].get("supersample", 1) or 1))
    big = max(Decimal(1), *(abs(Decimal(x)) for x in r["view"]["centre"]))
    return float(px / big)


def float32_ok(r):
    big = max(Decimal(1), *(abs(Decimal(x)) for x in r["view"]["centre"]))
    wide = abs(Decimal(r["view"]["width"])) / big >= Decimal(str(F32_WIDTH_LIMIT))
    return r["formula"] in PAGE_FORMULAS and wide and float32_rel(r) >= F32_REL_LIMIT


# ---------------------------------------------------------------- shader and page
def uniforms(r, w=None, h=None):
    """Normalised recipe -> the uniform dict explorer.html drawUniforms() takes."""
    w = w or r["size"]["w"]
    h = h or r["size"]["h"]
    p, c, v = r["params"], r["colouring"], r["view"]
    pal = r["palette"]
    u = {"w": w, "h": h, "cx": float(Decimal(v["centre"][0])), "cy": float(Decimal(v["centre"][1])),
         "px": float(Decimal(v["width"])) / w, "rot": math.radians(float(v.get("rotation_deg", 0) or 0)),
         "formula": PAGE_FORMULAS.index(r["formula"]), "power": int(p.get("power", 2)),
         "maxit": int(p["max_iter"]), "bail2": float(p["bailout"]) ** 2,
         "kr": 0.0, "ki": 0.0, "flip": 1 if r["formula"] == "burning-ship" and p.get("flip_y") else 0,
         "density": float(c.get("density", 0.02)), "phase": float(c.get("phase", 0) or 0),
         "inside": fw._hex(c.get("inside", "#000000")),
         "a": [0, 0, 0], "b": [0, 0, 0], "c": [0, 0, 0], "d": [0, 0, 0],
         "paltype": 0, "nstops": 0, "spos": [0.0] * 8, "scol": [0.0] * 24}
    if r["formula"] == "julia":
        u["kr"], u["ki"] = (float(Decimal(x)) for x in p["c"])
    if pal["type"] == "cosine":
        for k in "abcd":
            u[k] = [float(x) for x in pal[k]]
    else:
        stops = pal["stops"][:8]
        u["paltype"], u["nstops"] = 1, len(stops)
        for i, (pos, col) in enumerate(stops):
            u["spos"][i] = float(pos)
            u["scol"][3 * i:3 * i + 3] = fw._hex(col)
    return u


def page_html():
    """The self-contained page: explorer.html with fractal.frag inlined."""
    return PAGE.read_text(encoding="utf-8").replace("/*FRAG*/", FRAG.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- browser route
BROWSER_ARGS = ["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"]


class Browser:
    """Headless system Edge (or Chrome) through Playwright with the explorer page loaded."""

    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        last = None
        for ch in ("msedge", "chrome"):
            try:
                self.b = self.pw.chromium.launch(channel=ch, headless=True, args=BROWSER_ARGS)
                self.channel = ch
                break
            except Exception as e:  # noqa: BLE001
                last = e
        else:
            self.pw.stop()
            raise RuntimeError(f"no msedge or chrome channel: {last}")
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name) / "explorer.html"
        p.write_text(page_html(), encoding="utf-8")
        self.page = self.b.new_page()
        self.page.goto(p.as_uri() + "#f=mandelbrot&cx=-0.75&cy=0&w=3.5&sz=64x48")
        self.page.wait_for_function("window.fw !== undefined")
        self.renderer = self.page.evaluate("fw.renderer()")

    def render(self, r):
        """Normalised recipe -> uint8 HxWx3 (top row first)."""
        import numpy as np
        ss = int(r["size"].get("supersample", 1) or 1)
        w, h = r["size"]["w"] * ss, r["size"]["h"] * ss
        self.page.evaluate("u => fw.drawUniforms(u)", uniforms(r, w, h))
        raw = base64.b64decode(self.page.evaluate("fw.pixels()"))
        a = np.frombuffer(raw, np.uint8).reshape(h, w, 4)[::-1, :, :3].astype(float)
        if ss > 1:
            a = a.reshape(r["size"]["h"], ss, r["size"]["w"], ss, 3).mean(axis=(1, 3))
        return np.clip(a + 0.5, 0, 255).astype(np.uint8) if ss > 1 else a.astype(np.uint8)

    def close(self):
        self.b.close()
        self.pw.stop()
        self.tmp.cleanup()


def probe_browser():
    """-> (ok, note). Starts and closes the browser once."""
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False, "playwright missing (pip install playwright)"
    try:
        b = Browser()
        note = f"{b.channel} headless, {b.renderer}"
        b.close()
        return True, note
    except Exception as e:  # noqa: BLE001
        return False, f"playwright installed, no browser: {str(e).splitlines()[0][:120]}"


def browser_render(r):
    b = Browser()
    try:
        return b.render(r)
    finally:
        b.close()


# ---------------------------------------------------------------- server
def exact_render(r):
    """Normalised recipe -> (uint8 array, route). NumPy, or perturbation when deep."""
    if r["size"]["w"] * r["size"]["h"] > MAX_EXACT_PIXELS:
        raise ValueError(f"over {MAX_EXACT_PIXELS} pixels")
    if r["formula"] == "mandelbrot" and Decimal(r["view"]["width"]) < Decimal("1e-12"):
        import fw_deep
        return fw_deep.render_array(r, {}), "numpy-perturbation"
    return fw.render_array(r), "numpy"


def png_bytes(arr):
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.png"
        fw.write_png(p, arr=arr)
        return p.read_bytes()


def write_recipe(h, out_dir):
    r = hash_to_recipe(h)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 1
    while (out_dir / f"explore-{n:03d}.json").exists():
        n += 1
    p = out_dir / f"explore-{n:03d}.json"
    p.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    return p


def make_handler(out_dir):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype, extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path in ("/", "/index.html"):
                return self._send(200, page_html().encode("utf-8"), "text/html; charset=utf-8")
            if path == "/fractal.frag":
                return self._send(200, FRAG.read_bytes(), "text/plain; charset=utf-8")
            self._send(404, b"not found", "text/plain")

        def do_POST(self):
            path = urlsplit(self.path).path
            try:
                n = int(self.headers.get("Content-Length", 0))
                if n > 65536:
                    raise ValueError("request too large")
                body = json.loads(self.rfile.read(n) or b"{}")
                h = str(body.get("hash", ""))
                if path == "/export":
                    p = write_recipe(h, out_dir)
                    return self._send(200, json.dumps({"path": str(p)}).encode(), "application/json")
                if path == "/render":
                    r = fw.normalise(hash_to_recipe(h))
                    arr, route = exact_render(r)
                    return self._send(200, png_bytes(arr), "image/png", {"X-Route": route})
                self._send(404, b"not found", "text/plain")
            except (ValueError, KeyError, SystemExit) as e:
                self._send(400, str(e).encode("utf-8"), "text/plain; charset=utf-8")
    return H


def make_server(host="127.0.0.1", port=8765, out_dir="."):
    if host not in LOOPBACK:
        raise ValueError(f"refusing to bind {host!r}: the explorer serves 127.0.0.1 only")
    return ThreadingHTTPServer((host, port), make_handler(out_dir))


def serve(host="127.0.0.1", port=8765, out_dir=".", open_browser=False):
    srv = make_server(host, port, out_dir)
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"explorer at {url} (Ctrl+C stops); exports go to {Path(out_dir).resolve()}", flush=True)
    if open_browser:
        import webbrowser
        threading.Timer(0.3, webbrowser.open, (url,)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(serve())
