"""fractalwright 3D: raymarched distance-estimator fractals through the browser route.

`fw.py 3d render|recipe|gate`. The shader is scripts/page/fractal3d.frag (own GLSL, sphere
tracing after Hart 1996). Rendering needs Playwright and system Edge or Chrome; there is no
NumPy fallback for 3D (a CPU raymarch at 768x512 with AO and shadows would take minutes per
frame), and doctor says so. Every remedy is a switch in the recipe so the look gate can test
each alone: ao, shadow, fog, trap, dof, aa, camera (composed).

Path tracing (`--pt N`, recipe key "pt"): diffuse surfaces, sky dome plus sun, cosine-weighted
bounces, N samples accumulated over frames in a float framebuffer by additive blending. The random
numbers come from a PCG hash of (pixel, sample index, seed), so the same recipe gives the same pixels.
"""
import base64
import copy
import json
import math
import sys
import tempfile
import time
from pathlib import Path

PAGE_DIR = Path(__file__).resolve().parent / "page"
FRAG3D = PAGE_DIR / "fractal3d.frag"
FORMULAS3D = ("mandelbulb", "mandelbox", "quatjulia", "menger", "hybrid")
REMEDIES = ("ao", "shadow", "fog", "trap", "dof", "aa", "camera")
# Default look (Mark's 3D gate 2026-11-14 kept all-remedies, shadow and camera renders; judge: shadow 6-0,
# ao 5-0-1, camera 5-0-1, fog 0-4-2). Fog, trap, dof and aa stay off unless asked.
DEFAULT_REMEDIES = ("shadow", "ao", "camera")
PALETTE3D = {"a": [0.5, 0.5, 0.5], "b": [0.5, 0.5, 0.5], "c": [1.0, 1.0, 1.0], "d": [0.0, 0.33, 0.67]}

# Per formula: params, and named views as (target, direction from target to eye, distance).
FORMULA_DEFAULTS = {
    "mandelbulb": {"iter": 10, "power": 8.0},
    "mandelbox": {"iter": 14, "scale": 2.0},   # -1.5 read as a plain cube from outside (3D gate)
    "quatjulia": {"iter": 12, "c": [-0.2, 0.6, 0.2, 0.0]},
    "menger": {"iter": 5},
    "hybrid": {"iter": 10, "power": 8.0, "scale": 2.5},
}
VIEWS = {
    "mandelbulb": {"whole": ([0, 0, 0], [0.55, 0.45, 0.7], 2.9), "close": ([0.25, 0.45, 0.35], [0.4, 0.6, 0.7], 0.9)},
    "mandelbox": {"whole": ([0, 0, 0], [0.6, 0.5, 0.65], 15.0), "close": ([4.0, 4.0, 4.0], [0.6, 0.5, 0.65], 5.0)},
    "quatjulia": {"whole": ([0, 0, 0], [0.3, 0.55, 0.8], 3.2), "close": ([0.1, 0.3, 0.3], [0.5, 0.6, 0.6], 1.3)},
    "menger": {"whole": ([0, 0, 0], [0.75, 0.55, 0.9], 4.0), "close": ([0.6, 0.6, 1.0], [0.25, 0.2, 0.95], 1.0)},
    "hybrid": {"whole": ([0, 0, 0], [0.55, 0.45, 0.7], 3.2), "close": ([0.4, 0.4, 0.4], [0.4, 0.6, 0.7], 1.0)},
}
PT_DEFAULTS = {"samples": 64, "bounces": 2, "seed": 1, "spf": 4}
SUN = [2.2, 2.0, 1.75]
SKY_ZENITH, SKY_HORIZON = [0.16, 0.22, 0.38], [0.34, 0.36, 0.4]
LAZY_FOV = 60.0          # vertical degrees: the "default" camera
COMPOSED_MM = 40.0       # full-frame focal length for the composed camera (35-50 mm band)


