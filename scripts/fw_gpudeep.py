"""fractalwright GPU deep zoom: perturbation in a WebGL2 fragment shader (browser route).

Python computes the reference orbit at the view centre in stdlib Decimal (fw_deep.reference_orbit)
and uploads it as an RG32F texture. scripts/page/deep.frag iterates each pixel's float32 delta
with Zhuoran rebasing and a scaled phase (delta in pixel units until it reaches about 1e-30), so
dc never underflows float32. The shader returns nu, n and a rebased flag per pixel; Python colours
with fw.colour, so palettes match the CPU route exactly.

Depth: width / pixels must stay above about 3e-69 (the switch threshold 1e-30 / spacing must fit
in float32). GPU_MIN_WIDTH is set at 1e-60 with margin; below it fw.py uses fw_deep on the CPU.
"""
import base64
import math
import tempfile
from decimal import Decimal
from pathlib import Path

import numpy as np

import fw
import fw_deep

FRAG = Path(__file__).resolve().parent / "page" / "deep.frag"
GPU_MIN_WIDTH = Decimal("1e-60")
SWITCH = 1e-30   # |dz| at which the scaled delta converts to an absolute one
TEX_W = 2048
TILE_ROWS = 128  # rows per draw call, keeps each call well under the Windows GPU timeout

PAGE = """<!doctype html><meta charset="utf-8"><canvas id="cv" width="8" height="8"></canvas>
<script id="fragsrc" type="x-shader/x-fragment">/*FRAG*/</script>
<script>
const cv = document.getElementById("cv");
const gl = cv.getContext("webgl2", { antialias: false });
const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o);
  if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; };
const prog = gl.createProgram();
gl.attachShader(prog, sh(gl.VERTEX_SHADER, "#version 300 es\\nin vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }"));
gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, document.getElementById("fragsrc").textContent.trim()));
gl.bindAttribLocation(prog, 0, "p"); gl.linkProgram(prog);
if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
gl.useProgram(prog);
const vb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vb);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
const L = n => gl.getUniformLocation(prog, n);
const b64f = s => { const b = atob(s), u = new Uint8Array(b.length); for (let i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return new Float32Array(u.buffer); };
window.fwdeep = {
  renderer() { const e = gl.getExtension("WEBGL_debug_renderer_info"); return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : "?"; },
  draw(u) {
    const t0 = performance.now();
    const orb = b64f(u.orbit), th = Math.ceil(orb.length / 2 / u.tw);
    const pad = new Float32Array(u.tw * th * 2); pad.set(orb);
    const tex = gl.createTexture(); gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_ALIGNMENT, 1);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RG32F, u.tw, th, 0, gl.RG, gl.FLOAT, pad);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
    const out = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, out);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA32UI, u.w, u.h);
    const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, out, 0);
    gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.uniform1i(L("u_orbit"), 0); gl.uniform2f(L("u_size"), u.w, u.h); gl.uniform1f(L("u_rot"), u.rot);
    gl.uniform1i(L("u_tw"), u.tw); gl.uniform1i(L("u_last"), u.last); gl.uniform1i(L("u_julia"), u.julia);
    gl.uniform1i(L("u_maxit"), u.maxit); gl.uniform1f(L("u_bail2"), u.bail2);
    gl.uniform1f(L("u_s1"), u.s1); gl.uniform1f(L("u_s2"), u.s2); gl.uniform1f(L("u_S"), u.S); gl.uniform1f(L("u_T"), u.T);
    gl.uniform2f(L("u_z0"), u.z0[0], u.z0[1]);
    gl.viewport(0, 0, u.w, u.h); gl.enable(gl.SCISSOR_TEST);
    const buf = new Uint32Array(u.w * u.h * 4);
    for (let y = 0; y < u.h; y += u.tile) {
      const n = Math.min(u.tile, u.h - y);
      gl.scissor(0, y, u.w, n); gl.drawArrays(gl.TRIANGLES, 0, 3);
      gl.readPixels(0, y, u.w, n, gl.RGBA_INTEGER, gl.UNSIGNED_INT, new Uint32Array(buf.buffer, y * u.w * 16, n * u.w * 4));
    }
    gl.disable(gl.SCISSOR_TEST); gl.bindFramebuffer(gl.FRAMEBUFFER, null);
    gl.deleteFramebuffer(fb); gl.deleteTexture(out); gl.deleteTexture(tex);
    const ms = performance.now() - t0;
    const b8 = new Uint8Array(buf.buffer); let s = "";
    for (let i = 0; i < b8.length; i += 32768) s += String.fromCharCode.apply(null, b8.subarray(i, i + 32768));
    return { data: btoa(s), ms };
  },
};
</script>"""


def supported(r):
    """True when the GPU perturbation path can draw this recipe."""
    return (r["formula"] in fw_deep.FORMULAS and int(r["params"].get("power", 2)) == 2
            and Decimal(r["view"]["width"]) >= GPU_MIN_WIDTH)


