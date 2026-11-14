"""fw.py audio: a song in, a frame-stepped fractal video out, with the song muxed in sync.

Envelopes come from musicwright (`mw.py envelopes`, the owner of audio analysis); when musicwright is absent or
too old, a small internal NumPy fallback measures the same fields. Frames are rendered one at a time at
t = n / fps (never real-time capture), by the browser shader when available, else NumPy. A flash limiter damps
any frame that would push the large-area luminance swings past 3 per second, and flashcheck gates the result.
The live page (`/audio` on `fw.py serve`) runs the same mappings on the Web Audio analyser.
"""
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np


def _fw():
    m = sys.modules.get("fw")
    if m is None or not hasattr(m, "write_png"):
        m = sys.modules.get("__main__")
    if m is None or not hasattr(m, "write_png"):
        import fw as m  # noqa: F811
    return m


# Mapping constants, shared with page/audio.html (keep the two in step).
ATTACK_S = 0.02       # one-pole attack (refs/09 3.1: 10-30 ms)
RELEASE_S = 0.25      # one-pole release (refs/09 3.1: 150-400 ms; also a flash guard)
HUE_TAU_S = 1.0       # chroma-to-hue smoothing, slow so a key change reads as a colour change, not flicker
BEAT_DECAY_S = 0.2    # beat accent decay
BEAT_MIN_GAP_S = 0.34  # at most about 3 accents a second
BASS_HZ, TREB_HZ = 250.0, 4000.0  # driver split (refs/09 3.1 MilkDrop-style bands built from critical bands)

AUDIO_PRESETS = {
    "julia-pulse": {
        "doc": "bass swells the julia c radius, beats kick the zoom, mids drift the colour, chroma sets the hue",
        "recipe": {"formula": "julia", "params": {"c": ["-0.8", "0.156"], "max_iter": 300},
                   "view": {"centre": ["0", "0"], "width": "3.0"}},
        "c_radius": 0.05, "zoom_kick": 0.12, "mid_drift": 0.35, "treb_density": 0.4, "dive": 0.0,
    },
    "mandel-dive": {
        "doc": "the zoom travels with the loudness, bass pulses the scale, beats kick, chroma sets the hue",
        "recipe": {"formula": "mandelbrot", "params": {"max_iter": 400},
                   "view": {"centre": ["-0.7436447860", "0.1318252536"], "width": "0.05"}},
        "c_radius": 0.0, "zoom_kick": 0.10, "mid_drift": 0.25, "treb_density": 0.3, "dive": 0.6,
    },
}


# ---------------------------------------------------------------- envelopes
def find_musicwright():
    """Path to mw.py, or None. FW_MUSICWRIGHT=none forces the internal fallback; a path overrides the search."""
    env = os.environ.get("FW_MUSICWRIGHT")
    if env is not None:
        return None if env.strip().lower() in ("", "none", "off") else (Path(env) if Path(env).is_file() else None)
    here = Path(__file__).resolve()
    cands = [here.parents[2] / "musicwright" / "skills" / "musicwright" / "scripts" / "mw.py"]
    ip = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    try:
        data = json.loads(ip.read_text(encoding="utf-8"))
        for key, rows in (data.get("plugins") or {}).items():
            if key.split("@")[0] == "musicwright":
                for row in rows if isinstance(rows, list) else [rows]:
                    cands.append(Path(row.get("installPath", "")) / "skills" / "musicwright" / "scripts" / "mw.py")
    except (OSError, ValueError, AttributeError):
        pass
    for c in cands:
        if c.is_file():
            return c
    return None


def envelopes(song, fps, bands="critical", allow_mp3=False):
    """-> (envelope dict, source note). musicwright first, internal NumPy fallback second."""
    mw = find_musicwright()
    if mw is not None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "env.json"
            cmd = [sys.executable, str(mw), "envelopes", str(song), "--fps", str(fps), "--bands", str(bands), "--json", str(out)]
            if allow_mp3:
                cmd.append("--allow-mp3")
            p = subprocess.run(cmd, capture_output=True, text=True)
            try:
                res = json.loads(p.stdout or "{}")
            except ValueError:
                res = {}
            if res.get("ok") and out.is_file():
                return json.loads(out.read_text(encoding="utf-8")), f"musicwright ({mw})"
            if "MP3" in str(res.get("error", "")):
                raise SystemExit(f"{res['error']}; {res.get('fix', '')}")
            note = f"musicwright at {mw} has no usable envelopes command ({(res.get('error') or p.stderr.strip()[-120:] or 'no output')}); internal fallback"
    else:
        note = "musicwright not found; internal fallback"
    if Path(song).suffix.lower() == ".mp3" and not allow_mp3:
        raise SystemExit("refusing to measure an MP3 (encoder delay and lowpass shift the bands); use the WAV or FLAC, or pass --allow-mp3")
    return internal_envelopes(song, fps), note


