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

`FW explain <family>` gives the formula, how it is made and the presets. Families: mandelbrot, julia, burning-ship, tricorn, multibrot. Read [references/02-escape-time.md](../../references/02-escape-time.md) only when the user asks for depth or a colouring method beyond smooth.

## Step 2: render

`FW render <preset or recipe.json> -o out.png [--size WxH] [--iter N] [--palette NAME] [--supersample 2]`. It writes `out.png` and `out.json`. Confirm both files exist before reporting. To change a view, edit the recipe's `view.centre` and `view.width` (decimal strings, keep every digit) and render the recipe again. `FW palette` lists palettes; `FW palette NAME -o swatch.png` shows one. Past a width of about 1e-13 float64 fails; say so instead of rendering noise ([references/03-deep-zoom.md](../../references/03-deep-zoom.md)).

## Step 3: measure

- `FW measure box image.png [--invert] [--threshold T]`: box-counting dimension of the dark (or light) pixels. Give the result with its error bar from [references/08-measuring.md](../../references/08-measuring.md) (about +-0.02 to 0.05 on a clean 1-2k px render), never as exact.
- `FW measure area --size 1024`: Mandelbrot area by pixel count (proven within 0.0002 of 1.50659 at 1024 px).

## Maintenance

Unit files at the repository root: `evergreen.json`, `RESEARCH.md`, `CHANGELOG.md`, `LEARNINGS.md`, `TESTS.md`. Beat `fractal-art` feeds refreshes; `harvest.json` lists harvest targets.
