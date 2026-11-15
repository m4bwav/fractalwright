# fractalwright design note (Step C)

Date: 2026-11-14. Machine: Windows 11, RTX 5060 Ti, Python 3.14.6. Benchmark: [bench/bench.py](../../bench/bench.py), raw numbers in `bench/out/results.json` (not committed; rerun with `bench/.venv/Scripts/python bench/bench.py`).

## 1. Measured render core

Same job for every candidate: Mandelbrot, 1920x1080, 1000 max iterations, smooth colouring (bailout radius 256, cosine palette), two views: **full** (centre -0.75,0, width 3.5) and **deep** (centre -0.7436447860,0.1318252536, width 1e-4, about 3.5e4 zoom). Time is the median of 3 warm runs and includes reading the pixels back to Python. Diff is the mean absolute pixel difference (0-255 per channel) against the NumPy float64 render. Determinism: each candidate rendered each view twice; all gave identical pixels.

| Candidate | Full view | Deep view | Diff full / deep | Deterministic | Install added (venv) | Outputs one code path serves |
|---|---|---|---|---|---|---|
| (a) pure Python stdlib | ~133 s (320x180 crop 3.7 s x36) | ~38 s (crop 1.07 s x36) | 0.0 / 0.52 (crop) | yes | 0 MB | stills only (video impractical) |
| (b) NumPy float64 (reference) | 5.9-6.7 s | 3.9-4.7 s | ref | yes | ~59 MB (numpy 38 + libs 21) | stills, video frames (slow), measure |
| (c) moderngl GLSL float32 | 0.0026 s | 0.0029 s | 0.27 / **21.3** | yes | ~1 MB (moderngl + glcontext) | stills, video frames; shader text reusable in the page |
| (c) moderngl GLSL float64 (`#version 400`, `double`) | 0.030 s | 0.030 s | 0.03 / **0.32** | yes | same | stills, video frames, deep zoom to ~1e13 |
| (d) wgpu-py WGSL float32 (no f64 in WGSL) | 0.0106 s | 0.0105 s | 0.26 / 21.2 | yes | ~13 MB (wgpu 11 + cffi etc.) | stills, video frames; WGSL also runs in a WebGPU page |
| (e) Playwright + headless system **Edge**, WebGL2 float32 | 0.195 s (0.004 s draw only) | 0.200 s (0.004 s) | 0.27 / 21.2 | yes | 118 MB (playwright pip incl. its Node driver); 0 MB browser (Edge ships with Windows) | all five: stills, video frames, interactive page, audio page, 3D raymarch, one shader |

Pillow (17 MB) is needed by every route for PNG out. Chromium was not downloaded: system Edge (`channel="msedge"`) ran headless on the real GPU through ANGLE/D3D11, so the Playwright Chromium download (not measured; documented around 100-150 MB) is unnecessary on Windows. On macOS/Linux, `channel="chrome"` covers an installed Chrome.

Findings:

- GPUs are 200-2000x faster than NumPy. The time of the browser route is almost all the base64 pixel transfer (0.19 s of 0.20 s); the draw itself matches moderngl.
- float32 is broken at 3.5e4 zoom already (diff 21, visible blockiness), which agrees with [references/03-deep-zoom.md](../../references/03-deep-zoom.md) (float32 plain-iteration limit ~1e4-1e5). Any float32 route needs perturbation (reference orbit in float64 or arbitrary precision on the CPU, float32 deltas on the GPU) past ~1e4.
- Desktop GLSL `double` on this NVIDIA card is ~10x slower than float32 but still 0.03 s per 1080p frame and matches NumPy (diff 0.3 is log/cos rounding at band edges). WebGL and WGSL have no double.
- Pure Python is ~20x slower than NumPy; usable only as a no-dependency fallback for thumbnails and for `measure` on small grids.

## 2. Decision

**Core: NumPy float64 on the CPU** is the one required dependency (with Pillow). It is the reference renderer every other route is checked against, it does `measure`, and it renders any still with no GPU. Pure Python stays as the last fallback for `doctor` and tiny previews only.

**Accelerators, optional and probed in this order** (`fw.py doctor` reports which are present; a missing one is never an error):

1. **Headless browser (Playwright + system Edge/Chrome), WebGL2.** First choice because one GLSL shader file serves stills, video frames, the interactive page (`serve`), the audio page and the 3D raymarcher; the interactive page is the product the user sees anyway. Frames read back with `toDataURL`/binary transfer; batch many frames per evaluate to amortise the 0.19 s transfer.
2. **moderngl** (1 MB) for float64 stills and zoom video to ~1e13 without perturbation, and as the fast offline path when no browser is found. The GLSL body is shared with the page (only the precision type changes).
3. **wgpu-py**: not adopted. It adds 13 MB, has no f64, and gives nothing moderngl and the browser do not already give. Revisit only if WebGPU compute (flames, buddhabrot histograms) needs atomics the browser path lacks.
4. **ComfyUI hosts** for AI styling passes only, never for the fractal maths.