BARK = [20, 100, 200, 300, 400, 510, 630, 770, 920, 1080, 1270, 1480, 1720, 2000, 2320, 2700, 3150, 3700, 4400,
        5300, 6400, 7700, 9500]


def decode(song, rate=22050):
    ff = shutil.which("ffmpeg")
    if not ff:
        raise SystemExit("ffmpeg not on PATH: needed to decode the song")
    raw = subprocess.run([ff, "-v", "error", "-i", str(song), "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, "<f4").astype(np.float64)


def internal_envelopes(song, fps, rate=22050):
    """Minimal stand-in for mw.py envelopes: critical bands, 200 ms loudness, flux onsets, beats, chroma."""
    x = decode(song, rate)
    n_fft = 2048  # 93 ms at 22.05 kHz: long enough for the 20-100 Hz band
    frames = max(1, int(math.floor(len(x) / rate * fps + 1e-9)))
    win = np.hanning(n_fft + 1)[:-1]
    pad = np.concatenate([np.zeros(n_fft), x, np.zeros(n_fft)])
    freqs = np.fft.rfftfreq(n_fft, 1 / rate)
    edges = [(BARK[i], BARK[i + 1]) for i in range(len(BARK) - 1)]
    sel = [(freqs >= lo) & (freqs < hi) for lo, hi in edges]
    pcs = np.round(69 + 12 * np.log2(np.maximum(freqs, 1) / 440.0)).astype(int) % 12
    cmask = (freqs >= 65) & (freqs <= 2000)
    E, L, F, C = [], [], [], []
    prev = None
    sq = np.concatenate([[0.0], np.cumsum(x * x)])
    half = int(0.1 * rate)
    for f in range(frames):
        c = int(f / fps * rate)
        seg = pad[c + n_fft - n_fft // 2: c + n_fft + n_fft // 2] * win
        ps = np.abs(np.fft.rfft(seg)) ** 2
        E.append([10 * math.log10(ps[s].sum() / (n_fft * n_fft / 4) + 1e-12) for s in sel])
        a0, a1 = max(0, c - half), min(len(x), c + half)
        L.append(10 * math.log10((sq[a1] - sq[a0]) / max(1, a1 - a0) + 1e-12))
        lm = np.log1p(1000 * ps[1:])
        F.append(0.0 if prev is None else float(np.maximum(0, lm - prev).sum()))
        prev = lm
        ch = np.bincount(pcs[cmask], weights=ps[cmask], minlength=12)
        C.append((ch / ch.max()).round(3).tolist() if ch.max() > 1e-9 else [0.0] * 12)
    E = np.array(E)
    peaks = E.max(axis=0)
    floor = np.maximum(peaks - 60, -100)
    norm = np.where(peaks > -100, np.clip((E - floor) / 60, 0, 1), 0.0)
    F = np.array(F)
    onsets = []
    if F.max() > 1e-6:
        h = max(1, int(0.5 * fps))
        for i in range(1, frames - 1):
            v = F[i]
            if v >= 0.1 * F.max() and v >= F[i - 1] and v >= F[i + 1] and v >= np.median(F[max(0, i - h):i + h + 1]) + 0.05 * F.max():
                if not onsets or i - onsets[-1] >= max(1, int(0.05 * fps)):
                    onsets.append(i)
    return {"fps": fps, "frames": frames, "duration_s": round(len(x) / rate, 4),
            "bands": [{"lo_hz": lo, "hi_hz": hi} for lo, hi in edges], "energy": norm.round(3).tolist(),
            "loudness": np.clip((np.array(L) + 60) / 60, 0, 1).round(3).tolist(), "loudness_window_ms": 200,
            "onsets": [i / fps for i in onsets], "beats": [i / fps for i in onsets], "chroma": C,
            "notes": "internal fallback: beats are the onsets (no tempo tracking)"}


# ---------------------------------------------------------------- mapping
def one_pole(x, fps, attack_s=ATTACK_S, release_s=RELEASE_S):
    a_up, a_dn = math.exp(-1 / max(1e-9, attack_s * fps)), math.exp(-1 / max(1e-9, release_s * fps))
    y, out = 0.0, []
    for v in x:
        k = a_up if v > y else a_dn
        y = k * y + (1 - k) * v
        out.append(y)
    return np.array(out)


def _spread(v):
    """Song-level 5th-95th percentile to 0..1 (offline sees the whole song); flat inputs stay as they are."""
    lo, hi = np.percentile(v, 5), np.percentile(v, 95)
    if hi - lo < 0.05:
        return np.clip(v, 0, 1)
    return np.clip((v - lo) / (hi - lo), 0, 1)


def drivers(env):
    """Envelope dict -> per-frame drivers: bass, mid, treb (smoothed 0..1), beat accent, hue (0..1), loud."""
    fps = env["fps"]
    E = np.array(env["energy"], dtype=float).reshape(env["frames"], -1)
    centres = np.array([math.sqrt(max(b["lo_hz"], 1) * b["hi_hz"]) for b in env["bands"]])
    groups = {"bass": centres < BASS_HZ, "mid": (centres >= BASS_HZ) & (centres < TREB_HZ), "treb": centres >= TREB_HZ}
    d = {}
    for k, m in groups.items():
        raw = E[:, m].mean(axis=1) if m.any() else np.zeros(len(E))
        d[k] = one_pole(_spread(raw), fps)
    n = len(E)
    acc = np.zeros(n)
    last = -1e9
    for b in env.get("beats") or []:
        i = int(round(b * fps))
        if 0 <= i < n and (i - last) / fps >= BEAT_MIN_GAP_S:
            last = i
            j = np.arange(i, n)
            acc[i:] = np.maximum(acc[i:], np.exp(-(j - i) / (BEAT_DECAY_S * fps)))
    d["beat"] = acc
    ch = np.array(env["chroma"], dtype=float).reshape(n, 12)
    ang = 2 * np.pi * np.arange(12) / 12
    vx, vy = (ch * np.cos(ang)).sum(1), (ch * np.sin(ang)).sum(1)
    sx = one_pole(vx, fps, HUE_TAU_S, HUE_TAU_S) if n else vx
    sy = one_pole(vy, fps, HUE_TAU_S, HUE_TAU_S) if n else vy
    hue, h = np.zeros(n), 0.0
    for i in range(n):
        if math.hypot(sx[i], sy[i]) > 1e-3:
            h = (math.atan2(sy[i], sx[i]) / (2 * math.pi)) % 1.0
        hue[i] = h
    d["hue"] = hue
    d["loud"] = one_pole(np.array(env.get("loudness") or [0.0] * n, dtype=float), fps)
    return d


def frame_recipes(base, preset, d, fps, intensity=0.6):
    """Drivers -> one recipe per frame. Every change is audio-driven: silence gives a still picture."""
    from decimal import Decimal
    P = AUDIO_PRESETS[preset]
    n = len(d["bass"])
    c0 = [float(Decimal(v)) for v in base["params"].get("c", ["0", "0"])]
    w0 = float(Decimal(base["view"]["width"]))
    ph0 = float(base["colouring"].get("phase", 0) or 0)
    den0 = float(base["colouring"].get("density", 0.02))
    k = float(intensity)
    drift = np.cumsum(d["mid"]) * P["mid_drift"] * k / fps
    dive = np.cumsum(d["loud"]) * P["dive"] * k / fps  # e-folds of zoom travelled, only while sound plays
    out = []
    for i in range(n):
        r = json.loads(json.dumps(base))
        if base["formula"] == "julia" and P["c_radius"]:
            s = 1 + P["c_radius"] * k * float(d["bass"][i])
            r["params"]["c"] = [repr(c0[0] * s), repr(c0[1] * s)]
        w = float(w0 * math.exp(-dive[i]) / (1 + P["zoom_kick"] * k * (d["beat"][i] + 0.5 * d["bass"][i])))
        r["view"]["width"] = repr(w)
        r["colouring"]["phase"] = round(float((ph0 + d["hue"][i] + drift[i]) % 1.0), 6)
        r["colouring"]["density"] = float(den0 * (1 + P["treb_density"] * k * d["treb"][i]))
        out.append(r)
    return out


# ---------------------------------------------------------------- flash limiter
class FlashLimiter:
    """Mirrors the whole-frame swing walk of fw.flash_check (stricter than its area rule) and blends a frame back toward the last output frame whenever
    keeping it would complete a swing while the last second already holds `allowed` swings."""

    def __init__(self, fps, allowed=None):
        fw = _fw()
        self.swing = fw.FLASH_SWING
        self.allowed = fw.FLASH_MAX_PER_S - 1 if allowed is None else allowed  # one in hand for video coding
        self.win = max(1, int(round(fps)))
        self.swings, self.i, self.prev = [], 0, None
        self.lo = self.hi = None
        self.dir = 0
        self.damped = 0

    def _lum(self, f):
        return float(_fw().rel_luminance(f.astype(np.float64) / 255).mean())

    def _step(self, x, commit):
        lo, hi, d = self.lo, self.hi, self.dir
        hit = False
        if d == 0:
            lo, hi = min(lo, x), max(hi, x)
            if x - lo >= self.swing:
                hit, d, hi = True, 1, x
            elif hi - x >= self.swing:
                hit, d, lo = True, -1, x
        elif d > 0:
            if x > hi:
                hi = x
            elif hi - x >= self.swing:
                hit, d, lo = True, -1, x
        else:
            if x < lo:
                lo = x
            elif x - lo >= self.swing:
                hit, d, hi = True, 1, x
        if commit:
            self.lo, self.hi, self.dir = lo, hi, d
            if hit:
                self.swings.append(self.i)
        return hit

    def __call__(self, frame):
        frame = np.asarray(frame, dtype=np.uint8)
        if self.prev is None:
            x = self._lum(frame)
            self.lo = self.hi = x
            self.prev, self.i = frame, 1
            return frame
        recent = sum(1 for s in self.swings if s > self.i - self.win)
        x = self._lum(frame)
        out = frame
        if recent >= self.allowed and self._step(x, False):
            prev = self.prev.astype(np.float64)
            lo_a, hi_a, best = 0.0, 1.0, self.prev
            for _ in range(12):
                a = (lo_a + hi_a) / 2
                cand = np.clip(prev + (frame.astype(np.float64) - prev) * a + 0.5, 0, 255).astype(np.uint8)
                if self._step(self._lum(cand), False):
                    hi_a = a
                else:
                    lo_a, best = a, cand
            out = best
            self.damped += 1
            x = self._lum(out)
        self._step(x, True)
        self.prev = out
        self.i += 1
        return out


# ---------------------------------------------------------------- render
class Renderer:
    def __init__(self, route, sample):
        self.route, self.b, self.note = "numpy", None, None
        if route in ("auto", "browser"):
            try:
                import fw_serve
                if not fw_serve.float32_ok(sample):
                    raise RuntimeError("float32 cannot hold this view")
                self.b = fw_serve.Browser()
                self.route = "browser"
            except Exception as e:  # noqa: BLE001
                if route == "browser":
                    raise SystemExit(f"browser route unavailable: {str(e).splitlines()[0][:160]}")
                self.note = f"browser route unavailable ({str(e).splitlines()[0][:100]}); NumPy"

    def __call__(self, r):
        fw = _fw()
        r = fw.normalise(r)
        if self.b is not None:
            return self.b.render(r)
        return np.asarray(fw.render_array(r), dtype=np.uint8)

    def close(self):
        if self.b is not None:
            self.b.close()


def render_frames(recipes, fps, route="numpy", frame_dir=None):
    """Render each recipe in order through the flash limiter. Returns (frames, limiter, route, note)."""
    fw = _fw()
    rnd = Renderer(route, fw.normalise(recipes[0]))
    lim = FlashLimiter(fps)
    frames = []
    try:
        for i, r in enumerate(recipes):
            f = lim(rnd(r))
            frames.append(f)
            if frame_dir is not None:
                fw.write_png(Path(frame_dir) / f"f_{i:05d}.png", arr=f)
    finally:
        rnd.close()
    return frames, lim, rnd.route, rnd.note


def mux(frame_dir, fps, n, song, out):
    ff = shutil.which("ffmpeg")
    if not ff:
        raise SystemExit("ffmpeg not on PATH: frames written, video skipped")
    subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(Path(frame_dir) / "f_%05d.png"),
                    "-i", str(song), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "18", "-r", str(fps), "-c:a", "aac", "-b:a", "192k", "-t", f"{n / fps:.6f}", str(out)],
                   check=True)


def stream_durations(path):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", str(path)],
                       capture_output=True, text=True, check=True)
    return {s["codec_type"]: float(s.get("duration") or 0) for s in json.loads(p.stdout)["streams"]}