def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def mm_to_vfov(mm):
    """Full-frame (36x24 mm) focal length -> vertical field of view in degrees."""
    return math.degrees(2 * math.atan(12.0 / mm))


def default_recipe(formula="mandelbulb", view="whole"):
    if formula not in FORMULAS3D:
        raise ValueError(f"3d formula must be one of {', '.join(FORMULAS3D)}")
    return {
        "kind": "3d", "formula": formula, "params": dict(copy.deepcopy(FORMULA_DEFAULTS[formula])),
        "view": view, "camera": None,
        "remedies": {k: k in DEFAULT_REMEDIES for k in REMEDIES},
        "size": {"w": 768, "h": 512},
        "palette": copy.deepcopy(PALETTE3D),
        "light": [0.55, 0.75, 0.35],
        "march": {"steps": 256, "fudge": 0.85},
    }


def camera_for(r):
    """Recipe -> explicit camera {eye, target, fov_deg, roll_deg, focus}. Explicit cameras pass through."""
    if r.get("camera"):
        return dict(r["camera"])
    tgt, d, dist = VIEWS[r["formula"]][r["view"]]
    d = _norm(d)
    if not r["remedies"].get("camera"):
        eye = [t + dist * x for t, x in zip(tgt, d)]
        return {"eye": eye, "target": list(tgt), "fov_deg": LAZY_FOV, "roll_deg": 0.0, "focus": dist}
    # Composed: 40 mm lens, distance scaled so the subject keeps its size, camera dropped to a low
    # angle (looking up about 12 degrees), subject moved onto the left third, a slight roll.
    fov = mm_to_vfov(COMPOSED_MM)
    dist2 = dist * math.tan(math.radians(LAZY_FOV / 2)) / math.tan(math.radians(fov / 2)) * 0.85
    az = math.atan2(d[0], d[2])
    el = math.radians(-12.0)
    d2 = [math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az)]
    eye = [t + dist2 * x for t, x in zip(tgt, d2)]
    fwd = _norm([t - e for t, e in zip(tgt, eye)])
    right = _norm([fwd[1] * 0 - fwd[2] * 1, fwd[2] * 0 - fwd[0] * 0, fwd[0] * 1 - fwd[1] * 0])
    aspect = r["size"]["w"] / r["size"]["h"]
    hhalf = math.tan(math.radians(fov / 2)) * aspect
    shift = hhalf * (1 / 3) * dist2          # aim right of the subject so it sits on the left third
    target = [t + shift * x for t, x in zip(tgt, right)]
    return {"eye": eye, "target": target, "fov_deg": fov, "roll_deg": 4.0, "focus": dist2}


def normalise(r):
    """Fill defaults, check names, and make the camera explicit (so the recipe replays exactly)."""
    base = default_recipe(r.get("formula", "mandelbulb"), r.get("view", "whole"))
    out = copy.deepcopy(base)
    for k, v in r.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(copy.deepcopy(v))
        else:
            out[k] = copy.deepcopy(v)
    if out["view"] not in VIEWS[out["formula"]] and not out.get("camera"):
        raise ValueError(f"view must be one of {', '.join(VIEWS[out['formula']])} or give a camera")
    bad = set(out["remedies"]) - set(REMEDIES)
    if bad:
        raise ValueError(f"unknown remedies: {', '.join(sorted(bad))}")
    if out.get("pt"):
        pt = dict(PT_DEFAULTS)
        pt.update(out["pt"] if isinstance(out["pt"], dict) else {"samples": int(out["pt"])})
        pt = {k: int(v) for k, v in pt.items()}
        if pt["samples"] < 1 or not 0 <= pt["bounces"] <= 7 or not 1 <= pt["spf"] <= 64:
            raise ValueError("pt: samples >= 1, bounces 0-7, spf 1-64")
        pt["seed"] &= 0xFFFFFFFF
        out["pt"] = pt
    else:
        out.pop("pt", None)
    out["camera"] = camera_for(out)
    return out