Precision routing: width/pixel > ~1e-7 (zoom < 1e4) any float32 route; up to ~1e13 moderngl double or NumPy; beyond that perturbation with a NumPy/mpmath reference orbit and GPU deltas (Step D, after the plain path is proven). Every GPU result can be spot-checked against NumPy with the same diff metric used here (pass bar: mean diff < 1.0).

## 3. Recipe file (one JSON per render)

Enough to redraw the picture exactly. Centre and width are decimal strings so deep zooms keep every digit; floats elsewhere.

```json
{
  "fractalwright": "0.1.0",
  "family": "escape-time",
  "formula": "mandelbrot",
  "params": {"power": 2, "bailout": 256, "max_iter": 1000},
  "view": {"centre": ["-0.7436447860", "0.1318252536"], "width": "1e-4", "rotation_deg": 0},
  "size": {"w": 1920, "h": 1080, "supersample": 1},
  "colouring": {"method": "smooth", "density": 0.02, "inside": "#000000"},
  "palette": {"type": "cosine", "a": [0.5,0.5,0.5], "b": [0.5,0.5,0.5], "c": [1,1,1], "d": [0.0,0.33,0.67]},
  "seed": 0,
  "render": {"route": "numpy", "precision": "float64"},
  "ai_pass": null
}
```

Fields: `family` (escape-time, flame, lsystem, ifs, attractor, 3d-de, and any neighbour admitted below), `formula` (named preset or formula id), `params` (formula-specific; julia adds `c` as two decimal strings), `palette` (`cosine`, `stops` with colour/position list, or a named preset), `seed` (for anything random: flames, noise, jitter), `render.route` is a hint, not a requirement; the redraw may use any route that meets the precision. `ai_pass` holds a ComfyUI workflow name, model, prompt, seed and denoise when styling was applied. Animation recipes (`zoom`, `morph`, `loop`, `audio`) add `keyframes` (list of views with times), `fps`, `duration_s` and, for audio, `audio` (file hash and band mapping).

## 4. Scope edges (Mark's answers, 2026-11-14)

| Neighbour | Ruling | Note |
|---|---|---|
| Escape-time, flames/IFS, L-systems, attractors, 3D DE, noise as fractal terrain | in | the plugin's core per Step A |
| Reaction-diffusion (Gray-Scott) | **in**, as a GPU preset | same shader/page machinery |
| Cellular automata (elementary rules, Life, Lenia) | **in** (Mark overruled the guess "out") | build after the escape-time video path; Rule 90 = Sierpinski ties it to `measure` |
| Tilings (Penrose, Truchet, hyperbolic) | **in** (overruled "out") | self-similar substitution tilings; `measure` must say they are not fractal in the box-count sense |
| Kleinian limit sets (Indra's Pearls) | **in v1** (overruled "later") | Indra's Pearls (book #7) is the reference; wanted |

## 5. Commands mapped to the core

| Command | Core path |
|---|---|
| `doctor` | probes numpy, Pillow, moderngl (float64 support), Playwright + Edge/Chrome, ffmpeg, ComfyUI hosts |
| `explain` | text from `references/` and `kb/`; no rendering |
| `identify` | NumPy feature measures (box-count dimension, symmetry, colour stats) against kb signatures |
| `measure` | NumPy float64 only (reference numbers: Mandelbrot area ~1.5066, Sierpinski log3/log2, Koch log4/log3) |
| `render`, `palette`, `sheet` | browser or moderngl by precision; NumPy fallback; Pillow for sheets |
| `zoom`, `morph`, `loop` | GPU frames (browser batch or moderngl double), ffmpeg encode; perturbation past 1e13 |
| `serve`, `export` | the WebGL2 page itself; `export` writes the recipe JSON |
| `audio` + live page | browser page stepped frame by frame from analysed audio (NumPy FFT); live page uses WebAudio |
| `flame`, `lsystem` | NumPy (histogram/turtle) first; GPU later if slow |
| 3D (Step E) | the browser page raymarching a DE shader |

## 6. Settled choices (askwright set fractalwright-scope-2026-11-14, closed)

1. Name: fractalwright.
2. Repository: public from the first commit.
3. Neighbours: all four in (above).
4. AI styling: **off by default since 2026-11-14** (Mark compared the AI-styled zoom with the exact one, askwright set fractalwright-ai-look-2026-11-14, and chose exact; `--ai` turns it on). Original ruling: on by default for video (`zoom`, `morph`, `loop`, `audio`) when a ComfyUI host is reachable; stills stay exact by default. `--no-ai` gives the exact video; the exact frames are always kept beside the styled file, and the styled file and recipe are marked interpreted (`ai_pass` filled). No host reachable: exact video, with a note, never an error.
5. Playwright + system Edge is the first optional accelerator.