def _sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_audio(a):
    fw = _fw()
    song = Path(a.song)
    if not song.is_file():
        raise SystemExit(f"no such file: {song}")
    import fw_ai
    fw_ai.kw_from(a)  # fail on a bad --ai-denoise before any frame renders
    P = AUDIO_PRESETS[a.preset]
    base = fw.load_recipe(a.recipe) if a.recipe else fw._merge(fw.default_recipe(), json.loads(json.dumps(P["recipe"])))
    if a.size:
        w, h = a.size.lower().split("x")
        base["size"]["w"], base["size"]["h"] = int(w), int(h)
    if a.iter:
        base["params"]["max_iter"] = a.iter
    if a.palette:
        base["palette"] = dict(fw.PALETTES[a.palette])
    base = fw.normalise(base)
    env, src = envelopes(song, a.fps, a.bands, a.allow_mp3)
    if a.duration:
        env = _cut(env, int(round(a.duration * a.fps)))
    d = drivers(env)
    recipes = frame_recipes(base, a.preset, d, a.fps, a.intensity)
    out = Path(a.out)
    fdir = out.with_name(out.stem + "_frames")
    if fdir.exists():
        shutil.rmtree(fdir)
    fdir.mkdir(parents=True)
    frames, lim, route, rnote = render_frames(recipes, a.fps, a.route, fdir)
    n = len(frames)
    mux(fdir, a.fps, n, song, out)
    fc = fw.flash_check([f.astype(np.float64) / 255 for f in frames], a.fps)
    dur = stream_durations(out)
    rec = json.loads(json.dumps(base))
    rec["animation"] = {"kind": "audio", "preset": a.preset, "fps": a.fps, "frames": n, "duration_s": n / a.fps,
                        "frame_dir": fdir.name, "intensity": a.intensity,
                        "mapping": {"bass": "julia c radius and zoom pulse", "mid": "colour phase drift",
                                    "treb": "palette density", "chroma": "hue", "beats": "zoom kick",
                                    "loudness": "zoom travel" if P["dive"] else "none",
                                    "attack_s": ATTACK_S, "release_s": RELEASE_S, "beat_min_gap_s": BEAT_MIN_GAP_S},
                        "audio": {"file": song.name, "sha256": _sha256(song), "envelopes": src, "bands": a.bands},
                        "flash": {"damped_frames": lim.damped, "check": fc}, "streams_s": dur}
    notes = [f"envelopes: {src}", f"route: {route}"] + ([rnote] if rnote else [])
    import fw_ai
    fw_ai.apply(rec, notes, fdir, out, a.fps, ai=a.ai, **fw_ai.kw_from(a))
    rec["notes"] = notes
    rp = out.with_suffix(".json")
    rp.write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    fw_ai.write_ai_recipe(rec, out)
    print(f"wrote {out}, {rp} and {n} frames")
    for s in notes:
        print("note:", s)
    print(f"flash limiter damped {lim.damped} frames; flashcheck: {fc['max_swings_per_s']} swings/s "
          f"(limit {fw.FLASH_MAX_PER_S}) {'pass' if fc['pass'] else 'FAIL'}")
    return 0 if fc["pass"] else 4


