"""fractalwright Step C render-core benchmark.

Same job for every candidate: Mandelbrot, 1920x1080, 1000 max iterations,
smooth colouring (bailout radius 256), two views. Wall time is the median of
3 warm runs (one untimed warm-up first). Output PNGs go to bench/out/.
The CPU reference is NumPy float64. Run with bench/.venv/Scripts/python.
"""
import base64, io, json, math, statistics, sys, time
from pathlib import Path
import numpy as np
from PIL import Image

W, H, MAXIT = 1920, 1080, 1000
VIEWS = {
    "full": (-0.75, 0.0, 3.5),                       # centre x, y, width
    "deep": (-0.7436447860, 0.1318252536, 1e-4),
}
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
R2 = 256.0 * 256.0


def colour_np(nu, inside):
    """nu: smooth iteration count; inside: bool mask. Returns uint8 HxWx3."""
    t = nu * 0.02
    rgb = np.stack([0.5 + 0.5 * np.cos(6.2831853 * (t + p)) for p in (0.0, 0.33, 0.67)], -1)
    rgb[inside] = 0.0
    return np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)


# ---------------- (a) pure Python ----------------
def render_py(view, w=W, h=H, x0=0, y0=0, cw=320, ch=180):
    cx, cy, width = view
    px = width / w
    out = bytearray(cw * ch * 3)
    log2 = math.log(2)
    for j in range(ch):
        ci = cy + ((h / 2) - (y0 + j + 0.5)) * px
        for i in range(cw):
            cr = cx + ((x0 + i + 0.5) - w / 2) * px
            zr = zi = 0.0
            n = 0
            while n < MAXIT:
                zr2, zi2 = zr * zr, zi * zi
                if zr2 + zi2 > R2:
                    break
                zi = 2 * zr * zi + ci
                zr = zr2 - zi2 + cr
                n += 1
            k = (j * cw + i) * 3
            if n < MAXIT:
                nu = n + 1 - math.log(math.log(zr * zr + zi * zi) / 2 / log2) / log2
                t = nu * 0.02
                for c, p in enumerate((0.0, 0.33, 0.67)):
                    v = 0.5 + 0.5 * math.cos(6.2831853 * (t + p))
                    out[k + c] = min(255, max(0, int(v * 255.0 + 0.5)))
    return np.frombuffer(bytes(out), np.uint8).reshape(ch, cw, 3)


# ---------------- (b) NumPy float64 (reference) ----------------
def render_np(view):
    cx, cy, width = view
    px = width / W
    xs = cx + (np.arange(W) + 0.5 - W / 2) * px
    ys = cy + (H / 2 - (np.arange(H) + 0.5)) * px
    c = (xs[None, :] + 1j * ys[:, None]).ravel()
    z = np.zeros_like(c)
    n = np.full(c.shape, MAXIT, np.int32)
    zf = np.zeros_like(c)
    idx = np.arange(c.size)
    cc = c.copy()
    for it in range(MAXIT):
        z = z * z + cc
        esc = (z.real * z.real + z.imag * z.imag) > R2
        if esc.any():
            e = idx[esc]
            n[e] = it  # escaped after it+1 steps; matches the loop form below
            zf[e] = z[esc]
            keep = ~esc
            z, cc, idx = z[keep], cc[keep], idx[keep]
            if idx.size == 0:
                break
    inside = n == MAXIT
    nu = np.zeros(c.size)
    o = ~inside
    nu[o] = (n[o] + 1) + 1 - np.log2(np.log(np.abs(zf[o]) ** 2) / 2 / math.log(2))
    return colour_np(nu.reshape(H, W), inside.reshape(H, W))


