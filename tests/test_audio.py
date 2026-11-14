"""fw.py audio and the live audio page: proof bars from refs/09 (bands in order, calm silence, beats on the frame,
flash limit, A/V sync, identical reruns). Test audio is made in code and kept short. Needs ffmpeg; skips without."""
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.request
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import fw  # noqa: E402
import fw_audio  # noqa: E402
import fw_serve  # noqa: E402

HAVE_FF = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
NEEDS_FF = unittest.skipUnless(HAVE_FF, "ffmpeg not on PATH")
RATE = 22050


def write_wav(path, x, rate=RATE):
    x = np.clip(np.asarray(x), -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((x * 32000).astype("<i2").tobytes())
    return path


def sweep(seconds=4.0, f0=40.0, f1=8000.0):
    t = np.arange(int(seconds * RATE)) / RATE
    k = math.log(f1 / f0)
    return 0.5 * np.sin(2 * np.pi * f0 * seconds / k * (np.exp(t * k / seconds) - 1))


def clicks(seconds=4.0, period=0.5):
    t = np.arange(int(seconds * RATE)) / RATE
    return np.where((t % period) < 0.01, 0.8 * np.sin(2 * np.pi * 1000 * t), 0.0)


def noise_bursts(seconds=3.0, rate_hz=10.0, burst=0.05, seed=0):
    t = np.arange(int(seconds * RATE)) / RATE
    rng = np.random.default_rng(seed)
    return np.where((t % (1 / rate_hz)) < burst, rng.uniform(-0.9, 0.9, len(t)), 0.0)


def small(preset="julia-pulse", w=64, h=36):
    r = fw._merge(fw.default_recipe(), json.loads(json.dumps(fw_audio.AUDIO_PRESETS[preset]["recipe"])))
    r["size"]["w"], r["size"]["h"] = w, h
    r["params"]["max_iter"] = 120
    return fw.normalise(r)


class Env:
    """Run with the internal fallback, or with a given mw.py."""

    def __init__(self, mw):
        self.mw, self.old = mw, None

    def __enter__(self):
        self.old = os.environ.get("FW_MUSICWRIGHT")
        os.environ["FW_MUSICWRIGHT"] = str(self.mw) if self.mw else "none"

    def __exit__(self, *a):
        if self.old is None:
            os.environ.pop("FW_MUSICWRIGHT", None)
        else:
            os.environ["FW_MUSICWRIGHT"] = self.old


def sources():
    """Internal always; musicwright too when an mw.py with `envelopes` is found."""
    out = [None]
    mw = fw_audio.find_musicwright()
    if mw and "envelopes" in Path(mw).read_text(encoding="utf-8", errors="replace"):
        out.append(mw)
    return out


@NEEDS_FF
class AudioProofs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="fw_audio_"))
        cls.sweep = write_wav(cls.tmp / "sweep.wav", sweep())
        cls.clicks = write_wav(cls.tmp / "clicks.wav", clicks())
        cls.silence = write_wav(cls.tmp / "silence.wav", np.zeros(int(1.5 * RATE)))
        cls.strobe = write_wav(cls.tmp / "strobe.wav", noise_bursts())
        cls.srcs = sources()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def env(self, song, fps, mw):
        with Env(mw):
            e, note = fw_audio.envelopes(song, fps)
        self.assertIn("musicwright" if mw else "internal", note)
        return e

    def test_sweep_lights_bands_in_order(self):
        # Proof bar: the dominant driver (0 bass, 1 mid, 2 treb) never steps back during a rising sweep.
        for mw in self.srcs:
            with self.subTest(source="musicwright" if mw else "internal"):
                d = fw_audio.drivers(self.env(self.sweep, 30, mw))
                dom = np.argmax(np.stack([d["bass"], d["mid"], d["treb"]]), axis=0)[3:-3]
                self.assertTrue(np.all(np.diff(dom) >= 0), dom.tolist())
                self.assertEqual((dom[0], dom[-1]), (0, 2))

    def test_silence_gives_a_calm_frame(self):
        # Proof bar: every pixel's variance over time under 1e-6 (measured 0.0: nothing moves without sound).
        with Env(None):
            e, _ = fw_audio.envelopes(self.silence, 12)
        recs = fw_audio.frame_recipes(small(), "julia-pulse", fw_audio.drivers(e), 12)
        frames, lim, _, _ = fw_audio.render_frames(recs, 12, "numpy")
        stack = np.stack(frames).astype(float) / 255
        self.assertLess(float(stack.var(axis=0).max()), 1e-6)
        self.assertEqual(lim.damped, 0)

    def test_click_beats_land_within_one_frame(self):
        # Proof bar: each beat accent peaks within one frame of a click at 30 fps.
        fps = 30
        for mw in self.srcs:
            with self.subTest(source="musicwright" if mw else "internal"):
                d = fw_audio.drivers(self.env(self.clicks, fps, mw))
                acc = d["beat"]
                peaks = [i for i in range(len(acc)) if acc[i] == 1.0]
                self.assertGreaterEqual(len(peaks), 6, peaks)
                for p in peaks:
                    self.assertLessEqual(abs(p - round(p / (0.5 * fps)) * 0.5 * fps), 1, peaks)

    def test_flash_limit_on_a_strobe(self):
        # Proof bar: <= 3 swings/s after the limiter, on a white-noise burst train at full intensity and on a
        # black/white frame strobe (15 swings/s raw at 30 fps).
        with Env(None):
            e, _ = fw_audio.envelopes(self.strobe, 30)
        recs = fw_audio.frame_recipes(small(), "julia-pulse", fw_audio.drivers(e), 30, intensity=1.0)
        frames, _, _, _ = fw_audio.render_frames(recs, 30, "numpy")
        fc = fw.flash_check([f / 255 for f in frames], 30)
        self.assertLessEqual(fc["max_swings_per_s"], 3, fc)
        raw = [np.full((8, 8, 3), 255 * (i % 2), np.uint8) for i in range(60)]
        self.assertGreater(fw.flash_check([f / 255 for f in raw], 30)["max_swings_per_s"], 3)
        lim = fw_audio.FlashLimiter(30)
        out = [lim(f) for f in raw]
        fc2 = fw.flash_check([f / 255 for f in out], 30)
        self.assertLessEqual(fc2["max_swings_per_s"], 3, fc2)
        self.assertGreater(lim.damped, 0)

    def test_av_duration_and_identical_reruns(self):
        # Proof bars: video and audio streams within one frame of each other and of frames/fps; reruns identical.
        song = write_wav(self.tmp / "short.wav", 0.6 * clicks(1.5) + 0.2 * sweep(1.5))
        outs = []
        for k in range(2):
            out = self.tmp / f"av{k}.mp4"
            with Env(None):
                code = fw.main(["audio", str(song), "-o", str(out), "--size", "64x36", "--fps", "12", "--iter", "100",
                                "--route", "numpy", "--no-ai"])
            self.assertEqual(code, 0)
            outs.append(out)
        rec = json.loads(outs[0].with_suffix(".json").read_text(encoding="utf-8"))
        n, fps = rec["animation"]["frames"], 12
        self.assertEqual(n, math.floor(1.5 * fps))
        d = fw_audio.stream_durations(outs[0])
        self.assertLessEqual(abs(d["video"] - n / fps), 1 / fps, d)
        self.assertLessEqual(abs(d["audio"] - d["video"]), 1 / fps, d)
        self.assertTrue(rec["animation"]["flash"]["check"]["pass"])
        self.assertEqual(rec["animation"]["audio"]["envelopes"], "musicwright not found; internal fallback")
        a = sorted((self.tmp / "av0_frames").glob("*.png"))
        b = sorted((self.tmp / "av1_frames").glob("*.png"))
        self.assertEqual(len(a), n)
        self.assertTrue(all(x.read_bytes() == y.read_bytes() for x, y in zip(a, b)))

    def test_mp3_is_refused(self):
        mp3 = self.tmp / "x.mp3"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(self.silence), str(mp3)], check=True)
        with Env(None), self.assertRaises(SystemExit):
            fw_audio.envelopes(mp3, 12)