def _cut(env, n):
    n = max(1, min(n, env["frames"]))
    e = dict(env, frames=n, duration_s=n / env["fps"])
    for k in ("energy", "energy_db", "loudness", "loudness_db", "onset_strength", "chroma"):
        if k in e:
            e[k] = e[k][:n]
    for k in ("onsets", "beats"):
        e[k] = [t for t in e.get(k) or [] if t < n / env["fps"]]
    return e


def register(sub):
    s = sub.add_parser("audio", help="song -> frame-stepped fractal video driven by its bands, beats and chroma, muxed with the song")
    s.add_argument("song", help="WAV or FLAC (MP3 refused unless --allow-mp3)")
    s.add_argument("--preset", choices=list(AUDIO_PRESETS), default="julia-pulse")
    s.add_argument("--recipe", help="start from this preset or recipe.json instead of the audio preset's view")
    s.add_argument("-o", "--out", default="audio.mp4")
    s.add_argument("--size", default="640x360", help="WxH (even numbers for H.264)")
    s.add_argument("--iter", type=int)
    s.add_argument("--palette")
    s.add_argument("--fps", type=int, default=30)
    s.add_argument("--duration", type=float, help="render only the first N seconds")
    s.add_argument("--bands", default="critical")
    s.add_argument("--intensity", type=float, default=0.6, help="modulation depth 0..1 (the flash limiter still applies)")
    s.add_argument("--route", choices=["auto", "browser", "numpy"], default="auto")
    s.add_argument("--allow-mp3", action="store_true")
    s.add_argument("--ai", action=__import__("argparse").BooleanOptionalAction, default=True,
                   help="AI styling pass (default on): img2img via ComfyUI to <out>_ai.mp4; exact video always kept")
    import fw_ai
    fw_ai.add_args(s)
    s.set_defaults(fn=cmd_audio)