# Shared shader body. Loop form: n counts completed z updates before escape.
GLSL_BODY = """
    {T} cx = {T}(u_c.x) + ({T}(gl_FragCoord.x) - {T}({W}) * 0.5) * {T}(u_px);
    {T} cy = {T}(u_c.y) + ({T}({H}) * 0.5 - {T}(gl_FragCoord.y)) * {T}(u_px);
    {T} zr = 0.0, zi = 0.0;
    int n = 0;
    for (; n < {M}; n++) {{
        {T} zr2 = zr*zr, zi2 = zi*zi;
        if (zr2 + zi2 > 65536.0) break;
        zi = 2.0*zr*zi + cy;
        zr = zr2 - zi2 + cx;
    }}
    if (n >= {M}) {{ frag = vec4(0,0,0,1); return; }}
    float m2 = float(zr*zr + zi*zi);
    float nu = float(n) + 1.0 - log2(log(m2) * 0.5 / log(2.0));
    float t = nu * 0.02;
    frag = vec4(0.5 + 0.5*cos(6.2831853*(t + vec3(0.0, 0.33, 0.67))), 1.0);
"""
# note: CPU nu uses (n+1)+1-...; GPU n here == CPU (it+1). Same formula.


def glsl_src(double):
    T = "double" if double else "float"
    head = "#version 400\n" if double else "#version 330\n"
    uni = "uniform dvec2 u_c; uniform double u_px;" if double else "uniform vec2 u_c; uniform float u_px;"
    return head + uni + "\nout vec4 frag;\nvoid main(){" + GLSL_BODY.format(T=T, W=W, H=H, M=MAXIT) + "}\n"


VERT = "#version 330\nin vec2 p; void main(){ gl_Position = vec4(p,0,1); }"


class ModernGL:
    def __init__(self, double):
        import moderngl
        self.ctx = moderngl.create_standalone_context(require=400 if double else 330)
        self.prog = self.ctx.program(vertex_shader=VERT, fragment_shader=glsl_src(double))
        vbo = self.ctx.buffer(np.array([-1, -1, 3, -1, -1, 3], "f4").tobytes())
        self.vao = self.ctx.vertex_array(self.prog, [(vbo, "2f", "p")])
        self.fbo = self.ctx.simple_framebuffer((W, H), components=4)
        self.double = double
        self.renderer = self.ctx.info.get("GL_RENDERER")

    def render(self, view):
        cx, cy, width = view
        self.prog["u_c"].value = (cx, cy)
        self.prog["u_px"].value = width / W
        self.fbo.use()
        self.vao.render()
        a = np.frombuffer(self.fbo.read(components=3), np.uint8).reshape(H, W, 3)
        return a.copy()  # GL rows come back bottom-up; shader already maps row 0 to the top of the view


WGSL = """
struct U { c: vec2<f32>, px: f32, pad: f32 };
@group(0) @binding(0) var<uniform> u: U;
@vertex fn vs(@builtin(vertex_index) i: u32) -> @builtin(position) vec4<f32> {
  var p = array<vec2<f32>,3>(vec2(-1.0,-1.0), vec2(3.0,-1.0), vec2(-1.0,3.0));
  return vec4(p[i], 0.0, 1.0);
}
@fragment fn fs(@builtin(position) fc: vec4<f32>) -> @location(0) vec4<f32> {
  let cx = u.c.x + (fc.x - %(W)d.0*0.5) * u.px;
  let cy = u.c.y + (%(H)d.0*0.5 - fc.y) * u.px;
  var zr = 0.0; var zi = 0.0; var n = 0;
  loop { if (n >= %(M)d) { break; }
    let zr2 = zr*zr; let zi2 = zi*zi;
    if (zr2 + zi2 > 65536.0) { break; }
    zi = 2.0*zr*zi + cy; zr = zr2 - zi2 + cx; n = n + 1; }
  if (n >= %(M)d) { return vec4(0.0,0.0,0.0,1.0); }
  let nu = f32(n) + 1.0 - log2(log(zr*zr+zi*zi) * 0.5 / log(2.0));
  let t = nu * 0.02;
  return vec4(0.5 + 0.5*cos(6.2831853*(vec3(t) + vec3(0.0,0.33,0.67))), 1.0);
}
""" % dict(W=W, H=H, M=MAXIT)