def page_html():
    return PAGE.replace("/*FRAG*/", FRAG.read_text(encoding="utf-8"))


def _pow2_split(s):
    """s -> (s1, s2), powers of two with s1 * s2 ~= s split evenly, both inside float32 range."""
    e = math.floor(math.log2(s))
    m = s / 2.0 ** e          # 1 <= m < 2
    a = e // 2
    return float(np.float32(m * 2.0 ** a)), float(2.0 ** (e - a))


def uniforms(r):
    """Normalised recipe -> uniform dict plus the orbit (base64 float32 pairs)."""
    ss = int(r["size"].get("supersample", 1) or 1)
    W, H = r["size"]["w"] * ss, r["size"]["h"] * ss
    width = Decimal(r["view"]["width"])
    p = r["params"]
    maxit, R2 = int(p["max_iter"]), float(p["bailout"]) ** 2
    cx, cy = r["view"]["centre"]
    julia = r["formula"] == "julia"
    if julia:
        Zr, Zi = fw_deep.reference_orbit(p["c"][0], p["c"][1], maxit, R2, fw_deep._prec(width), z0=(cx, cy))
    else:
        Zr, Zi = fw_deep.reference_orbit(cx, cy, maxit, R2, fw_deep._prec(width))
    orb = np.empty(2 * len(Zr), np.float32)
    orb[0::2], orb[1::2] = Zr, Zi
    s = float(width / W)
    s1, s2 = _pow2_split(s)
    T = SWITCH / s
    if T > 3e38:
        raise ValueError(f"width {width} below the GPU scaled-delta range ({GPU_MIN_WIDTH})")
    return {"w": W, "h": H, "rot": math.radians(float(r["view"].get("rotation_deg", 0) or 0)),
            "tw": TEX_W, "last": len(Zr) - 1, "julia": 1 if julia else 0, "maxit": maxit, "bail2": R2,
            "s1": s1, "s2": s2, "S": float(np.float32(s)), "T": min(T, 3e38) if T > 1 else 0.0,
            "z0": [float(Zr[0]), float(Zi[0])], "tile": TILE_ROWS,
            "orbit": base64.b64encode(orb.tobytes()).decode("ascii")}


class GpuDeep:
    """Headless Edge (or Chrome) with the deep page loaded; reuse for many frames."""

    def __init__(self):
        from playwright.sync_api import sync_playwright
        import fw_serve
        self.pw = sync_playwright().start()
        last = None
        for ch in ("msedge", "chrome"):
            try:
                self.b = self.pw.chromium.launch(channel=ch, headless=True, args=fw_serve.BROWSER_ARGS)
                self.channel = ch
                break
            except Exception as e:  # noqa: BLE001
                last = e
        else:
            self.pw.stop()
            raise RuntimeError(f"no msedge or chrome channel: {last}")
        self.tmp = tempfile.TemporaryDirectory()
        page = Path(self.tmp.name) / "deep.html"
        page.write_text(page_html(), encoding="utf-8")
        self.page = self.b.new_page()
        errs = []
        self.page.on("pageerror", lambda e: errs.append(str(e)))
        self.page.goto(page.as_uri())
        try:
            self.page.wait_for_function("window.fwdeep !== undefined", timeout=15000)
        except Exception:
            self.close()
            raise RuntimeError("deep shader page failed: " + "; ".join(errs)[:300])
        self.renderer = self.page.evaluate("fwdeep.renderer()")
        self.last_ms = 0.0

    def escape(self, r):
        """Normalised recipe -> (nu, inside, n, rebased) at supersampled size, top row first."""
        u = uniforms(r)
        res = self.page.evaluate("u => fwdeep.draw(u)", u)
        self.last_ms = float(res["ms"])
        a = np.frombuffer(base64.b64decode(res["data"]), np.uint32).reshape(u["h"], u["w"], 4)[::-1]
        nu = a[..., 0].copy().view(np.float32).astype(np.float64)
        n = a[..., 1].astype(np.int64)
        inside = nu < 0
        n[inside] = -1
        nu[inside] = 0.0
        return nu, inside, n, a[..., 2].astype(bool)

    def render(self, r, stats=None):
        """Recipe -> uint8 HxWx3, coloured by fw.colour (same palette code as the CPU routes)."""
        r = fw.normalise(r)
        nu, inside, _, reb = self.escape(r)
        if stats is not None:
            stats.update(rebased_pixels=int(reb.sum()), gpu_ms=self.last_ms, renderer=self.renderer)
        rgb = fw.colour(r, nu, inside)
        ss = int(r["size"].get("supersample", 1) or 1)
        if ss > 1:
            h, w = r["size"]["h"], r["size"]["w"]
            rgb = rgb.reshape(h, ss, w, ss, 3).mean(axis=(1, 3))
        return np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)

    def close(self):
        try:
            self.b.close()
        finally:
            self.pw.stop()
            self.tmp.cleanup()


def render_array(r, stats=None):
    g = GpuDeep()
    try:
        return g.render(r, stats)
    finally:
        g.close()