def uniforms(r):
    r = normalise(r)
    cam, p, rem, m = r["camera"], r["params"], r["remedies"], r["march"]
    w, h = r["size"]["w"], r["size"]["h"]
    fov = math.radians(cam["fov_deg"])
    spp = 1
    if rem.get("aa"):
        spp = 4
    if rem.get("dof"):
        spp = 16
    dist = cam.get("focus", 3.0)
    return {
        "w": w, "h": h, "eye": cam["eye"], "target": cam["target"], "fov": fov,
        "roll": math.radians(cam.get("roll_deg", 0.0)),
        "formula": FORMULAS3D.index(r["formula"]), "iter": int(p.get("iter", 10)),
        "power": float(p.get("power", 8.0)), "scale": float(p.get("scale", -1.5)),
        "jc": [float(x) for x in p.get("c", [-0.2, 0.6, 0.2, 0.0])],
        "steps": int(m["steps"]), "fudge": float(m["fudge"]), "maxdist": dist * 4 + 6,
        "eps": 0.75 * math.tan(fov / 2) / h,
        "light": r["light"], "bg": [0.16, 0.16, 0.18], "fogcol": [0.72, 0.78, 0.86],
        "a": p_or(r, "a"), "b": p_or(r, "b"), "c": p_or(r, "c"), "d": p_or(r, "d"),
        "ao": int(bool(rem.get("ao"))), "shadow": int(bool(rem.get("shadow"))), "fog": int(bool(rem.get("fog"))),
        "trap": int(bool(rem.get("trap"))), "dof": int(bool(rem.get("dof"))), "aa": int(bool(rem.get("aa") or rem.get("dof"))),
        "aperture": 0.012 * dist, "focus": dist, "fogdens": 0.12 / (dist * dist), "spp": spp,
        "pt": 1 if r.get("pt") else 0, "sun": SUN, "skyz": SKY_ZENITH, "skyh": SKY_HORIZON,
        **({"samples": r["pt"]["samples"], "bounces": r["pt"]["bounces"], "seed": r["pt"]["seed"],
            "spf": r["pt"]["spf"]} if r.get("pt") else {}),
    }


def p_or(r, k):
    return [float(x) for x in r["palette"][k]]


