"""AI styling pass for fractalwright videos: per-frame img2img through ComfyUI, then temporal smoothing.

The exact frames stay untouched. The pass writes <out>_ai.mp4 and <out>_ai_frames/, and returns the
ai_pass block for the recipe (model, licence class, denoise, seed, smoothing, timings). Standard library + NumPy.

Route: Z-Image Turbo img2img (Apache 2.0, open weights, commercial use allowed), one fixed seed for every frame,
low denoise, then an exponential moving average over the residual (styled minus exact), so the geometry moves
exactly with the maths and only the added texture is smoothed in time. No Krea 2, no Meta-gated models.
"""
import io
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import numpy as np

MODEL = {"name": "Z-Image Turbo", "unet": "z_image_turbo_bf16.safetensors", "clip": "qwen_3_4b.safetensors",
         "clip_type": "lumina2", "vae": "ae.safetensors", "licence": "Apache-2.0",
         "licence_class": "open weights, commercial use allowed"}
DEFAULT_PROMPT = ("the same fractal image, rich painterly texture, subtle film grain, soft glow, "
                  "fine detail, same colours and composition")
DEFAULT_DENOISE = 0.3
DEFAULT_SEED = 7
DEFAULT_SMOOTH = 0.5  # EMA weight of the current frame's residual


def build_workflow(image_name, prompt=DEFAULT_PROMPT, seed=DEFAULT_SEED, denoise=DEFAULT_DENOISE, steps=9,
                   prefix="fw_ai"):
    """ComfyUI API graph: LoadImage -> VAEEncode -> KSampler(denoise) -> VAEDecode -> SaveImage."""
    if not 0 < denoise <= 1:
        raise ValueError("denoise must be in (0, 1]")
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": MODEL["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": MODEL["clip"], "type": MODEL["clip_type"]}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": MODEL["vae"]}},
        "4": {"class_type": "LoadImage", "inputs": {"image": image_name}},
        "5": {"class_type": "VAEEncode", "inputs": {"pixels": ["4", 0], "vae": ["3", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["2", 0]}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["6", 0], "negative": ["7", 0],
                                                   "latent_image": ["5", 0], "seed": int(seed), "steps": int(steps),
                                                   "cfg": 1.0, "sampler_name": "res_multistep",
                                                   "scheduler": "simple", "denoise": float(denoise)}},
        "9": {"class_type": "VAEDecode", "inputs": {"samples": ["8", 0], "vae": ["3", 0]}},
        "10": {"class_type": "SaveImage", "inputs": {"images": ["9", 0], "filename_prefix": prefix}},
    }


def smooth_residuals(exact, styled, alpha=DEFAULT_SMOOTH):
    """out_i = exact_i + r_i, r_i = alpha*(styled_i - exact_i) + (1-alpha)*r_{i-1}. Arrays float 0..1."""
    out, r = [], None
    for e, s in zip(exact, styled):
        d = s - e
        r = d if r is None else alpha * d + (1 - alpha) * r
        out.append(np.clip(e + r, 0, 1))
    return out


def flicker(frames):
    """Mean abs diff between neighbouring frames, 0..255 scale."""
    if len(frames) < 2:
        return 0.0
    return float(np.mean([np.abs(frames[i + 1] - frames[i]).mean() for i in range(len(frames) - 1)]) * 255)


def _upload(host, path):
    boundary = uuid.uuid4().hex
    name = f"fw_{uuid.uuid4().hex[:8]}_{Path(path).name}"
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
            f"Content-Type: image/png\r\n\r\n").encode() + Path(path).read_bytes() + \
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"http://{host}/upload/image", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["name"]