class WGPU:
    def __init__(self):
        import wgpu
        self.wgpu = wgpu
        self.adapter = wgpu.gpu.request_adapter_sync(power_preference="high-performance")
        self.dev = self.adapter.request_device_sync()
        sm = self.dev.create_shader_module(code=WGSL)
        self.ubuf = self.dev.create_buffer(size=16, usage=wgpu.BufferUsage.UNIFORM | wgpu.BufferUsage.COPY_DST)
        bgl = self.dev.create_bind_group_layout(entries=[{"binding": 0, "visibility": wgpu.ShaderStage.FRAGMENT,
                                                          "buffer": {"type": "uniform"}}])
        self.bg = self.dev.create_bind_group(layout=bgl, entries=[{"binding": 0, "resource": {"buffer": self.ubuf}}])
        self.pipe = self.dev.create_render_pipeline(
            layout=self.dev.create_pipeline_layout(bind_group_layouts=[bgl]),
            vertex={"module": sm, "entry_point": "vs"},
            fragment={"module": sm, "entry_point": "fs", "targets": [{"format": "rgba8unorm"}]},
            primitive={}, depth_stencil=None, multisample=None)
        self.tex = self.dev.create_texture(size=(W, H, 1), format="rgba8unorm",
                                           usage=wgpu.TextureUsage.RENDER_ATTACHMENT | wgpu.TextureUsage.COPY_SRC)
        self.view = self.tex.create_view()
        self.renderer = self.adapter.info.get("device", "?")

    def render(self, view):
        cx, cy, width = view
        self.dev.queue.write_buffer(self.ubuf, 0, np.array([cx, cy, width / W, 0], "f4").tobytes())
        enc = self.dev.create_command_encoder()
        rp = enc.begin_render_pass(color_attachments=[{"view": self.view, "load_op": "clear", "store_op": "store",
                                                       "clear_value": (0, 0, 0, 1)}])
        rp.set_pipeline(self.pipe); rp.set_bind_group(0, self.bg); rp.draw(3); rp.end()
        self.dev.queue.submit([enc.finish()])
        data = self.dev.queue.read_texture({"texture": self.tex}, {"bytes_per_row": W * 4}, (W, H, 1))
        return np.frombuffer(data, np.uint8).reshape(H, W, 4)[:, :, :3].copy()


HTML = """<!doctype html><canvas id=c width=%(W)d height=%(H)d></canvas><script>
const gl = document.getElementById('c').getContext('webgl2', {preserveDrawingBuffer:true, antialias:false});
const vs = `#version 300 es
in vec2 p; void main(){ gl_Position = vec4(p,0,1); }`;
const fs = `#version 300 es
precision highp float; precision highp int;
uniform vec2 u_c; uniform float u_px; out vec4 frag;
void main(){%(BODY)s}`;
function sh(t,s){const o=gl.createShader(t);gl.shaderSource(o,s);gl.compileShader(o);
 if(!gl.getShaderParameter(o,gl.COMPILE_STATUS)) throw gl.getShaderInfoLog(o); return o;}
const pr = gl.createProgram(); gl.attachShader(pr, sh(gl.VERTEX_SHADER,vs)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER,fs));
gl.linkProgram(pr); gl.useProgram(pr);
const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER,b);
gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1,3,-1,-1,3]), gl.STATIC_DRAW);
gl.enableVertexAttribArray(0); gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);
const buf = new Uint8Array(%(W)d*%(H)d*4);
window.draw = (cx,cy,px) => { gl.viewport(0,0,%(W)d,%(H)d);
  gl.uniform2f(gl.getUniformLocation(pr,'u_c'),cx,cy); gl.uniform1f(gl.getUniformLocation(pr,'u_px'),px);
  gl.drawArrays(gl.TRIANGLES,0,3); gl.readPixels(0,0,%(W)d,%(H)d,gl.RGBA,gl.UNSIGNED_BYTE,buf); return 0; };
window.grab = () => { let s=''; for (let i=0;i<buf.length;i+=32768) s += String.fromCharCode.apply(null, buf.subarray(i,i+32768)); return btoa(s); };
window.renderer = () => { const e=gl.getExtension('WEBGL_debug_renderer_info'); return e?gl.getParameter(e.UNMASKED_RENDERER_WEBGL):'?'; };
</script>"""