PAGE3D = """<!doctype html><html><head><meta charset="utf-8"></head><body>
<canvas id="cv" width="8" height="8"></canvas>
<script id="fragsrc" type="x-shader/x-fragment">/*FRAG*/</script>
<script>
const cv = document.getElementById("cv");
const gl = cv.getContext("webgl2", { preserveDrawingBuffer: true, antialias: false });
let U = {};
(function () {
  const vs = "#version 300 es\\nin vec2 p; void main(){ gl_Position = vec4(p, 0.0, 1.0); }";
  const sh = (t, s) => { const o = gl.createShader(t); gl.shaderSource(o, s); gl.compileShader(o);
    if (!gl.getShaderParameter(o, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(o)); return o; };
  const prog = gl.createProgram();
  gl.attachShader(prog, sh(gl.VERTEX_SHADER, vs));
  gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, document.getElementById("fragsrc").textContent.trim()));
  gl.bindAttribLocation(prog, 0, "p"); gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(prog));
  gl.useProgram(prog);
  const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  const n = gl.getProgramParameter(prog, gl.ACTIVE_UNIFORMS);
  for (let i = 0; i < n; i++) { const nm = gl.getActiveUniform(prog, i).name; U[nm] = gl.getUniformLocation(prog, nm); }
})();
const F = {u_fov:"fov",u_roll:"roll",u_power:"power",u_scale:"scale",u_fudge:"fudge",u_maxdist:"maxdist",u_eps:"eps",
  u_aperture:"aperture",u_focus:"focus",u_fogdens:"fogdens"};
const I = {u_formula:"formula",u_iter:"iter",u_steps:"steps",u_ao:"ao",u_shadow:"shadow",u_fog:"fog",u_trap:"trap",
  u_dof:"dof",u_aa:"aa",u_spp:"spp",u_pt:"pt",u_bounces:"bounces"};
const V3 = {u_eye:"eye",u_target:"target",u_light:"light",u_bg:"bg",u_fogcol:"fogcol",u_a:"a",u_b:"b",u_cc:"c",u_d:"d",
  u_sun:"sun",u_skyz:"skyz",u_skyh:"skyh"};
function setAll(u) {
  const s = (k, f, ...v) => { if (U[k]) gl[f](U[k], ...v); };
  s("u_size", "uniform2f", u.w, u.h); s("u_jc", "uniform4fv", u.jc);
  for (const k in F) s(k, "uniform1f", u[F[k]]);
  for (const k in I) if (u[I[k]] !== undefined) s(k, "uniform1i", u[I[k]]);
  for (const k in V3) s(k, "uniform3fv", u[V3[k]]);
  return s;
}
window.fw3 = {
  renderer() { const e = gl.getExtension("WEBGL_debug_renderer_info");
    return e ? gl.getParameter(e.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER); },
  draw(u, strip) {
    cv.width = u.w; cv.height = u.h; gl.viewport(0, 0, u.w, u.h);
    setAll(u);
    gl.enable(gl.SCISSOR_TEST);
    for (let y = 0; y < u.h; y += strip) {   // strips keep each GPU submit short (no driver timeout)
      gl.scissor(0, y, u.w, Math.min(strip, u.h - y)); gl.drawArrays(gl.TRIANGLES, 0, 3);
      const px = new Uint8Array(4); gl.readPixels(0, y, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, px);
    }
    gl.disable(gl.SCISSOR_TEST);
  },
  // Path tracer: sum samples/N into an RGBA32F target with additive blending, frame by frame.
  drawPT(u, strip) {
    if (!gl.getExtension("EXT_color_buffer_float")) throw new Error("no EXT_color_buffer_float");
    if (!gl.getExtension("EXT_float_blend")) throw new Error("no EXT_float_blend");
    cv.width = 1; cv.height = 1;
    const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texStorage2D(gl.TEXTURE_2D, 1, gl.RGBA32F, u.w, u.h);
    const fb = gl.createFramebuffer(); gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
    gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
    gl.viewport(0, 0, u.w, u.h); gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
    const s = setAll(u);
    s("u_seed", "uniform1ui", u.seed >>> 0); s("u_invn", "uniform1f", 1.0 / u.samples);
    gl.enable(gl.BLEND); gl.blendFunc(gl.ONE, gl.ONE); gl.enable(gl.SCISSOR_TEST);
    const px = new Float32Array(4);
    for (let done = 0; done < u.samples; done += u.spf) {
      s("u_frame0", "uniform1i", done); s("u_spf", "uniform1i", Math.min(u.spf, u.samples - done));
      for (let y = 0; y < u.h; y += strip) {
        gl.scissor(0, y, u.w, Math.min(strip, u.h - y)); gl.drawArrays(gl.TRIANGLES, 0, 3);
        gl.readPixels(0, y, 1, 1, gl.RGBA, gl.FLOAT, px);
      }
    }
    gl.disable(gl.SCISSOR_TEST); gl.disable(gl.BLEND);
    const buf = new Float32Array(u.w * u.h * 4);
    gl.readPixels(0, 0, u.w, u.h, gl.RGBA, gl.FLOAT, buf);
    gl.bindFramebuffer(gl.FRAMEBUFFER, null); gl.deleteFramebuffer(fb); gl.deleteTexture(tex);
    const b8 = new Uint8Array(buf.buffer);
    let str = ""; for (let i = 0; i < b8.length; i += 32768) str += String.fromCharCode.apply(null, b8.subarray(i, i + 32768));
    return btoa(str);
  },
  pixels() { const w = cv.width, h = cv.height, buf = new Uint8Array(w * h * 4);
    gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, buf);
    let s = ""; for (let i = 0; i < buf.length; i += 32768) s += String.fromCharCode.apply(null, buf.subarray(i, i + 32768));
    return btoa(s); },
};
</script></body></html>"""