class LivePage(unittest.TestCase):
    def test_served_on_loopback_with_analyser_and_limiter(self):
        srv = fw_serve.make_server("127.0.0.1", 0, tempfile.mkdtemp())
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            html = urllib.request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/audio", timeout=5).read().decode()
        finally:
            srv.shutdown()
            srv.server_close()
        for needle in ("createAnalyser", "smoothingTimeConstant = 0", "getUserMedia", "autoGainControl: false",
                       "limitedDraw", "Photosensitivity warning", "uniform vec2 u_k"):
            self.assertIn(needle, html)
        with self.assertRaises(ValueError):
            fw_serve.make_server("0.0.0.0", 0, ".")

    def test_page_constants_match_python(self):
        html = (ROOT / "scripts" / "page" / "audio.html").read_text(encoding="utf-8")
        for name in ("ATTACK_S", "RELEASE_S", "HUE_TAU_S", "BEAT_DECAY_S", "BEAT_MIN_GAP_S", "BASS_HZ", "TREB_HZ"):
            m = re.search(rf"\b{name} = ([0-9.]+)", html)
            self.assertIsNotNone(m, name)
            self.assertAlmostEqual(float(m.group(1)), float(getattr(fw_audio, name)), msg=name)
        self.assertIn(f"FLASH_SWING = {fw.FLASH_SWING:.2f}", html)
        self.assertIn(f"FLASH_MAX_PER_S = {fw.FLASH_MAX_PER_S}", html)
        for p, cfg in fw_audio.AUDIO_PRESETS.items():
            self.assertIn(f'"{p}"', html)
            for k in ("c_radius", "zoom_kick", "mid_drift", "treb_density", "dive"):
                self.assertRegex(html, rf'"{p}".*\b{k}: {re.escape(format(cfg[k], "g"))}\b', msg=(p, k))


if __name__ == "__main__":
    unittest.main()
