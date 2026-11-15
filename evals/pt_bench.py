"""Path-tracer proof run for fw.py 3d --pt: determinism, noise vs samples, timing, comparison sheet.

python evals/pt_bench.py OUT_DIR  -> OUT_DIR/pt_bench.json, sheet-pt-vs-default.jpg, pairs/*.jpg
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fw_3d  # noqa: E402


def recipe(formula, samples=None, size=512, seed=1):
    r = fw_3d.default_recipe(formula)
    r["size"] = {"w": size, "h": size}
    if samples:
        r["pt"] = {"samples": samples, "seed": seed}
    return fw_3d.normalise(r)


def main(out):
    out = Path(out)
    (out / "pairs").mkdir(parents=True, exist_ok=True)
    b = fw_3d.Browser3D()
    res = {"renderer": b.renderer}
    try:
        a1, _ = b.render(recipe("mandelbulb", 16))
        a2, _ = b.render(recipe("mandelbulb", 16))
        a3, _ = b.render(recipe("mandelbulb", 16, seed=2))
        res["determinism"] = {"same_seed_identical": bool((a1 == a2).all()),
                              "other_seed_changed_px": int((a1 != a3).any(2).sum())}
        ref, tref = b.render_linear(recipe("mandelbulb", 1024))
        res["reference"] = {"samples": 1024, "seconds": round(tref, 2)}
        noise = []
        for n in (4, 16, 64, 256):
            img, dt = b.render_linear(recipe("mandelbulb", n, seed=7))
            rmse = float(np.sqrt(((np.clip(img, 0, 4) - np.clip(ref, 0, 4)) ** 2).mean()))
            noise.append({"samples": n, "rmse": rmse, "seconds": round(dt, 2)})
        for x in noise:
            x["rmse_x_sqrtN"] = round(x["rmse"] * x["samples"] ** 0.5, 4)
            x["rmse"] = round(x["rmse"], 5)
        res["noise"] = noise
        timing = []
        for f in ("mandelbulb", "quatjulia", "menger"):
            for n in (64, 256):
                _, dt = b.render(recipe(f, n))
                timing.append({"formula": f, "samples": n, "size": 512, "seconds": round(dt, 2)})
            _, dt = b.render(recipe(f))
            timing.append({"formula": f, "samples": 0, "size": 512, "seconds": round(dt, 2), "route": "default"})
        res["timing"] = timing
        cells = []
        for f in ("mandelbulb", "quatjulia", "menger"):
            d, _ = b.render(recipe(f, size=768))
            p, _ = b.render(recipe(f, 256, size=768))
            fw_3d._save_jpeg(d, out / "pairs" / f"{f}-default.jpg", 90)
            fw_3d._save_jpeg(p, out / "pairs" / f"{f}-pt256.jpg", 90)
            cells += [(f"{f} default (shadow+ao+camera)", d), (f"{f} path traced 256 spp", p)]
        fw_3d._sheet(cells, out / "sheet-pt-vs-default.jpg", cols=2, scale=0.5)
    finally:
        b.close()
    (out / "pt_bench.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "pt_bench_out")