def _queue(host, graph):
    req = urllib.request.Request(f"http://{host}/prompt", data=json.dumps({"prompt": graph}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["prompt_id"]


def _wait(host, pid, deadline):
    """Poll history; a busy GPU just means we wait in its queue (never cancel anything)."""
    while time.time() < deadline:
        with urllib.request.urlopen(f"http://{host}/history/{pid}", timeout=30) as r:
            h = json.loads(r.read())
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error on {pid}: {st.get('messages')}")
            for node in h[pid].get("outputs", {}).values():
                for im in node.get("images", []):
                    q = urllib.parse.urlencode({"filename": im["filename"], "subfolder": im["subfolder"],
                                                "type": im["type"]})
                    with urllib.request.urlopen(f"http://{host}/view?{q}", timeout=60) as v:
                        return v.read()
        time.sleep(1.0)
    raise TimeoutError(f"ComfyUI prompt {pid} not done before the deadline")


def run_pass(host, frame_dir, out, fps, prompt=DEFAULT_PROMPT, seed=DEFAULT_SEED, denoise=DEFAULT_DENOISE,
             alpha=DEFAULT_SMOOTH, timeout_s=None):
    """Style every exact frame, smooth, encode <out stem>_ai.mp4. Returns the ai_pass dict."""
    from PIL import Image
    import fw
    t0 = time.time()
    timeout_s = timeout_s or float(os.environ.get("FW_AI_TIMEOUT_S", "1800"))
    deadline = t0 + timeout_s
    frames = sorted(Path(frame_dir).glob("*.png"))
    pids = []
    for p in frames:  # queue all first so ComfyUI keeps the model loaded
        name = _upload(host, p)
        pids.append(_queue(host, build_workflow(name, prompt, seed, denoise)))
    exact, styled = [], []
    for p, pid in zip(frames, pids):
        e = Image.open(p).convert("RGB")
        s = Image.open(io.BytesIO(_wait(host, pid, deadline))).convert("RGB")
        if s.size != e.size:
            s = s.resize(e.size, Image.LANCZOS)
        exact.append(np.asarray(e, dtype=np.float64) / 255)
        styled.append(np.asarray(s, dtype=np.float64) / 255)
    t_gen = time.time() - t0
    final = smooth_residuals(exact, styled, alpha)
    out = Path(out)
    adir = out.with_name(out.stem + "_ai_frames")
    adir.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(final):
        fw.write_png(adir / f"f_{i:05d}.png", arr=(f * 255 + 0.5).astype(np.uint8))
    aout = out.with_name(out.stem + "_ai.mp4")
    fw.encode_mp4(adir, fps, aout)
    fc = fw.flash_check(final, fps)
    return {"status": "applied", "interpreted": True, "host": host, "route": "img2img per frame + residual EMA",
            "model": MODEL["name"], "files": {k: MODEL[k] for k in ("unet", "clip", "vae")},
            "licence": MODEL["licence"], "licence_class": MODEL["licence_class"], "prompt": prompt,
            "seed": int(seed), "denoise": float(denoise), "steps": 9, "cfg": 1.0, "smooth_alpha": float(alpha),
            "video": aout.name, "frame_dir": adir.name, "frames": len(final),
            "seconds": round(time.time() - t0, 1), "seconds_generate": round(t_gen, 1),
            "flicker": {"exact": round(flicker(exact), 3), "styled_raw": round(flicker(styled), 3),
                        "styled": round(flicker(final), 3)},
            "flash": {"pass": fc["pass"], "max_swings_per_s": fc["max_swings_per_s"]}}


def apply(rec, notes, frame_dir, out, fps, ai=True, **kw):
    """Shared hook for zoom/morph/loop/audio: fill rec['ai_pass'] and notes. Never raises on host trouble."""
    import fw
    if not ai:
        notes.append("AI styling off (--no-ai): exact video")
        return
    host = fw.probe_comfy()
    if not host:
        notes.append("AI styling: no ComfyUI host reachable, exact video kept")
        return
    try:
        rec["ai_pass"] = run_pass(host, frame_dir, out, fps, **kw)
        ap = rec["ai_pass"]
        notes.append(f"AI styling: {ap['model']} img2img on {host} (denoise {ap['denoise']}, seed {ap['seed']}) "
                     f"-> {ap['video']}; interpreted, exact video and frames kept")
    except Exception as ex:  # noqa: BLE001
        rec["ai_pass"] = {"status": "failed", "host": host, "error": str(ex)[:300]}
        notes.append(f"AI styling failed on {host} ({ex.__class__.__name__}); exact video kept")


def add_args(s):
    """--ai-prompt/--ai-denoise/--ai-seed for zoom, morph, loop and audio."""
    s.add_argument("--ai-prompt", default=DEFAULT_PROMPT, help="img2img prompt for the AI pass")
    s.add_argument("--ai-denoise", type=float, default=DEFAULT_DENOISE, help="img2img denoise in (0, 1] (default 0.3)")
    s.add_argument("--ai-seed", type=int, default=DEFAULT_SEED, help="sampler seed, the same for every frame")


def kw_from(a):
    """argparse namespace -> run_pass keywords; validates denoise before any frame renders."""
    d = float(getattr(a, "ai_denoise", DEFAULT_DENOISE))
    if not 0 < d <= 1:
        raise SystemExit("--ai-denoise must be in (0, 1]")
    return {"prompt": getattr(a, "ai_prompt", DEFAULT_PROMPT), "denoise": d,
            "seed": int(getattr(a, "ai_seed", DEFAULT_SEED))}


def write_ai_recipe(rec, out):
    """Second recipe beside the styled video, marked interpreted. Only when the pass applied."""
    ap = rec.get("ai_pass") or {}
    if ap.get("status") != "applied":
        return None
    r = dict(rec, interpreted=True, exact_recipe=Path(out).with_suffix(".json").name)
    p = Path(out).with_name(Path(out).stem + "_ai.json")
    p.write_text(json.dumps(r, indent=2) + "\n", encoding="utf-8")
    return p
