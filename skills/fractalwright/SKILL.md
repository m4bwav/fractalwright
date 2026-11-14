---
name: fractalwright
description: "Render, explain, measure and animate fractals as reproducible recipes: Mandelbrot, Julia, Burning Ship, Tricorn and Multibrot stills from a recipe JSON or preset with smooth colouring and palettes, box-counting dimension and Mandelbrot area measured against known values, plain explanations of each family. Use whenever the user wants a fractal image or wallpaper, asks 'render a Mandelbrot', 'make a Julia set', 'what is the Burning Ship', 'what is the fractal dimension of this picture', 'measure this coastline', 'fractal palette', or wants to redraw a fractal exactly. Also 'refresh fractalwright'. Not for general shaders (threewright) or pixel art (pixelwright)."
license: MIT
metadata:
  version: 0.1.0
---

# fractalwright

Outcome: every picture is a PNG with a recipe JSON next to it that redraws it pixel for pixel. Numbers (dimension, area, symmetry) are measured, never guessed.

`FW` means `python scripts/fw.py` from the repository root (run it, do not read it).

## Step 0: freshness and tools

Read `evergreen.json` at the repository root. If `contradiction` is set or today is on or after `next_due`, say so in one line, do the task, then run `evergreen-refresh`. Run `FW doctor` once per machine: NumPy is the core; moderngl, Playwright and ffmpeg are optional and only probed.

## Step 1: pick the family

`FW explain <family>` gives the formula, how it is made and the presets. Families: mandelbrot, julia, burning-ship, tricorn, multibrot, kronecker (exact grid fractals: `FW render kronecker-carpet`, or `--mask 111,101,111 --power 6`). Read [references/02-escape-time.md](../../references/02-escape-time.md) only when the user asks for depth or a colouring method beyond smooth.

## Step 2: render

`FW render <preset or recipe.json> -o out.png [--size WxH] [--iter N] [--palette NAME] [--supersample 2]`. It writes `out.png` and `out.json`. Confirm both files exist before reporting. To change a view, edit the recipe's `view.centre` and `view.width` (decimal strings, keep every digit) and render the recipe again. `FW palette` lists palettes; `FW palette NAME -o swatch.png` shows one. Past a width of about 1e-13 float64 fails; say so instead of rendering noise ([references/03-deep-zoom.md](../../references/03-deep-zoom.md)).

## Step 2b: sheets and video

`FW sheet <recipe> --palettes A,B,C` or `--vary params.max_iter --values 100,300,1000` (complex values as `re:im`) writes a labelled contact sheet PNG and a JSON with each tile's recipe. Video: `FW zoom <recipe> --to-width W [--from-width W0] [--to-centre re,im]` (exponential width, eased centre), `FW morph <recipe> --path "re,im;re,im"` (julia c by default, `--vary` for another param), `FW loop <recipe> --circle re,im,r [--phase]` (closed path, last frame wraps to the first). All take `--size WxH --fps N --duration S`, write exact frames in `<out>_frames/`, an H.264 mp4 (yuv420p, CRF 18) and `<out>.json` with `animation` (keyframes, fps, duration_s). AI styling is on by default (`--no-ai` to skip): today it only probes ComfyUI and records `ai_pass: pending-not-implemented`; the exact video is always the delivered file. Every video gets a flash check; `FW flashcheck <video or frame dir>` runs it alone and exits 4 above 3 luminance swings (10% of full range) per second. Report a failure, never ship it ([references/09](../../references/09-audio-visuals.md)).

## Step 3: measure

- `FW measure box image.png [--invert] [--threshold T]`: box-counting dimension of the dark (or light) pixels over 15+ box sizes and seeded random offsets, with the fit range in decades, the local-slope curve and a verdict. Pass the verdict on as written: under two decades it is "descriptor only"; a drifting local slope is "not fractal". Give D with its error bar from [references/08-measuring.md](../../references/08-measuring.md), never as exact, and never name a shape from D.
- `FW measure lacunarity image.png`: gappiness per box size, the second number beside D (same D can look different).
- `FW measure ifs --ratios 0.5,0.5,0.5`: similarity dimension; exact only when the pieces do not overlap, else an upper bound.
- Height profiles and heightmaps are self-affine: `FW measure profile numbers.txt` (spectral slope, semivariogram, Katz) and `FW measure heightmap map.png|.npy` (radial spectrum, surface D = 3 - H). `measure box` refuses a numbers file.
- `FW measure katz curve.txt` (x,y or one column): a cheap roughness number, not D.
- `FW measure area --size 1024`: Mandelbrot area by pixel count (proven within 0.0002 of 1.50659 at 1024 px).

## Step 4: identify

`FW identify <preset | recipe.json | image.png> [--c re,im]`: hand-built features (mirror symmetry of the pixels, Julia connected or dust from the orbit of 0, main cardioid or period-2 bulb for c, the family's known symmetry). An image's box D is reported as a descriptor only. Never identify a fractal by its dimension.

## Maintenance

Unit files at the repository root: `evergreen.json`, `RESEARCH.md`, `CHANGELOG.md`, `LEARNINGS.md`, `TESTS.md`. Beat `fractal-art` feeds refreshes; `harvest.json` lists harvest targets.
