"""AI styling pass (fw_ai.py) without a GPU: workflow builder, smoothing, no-host fallback, a fake ComfyUI.

Run: python -m unittest discover -s tests -v
"""
import http.server
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fw  # noqa: E402
import fw_ai  # noqa: E402


def fake_comfy(full=True):
    """full=True: upload/prompt/history/view echo the uploaded PNG back. False: only /system_stats answers."""
    store = {}

    class H(http.server.BaseHTTPRequestHandler):
        def _send(self, body, ctype="application/json", code=200):
            self.send_response(code); self.send_header("Content-Type", ctype); self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/system_stats"):
                return self._send(b"{}")
            if not full:
                return self._send(b"{}", code=404)
            if self.path.startswith("/history/"):
                pid = self.path.rsplit("/", 1)[1]
                img = store["prompts"][pid]
                return self._send(json.dumps({pid: {"status": {"status_str": "success"}, "outputs": {
                    "10": {"images": [{"filename": img, "subfolder": "", "type": "output"}]}}}}).encode())
            if self.path.startswith("/view"):
                name = re.search(r"filename=([^&]+)", self.path).group(1)
                return self._send(store["files"][name], "image/png")
            self._send(b"{}", code=404)

        def do_POST(self):
            if not full:
                return self._send(b"{}", code=500)
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if self.path == "/upload/image":
                name = re.search(rb'filename="([^"]+)"', body).group(1).decode()
                start = body.index(b"\r\n\r\n") + 4
                end = body.index(b"\r\n--", start)
                store.setdefault("files", {})[name] = body[start:end]
                return self._send(json.dumps({"name": name}).encode())
            if self.path == "/prompt":
                g = json.loads(body)["prompt"]
                pid = f"p{len(store.setdefault('prompts', {}))}"
                store["prompts"][pid] = g["4"]["inputs"]["image"]
                return self._send(json.dumps({"prompt_id": pid}).encode())
            self._send(b"{}", code=404)

        def log_message(self, *a):
            pass
    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"127.0.0.1:{srv.server_address[1]}"


class Hosts:
    def __init__(self, value):
        self.value, self.old = value, None

    def __enter__(self):
        self.old = os.environ.get("FW_COMFY_HOSTS")
        os.environ["FW_COMFY_HOSTS"] = self.value

    def __exit__(self, *a):
        if self.old is None:
            os.environ.pop("FW_COMFY_HOSTS", None)
        else:
            os.environ["FW_COMFY_HOSTS"] = self.old


class TestAiPass(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls.tmp.name)
        r = fw.load_recipe("julia-rabbit")
        r["size"]["w"], r["size"]["h"] = 64, 48
        r["params"]["max_iter"] = 100
        cls.recs = fw.loop_frames(fw.normalise(r), 4, phase=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_workflow_builder(self):
        g = fw_ai.build_workflow("in.png", prompt="p", seed=11, denoise=0.25)
        ks = g["8"]["inputs"]
        self.assertEqual((ks["seed"], ks["denoise"], ks["cfg"], ks["steps"]), (11, 0.25, 1.0, 9))
        self.assertEqual(g["4"]["inputs"]["image"], "in.png")
        self.assertEqual(g["5"]["inputs"]["pixels"], ["4", 0])
        self.assertEqual(ks["latent_image"], ["5", 0])
        self.assertEqual(g["2"]["inputs"]["type"], "lumina2")
        text = json.dumps(g).lower()
        self.assertNotIn("krea", text)
        self.assertNotIn("sam3", text)
        self.assertEqual(fw_ai.MODEL["licence"], "Apache-2.0")
        for bad in (0, 1.5):
            with self.assertRaises(ValueError):
                fw_ai.build_workflow("x.png", denoise=bad)

    def test_smoothing_keeps_geometry_and_cuts_flicker(self):
        rng = np.random.default_rng(0)
        exact = [np.full((8, 8, 3), 0.5)] * 12
        styled = [np.clip(e + rng.normal(0, 0.05, e.shape), 0, 1) for e in exact]
        same = fw_ai.smooth_residuals(exact, styled, alpha=1.0)
        self.assertTrue(all(np.allclose(a, b) for a, b in zip(same, styled)))
        sm = fw_ai.smooth_residuals(exact, styled, alpha=0.5)
        self.assertLess(fw_ai.flicker(sm), fw_ai.flicker(styled))
        const = [e + 0.1 for e in exact]
        self.assertTrue(all(np.allclose(a, c) for a, c in zip(fw_ai.smooth_residuals(exact, const), const)))

    def test_no_host_fallback(self):
        with Hosts(""):
            rp, notes = fw.write_video("loop", self.recs, {"fps": 4, "duration_s": 1}, self.dir / "nohost.mp4")
        rec = json.loads(rp.read_text(encoding="utf-8"))
        self.assertIsNone(rec["ai_pass"])
        self.assertIn("no ComfyUI host", " ".join(notes))
        self.assertFalse((self.dir / "nohost_ai.mp4").exists())
        self.assertTrue((self.dir / "nohost.mp4").exists())

    def test_fake_host_applies_pass(self):
        srv, host = fake_comfy()
        try:
            with Hosts(host):
                rp, notes = fw.write_video("loop", self.recs, {"fps": 4, "duration_s": 1}, self.dir / "ai.mp4")
        finally:
            srv.shutdown()
        rec = json.loads(rp.read_text(encoding="utf-8"))
        ap = rec["ai_pass"]
        self.assertEqual(ap["status"], "applied")
        self.assertEqual((ap["model"], ap["licence"], ap["seed"], ap["denoise"]),
                         ("Z-Image Turbo", "Apache-2.0", fw_ai.DEFAULT_SEED, fw_ai.DEFAULT_DENOISE))
        self.assertTrue((self.dir / "ai.mp4").exists())
        self.assertTrue((self.dir / "ai_ai.mp4").exists())
        self.assertEqual(len(list((self.dir / "ai_frames").glob("*.png"))), 4)
        self.assertEqual(len(list((self.dir / "ai_ai_frames").glob("*.png"))), 4)
        side = json.loads((self.dir / "ai_ai.json").read_text(encoding="utf-8"))
        self.assertTrue(side["interpreted"])
        # echo server: styled == exact, so the residual is zero and flicker matches the exact frames
        self.assertAlmostEqual(ap["flicker"]["styled"], ap["flicker"]["exact"], delta=0.01)

    def test_broken_host_keeps_exact(self):
        srv, host = fake_comfy(full=False)
        try:
            with Hosts(host):
                rp, notes = fw.write_video("loop", self.recs, {"fps": 4, "duration_s": 1}, self.dir / "bad.mp4")
        finally:
            srv.shutdown()
        rec = json.loads(rp.read_text(encoding="utf-8"))
        self.assertEqual(rec["ai_pass"]["status"], "failed")
        self.assertTrue((self.dir / "bad.mp4").exists())
        self.assertFalse((self.dir / "bad_ai.json").exists())


if __name__ == "__main__":
    unittest.main()