def page3d_html():
    return PAGE3D.replace("/*FRAG*/", FRAG3D.read_text(encoding="utf-8"))


class Browser3D:
    """Headless system Edge (or Chrome) with the 3D page loaded; reuse it across many renders."""

    def __init__(self):
        import fw_serve
        from playwright.sync_api import sync_playwright
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
        p = Path(self.tmp.name) / "fractal3d.html"
        p.write_text(page3d_html(), encoding="utf-8")
        self.page = self.b.new_page()
        errors = []
        self.page.on("pageerror", lambda e: errors.append(str(e)))
        self.page.goto(p.as_uri())
        try:
            self.page.wait_for_function("window.fw3 !== undefined", timeout=60000)
        except Exception:
            self.close()
            raise RuntimeError("3D shader failed: " + "; ".join(errors)[:400])
        self.renderer = self.page.evaluate("fw3.renderer()")

    def render_linear(self, r):
        """Path-traced recipe -> (float32 HxWx3 linear radiance, seconds)."""
        import numpy as np
        u = uniforms(r)
        if not u["pt"]:
            raise ValueError("render_linear needs a recipe with pt")
        t0 = time.perf_counter()
        raw = base64.b64decode(self.page.evaluate("([u, s]) => fw3.drawPT(u, s)", [u, 64]))
        dt = time.perf_counter() - t0
        a = np.frombuffer(raw, np.float32).reshape(u["h"], u["w"], 4)[::-1, :, :3].copy()
        return a, dt

    def render(self, r):
        """Recipe -> (uint8 HxWx3, seconds)."""
        import numpy as np
        u = uniforms(r)
        if u["pt"]:
            lin, dt = self.render_linear(r)
            return to_srgb8(lin), dt
        strip = 16 if u["spp"] > 4 else 64
        t0 = time.perf_counter()
        self.page.evaluate("([u, s]) => fw3.draw(u, s)", [u, strip])
        raw = base64.b64decode(self.page.evaluate("fw3.pixels()"))
        dt = time.perf_counter() - t0
        a = np.frombuffer(raw, np.uint8).reshape(u["h"], u["w"], 4)[::-1, :, :3].copy()
        return a, dt

    def close(self):
        try:
            self.b.close()
        finally:
            self.pw.stop()
            self.tmp.cleanup()


def to_srgb8(lin):
    """Linear radiance -> 8-bit with the same 1/2.2 curve the shader's direct route uses."""
    import numpy as np
    return (np.clip(lin, 0.0, 1.0) ** (1 / 2.2) * 255.0 + 0.5).astype(np.uint8)


def probe():
    try:
        b = Browser3D()
    except Exception as e:  # noqa: BLE001
        return False, str(e).splitlines()[0][:120]
    note = f"{b.channel}, {b.renderer}"
    b.close()
    return True, note


# ---------------------------------------------------------------- gate
GATE_FORMULAS = ("mandelbulb", "quatjulia", "menger")
GATE_VIEWS = ("whole", "close")


def gate_variants():
    """(name, remedies dict) for baseline, each remedy alone, and all together."""
    out = [("baseline", {})]
    out += [(k, {k: True}) for k in REMEDIES]
    out.append(("all", {k: True for k in REMEDIES}))
    return out


def _save_jpeg(arr, path, quality=82):
    from PIL import Image
    Image.fromarray(arr).save(path, "JPEG", quality=quality, optimize=True)