class Browser:
    """Headless system Edge via Playwright (no Chromium download needed)."""
    def __init__(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.b = self.pw.chromium.launch(channel="msedge", headless=True,
                                         args=["--use-angle=d3d11", "--enable-gpu", "--ignore-gpu-blocklist"])
        self.page = self.b.new_page()
        body = GLSL_BODY.format(T="float", W=W, H=H, M=MAXIT)
        p = OUT / "webgl.html"
        p.write_text(HTML % dict(W=W, H=H, BODY=body), encoding="utf-8")
        self.page.goto(p.as_uri())
        self.renderer = self.page.evaluate("renderer()")

    def render(self, view, grab=True):
        cx, cy, width = view
        self.page.evaluate(f"draw({cx!r},{cy!r},{width / W!r})")
        if not grab:
            return None
        raw = base64.b64decode(self.page.evaluate("grab()"))
        return np.frombuffer(raw, np.uint8).reshape(H, W, 4)[:, :, :3].copy()

    def close(self):
        self.b.close(); self.pw.stop()


def timed(fn, runs=3):
    fn()  # warm
    ts = []
    out = None
    for _ in range(runs):
        t = time.perf_counter(); out = fn(); ts.append(time.perf_counter() - t)
    return statistics.median(ts), out


def main():
    res = {}
    ref = {}
    for v, view in VIEWS.items():
        t, img = timed(lambda: render_np(view))
        ref[v] = img
        Image.fromarray(img).save(OUT / f"numpy_{v}.png")
        again = render_np(view)
        res[f"numpy/{v}"] = dict(s=round(t, 3), diff=0.0, det=bool((again == img).all()))
        print("numpy", v, res[f"numpy/{v}"], flush=True)

    for v, view in VIEWS.items():  # pure python: 320x180 crop at centre, x36 pixels
        x0, y0 = W // 2 - 160, H // 2 - 90
        t, img = timed(lambda: render_py(view, x0=x0, y0=y0), runs=1)
        d = float(np.abs(img.astype(int) - ref[v][y0:y0 + 180, x0:x0 + 320].astype(int)).mean())
        det = bool((render_py(view, x0=x0, y0=y0) == img).all())
        res[f"python/{v}"] = dict(s_crop=round(t, 3), s_est=round(t * 36, 1), diff=round(d, 3), det=det)
        print("python", v, res[f"python/{v}"], flush=True)

    def gpu(name, mk):
        try:
            r = mk()
        except Exception as e:
            res[name] = dict(error=f"{type(e).__name__}: {e}"[:300]); print(name, res[name]); return
        for v, view in VIEWS.items():
            try:
                t, img = timed(lambda: r.render(view))
                Image.fromarray(img).save(OUT / f"{name.replace('/', '_')}_{v}.png")
                d = float(np.abs(img.astype(int) - ref[v].astype(int)).mean())
                same = bool((r.render(view) == img).all())
                res[f"{name}/{v}"] = dict(s=round(t, 4), diff=round(d, 3), det=same,
                                          gpu=getattr(r, "renderer", "?"))
                if isinstance(r, Browser):
                    t2, _ = timed(lambda: r.render(view, grab=False))
                    res[f"{name}/{v}"]["s_no_transfer"] = round(t2, 4)
            except Exception as e:
                res[f"{name}/{v}"] = dict(error=f"{type(e).__name__}: {e}"[:300])
            print(name, v, res[f"{name}/{v}"], flush=True)
        if hasattr(r, "close"):
            r.close()

    gpu("moderngl_f32", lambda: ModernGL(False))
    gpu("moderngl_f64", lambda: ModernGL(True))
    gpu("wgpu_f32", WGPU)
    gpu("webgl2_edge", Browser)
    (OUT / "results.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