def _sheet(cells, path, cols, label_h=22, scale=0.5):
    """cells: [(label, HxWx3 uint8)] -> labelled JPEG grid."""
    from PIL import Image, ImageDraw
    ims = [Image.fromarray(a) for _, a in cells]
    w, h = int(ims[0].width * scale), int(ims[0].height * scale)
    rows = math.ceil(len(cells) / cols)
    sheet = Image.new("RGB", (cols * w, rows * (h + label_h)), (24, 24, 26))
    dr = ImageDraw.Draw(sheet)
    for i, ((lab, _), im) in enumerate(zip(cells, ims)):
        x, y = (i % cols) * w, (i // cols) * (h + label_h)
        sheet.paste(im.resize((w, h), Image.LANCZOS), (x, y + label_h))
        dr.text((x + 6, y + 5), lab, fill=(230, 230, 230))
    sheet.save(path, "JPEG", quality=80, optimize=True)


def run_gate(out_dir, size=(768, 512), formulas=GATE_FORMULAS, views=GATE_VIEWS):
    out_dir = Path(out_dir)
    (out_dir / "renders").mkdir(parents=True, exist_ok=True)
    (out_dir / "recipes").mkdir(exist_ok=True)
    b = Browser3D()
    log = {"renderer": b.renderer, "channel": b.channel, "size": list(size), "renders": []}
    try:
        for f in formulas:
            for v in views:
                cells = []
                for name, rem in gate_variants():
                    r = default_recipe(f, v)
                    r["size"] = {"w": size[0], "h": size[1]}
                    r["remedies"] = {k: bool(rem.get(k)) for k in REMEDIES}
                    r = normalise(r)
                    arr, dt = b.render(r)
                    stem = f"{f}-{v}-{name}"
                    _save_jpeg(arr, out_dir / "renders" / f"{stem}.jpg")
                    (out_dir / "recipes" / f"{stem}.json").write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
                    log["renders"].append({"formula": f, "view": v, "variant": name, "seconds": round(dt, 3),
                                           "mean": round(float(arr.mean()), 2), "file": f"renders/{stem}.jpg"})
                    print(f"{stem}: {dt:.2f} s", flush=True)
                    cells.append((name, arr))
                _sheet(cells, out_dir / f"sheet-{f}-{v}.jpg", cols=3)
    finally:
        b.close()
    log["total_seconds"] = round(sum(x["seconds"] for x in log["renders"]), 2)
    (out_dir / "gate.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return log


# ---------------------------------------------------------------- CLI
def _load(spec):
    p = Path(spec)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if spec in FORMULAS3D:
        return default_recipe(spec)
    raise SystemExit(f"3d: {spec!r} is neither a recipe file nor one of {', '.join(FORMULAS3D)}")


def _apply_args(r, a):
    if getattr(a, "view", None):
        r["view"] = a.view
        r["camera"] = None
    if getattr(a, "size", None):
        w, h = a.size.lower().split("x")
        r["size"] = {"w": int(w), "h": int(h)}
    rem = r.setdefault("remedies", {})
    for k in (a.remedy or []):
        if k == "all":
            rem.update({x: True for x in REMEDIES})
        elif k == "none":
            rem.update({x: False for x in REMEDIES})
        elif k not in REMEDIES:
            raise SystemExit(f"3d: unknown remedy {k}; one of {', '.join(REMEDIES)}, all, none")
        else:
            rem[k] = True
    if getattr(a, "pt", None):
        pt = dict(r.get("pt") or {})
        pt["samples"] = a.pt
        for k in ("bounces", "seed"):
            if getattr(a, k, None) is not None:
                pt[k] = getattr(a, k)
        r["pt"] = pt
    return r


def cmd_3d(a):
    if a.action == "recipe":
        r = normalise(_apply_args(_load(a.target or "mandelbulb"), a))
        txt = json.dumps(r, indent=2) + "\n"
        if a.out:
            Path(a.out).write_text(txt, encoding="utf-8")
            print(f"wrote {a.out}")
        else:
            print(txt, end="")
        return 0
    if a.action == "render":
        r = normalise(_apply_args(_load(a.target or "mandelbulb"), a))
        out = Path(a.out or "fractal3d.png")
        try:
            b = Browser3D()
        except Exception as e:  # noqa: BLE001
            print(f"3d needs Playwright and Edge or Chrome (no NumPy fallback for 3D): {str(e).splitlines()[0][:160]}")
            return 2
        try:
            arr, dt = b.render(r)
        finally:
            b.close()
        import fw
        if out.suffix.lower() in (".jpg", ".jpeg"):
            _save_jpeg(arr, out)
        else:
            fw.write_png(out, arr=arr)
        rec = out.with_suffix(".json")
        rec.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out} and {rec} ({dt:.2f} s)")
        return 0
    if a.action == "mesh":
        import fw_mesh
        return fw_mesh.cmd_mesh(a, normalise(_load(a.target or "mandelbulb")))
    if a.action == "gate":
        w, h = (a.size or "768x512").lower().split("x")
        log = run_gate(a.out or "gate3d", (int(w), int(h)))
        print(f"{len(log['renders'])} renders, {log['total_seconds']} s GPU+readback, {log['renderer']}")
        return 0
    raise SystemExit("3d: action is recipe, render or gate")


EXPLAIN_3D = {
    "3d": "3D distance-estimator fractals (fw.py 3d). Sphere tracing (Hart 1996): march each ray by DE(p), a lower "
          "bound on the distance to the set. Mandelbulb power 8 and quaternion Julia use 0.5 r log r / dr with a "
          "running derivative; Mandelbox |z|/|dr| after box and sphere folds; Menger is the cube minus crosses; "
          "hybrid box-folds before each bulb step (evaluated at p*2.5 so it fits the bulb's frame). Default look: shadow, ao and a composed camera. Remedies as switches: ao, shadow, fog, trap, dof, aa, camera. "
          "--pt N path traces (diffuse, sky + sun, cosine-weighted bounces, seeded PCG RNG, N samples "
          "accumulated over frames). Browser route only (no NumPy fallback), except `3d mesh`, which samples the same DEs in NumPy and writes a watertight STL in millimetres. Shipped as a normal route after Mark's 3D gate (2026-11-14).",
}


def register(sub, explain):
    explain.update(EXPLAIN_3D)
    s = sub.add_parser("3d", help="3D DE fractals: recipe, render, gate (browser route); mesh (NumPy, printable STL)")
    s.add_argument("action", choices=["recipe", "render", "gate", "mesh"])
    s.add_argument("target", nargs="?", help=f"recipe.json or a formula ({', '.join(FORMULAS3D)})")
    s.add_argument("-o", "--out")
    s.add_argument("--view", help="whole or close (the formula's named views)")
    s.add_argument("--size", help="WxH, default 768x512")
    s.add_argument("--remedy", action="append", help=f"repeatable, added to the default ({', '.join(DEFAULT_REMEDIES)}): "
                   f"{', '.join(REMEDIES)}, all; none clears them first")
    s.add_argument("--pt", type=int, metavar="N", help="path trace with N samples per pixel (diffuse, sky + sun, "
                   "cosine-weighted bounces; replaces the shadow/ao look)")
    s.add_argument("--bounces", type=int, help=f"path tracer indirect bounces (default {PT_DEFAULTS['bounces']})")
    s.add_argument("--seed", type=int, help=f"path tracer seed (default {PT_DEFAULTS['seed']}); same seed, same pixels")
    s.add_argument("--res", type=int, help="mesh: grid points per side (default 200)")
    s.add_argument("--size-mm", type=float, help="mesh: longest side in millimetres (default 60)")
    s.add_argument("--iter", type=int, help="mesh: formula iterations (Menger defaults to level 3 for printing)")
    s.add_argument("--engine", choices=["auto", "skimage", "numpy"], default="auto",
                   help="mesh: marching cubes from scikit-image if installed (auto), or NumPy marching tetrahedra")
    s.set_defaults(fn=cmd_3d)
