---
name: fractalwright
description: "Render, animate, measure and identify fractals as reproducible recipes (PNG or mp4 plus a recipe JSON that redraws it): Mandelbrot, Julia, Burning Ship and Multibrot stills, deep zooms, zoom, morph and loop videos with a flash check, audio-reactive music videos and visualizers from a song, fractal flames, IFS, L-systems, strange attractors, fBm terrain, box-counting dimension. Use whenever the user wants a fractal image, wallpaper or video, asks 'render a Mandelbrot zoom', 'make a fractal flame', 'winamp-style visualizer for this song', 'what fractal is this picture', 'measure the fractal dimension of this coastline', or wants to redraw a fractal exactly. Also 'refresh fractalwright'. Not for general shaders (threewright), mastering music (musicwright) or pixel art (pixelwright)."
license: MIT
metadata:
  version: 0.10.0
---

# fractalwright

Outcome: every picture is a PNG with a recipe JSON next to it that redraws it pixel for pixel. Numbers (dimension, area, symmetry) are measured, never guessed.

`FW` means `python scripts/fw.py` from the repository root (run it, do not read it).

## Step 0: tools

Run the task straight away. Run `FW doctor` only when a command fails for a missing tool (NumPy is the core; moderngl, Playwright and ffmpeg are optional and only probed). Freshness (`evergreen.json`) is read on 'refresh fractalwright', not on every use. Render the preset as given; tune the look (iterations, density, supersample) only when asked.

## Step 1: pick the family

`FW explain <family>` gives the formula, how it is made and the presets. Families: mandelbrot, julia, burning-ship, tricorn, multibrot, kronecker (exact grid fractals: `FW render kronecker-carpet`, or `--mask 111,101,111 --power 6`). New to chaos: `FW explain logistic` gives the teaching order, `--plot cobweb|bifurcation -o out.png` draws it; `FW explain coastline` explains D by Richardson's rulers. Read [references/02-escape-time.md](../../references/02-escape-time.md) only when the user asks for depth or a colouring method beyond smooth.

## Step 2: render

`FW render <preset or recipe.json> -o out.png [--size WxH] [--iter N] [--palette NAME] [--supersample 2]`. It writes `out.png` and `out.json`. Confirm both files exist before reporting. To change a view, edit the recipe's `view.centre` and `view.width` (decimal strings, keep every digit) and render the recipe again. `FW palette` lists palettes; `FW palette NAME -o swatch.png` shows one. Past a width of about 1e-13 float64 fails; say so instead of rendering noise ([references/03-deep-zoom.md](../../references/03-deep-zoom.md)).

## Step 2a: explore

`FW serve [--port 8765] [--out-dir DIR] [--open]` runs the WebGL2 explorer on 127.0.0.1 only (any other host is refused). Drag pans, wheel or pinch zooms, shift-click picks Julia `c`; formula, iterations, rotation (`[` and `]` turn 15 degrees) and palette sit in the side panel; recipes with stop palettes (up to 8 stops) travel in the hash as `ps=pos:rrggbb,...`. The URL hash is the whole view, so the address is a share link. A precision box warns when float32 nears its limit; past it, Mandelbrot and Julia (power 2, width >= 1e-60) switch to GPU deep: the page posts the view to `/orbit`, the server computes the Decimal reference orbit, and the page draws it with the double-float perturbation shader (centre strings keep every digit while zooming); Render exact asks the server for a NumPy (or perturbation) PNG of the same view, Export writes a recipe JSON to the out dir. `FW export "<share url or #hash>" -o recipe.json` does the same from the command line. `--route browser` renders with headless Edge and the page shader; `--deep --route browser` (or any width under 1e-12) runs double-float perturbation on the GPU down to width 1e-60 (0.1-1% count differences), so use the CPU route when exact counts matter. Details (fallbacks, `--gpu-precision float32`, burning ship): [references/13-route-details.md](../../references/13-route-details.md).

## Step 2b: sheets and video

`FW audio <song.wav> [--preset julia-pulse|mandel-dive] [--recipe R] [--size 640x360] [--fps 30] [--duration S] [--intensity 0.6] [--route auto|browser|numpy]` makes a music video: song envelopes drive the fractal (bass, beats, mids, chroma, treble, loudness; nothing moves in silence), frames pass a flash limiter, flashcheck gates the result (exit 4 on a fail), and the song is muxed in. MP3 is refused unless `--allow-mp3`. `FW serve` also serves `/audio`, a live page. Mapping detail: [references/13-route-details.md](../../references/13-route-details.md).

`FW sheet <recipe> --palettes A,B,C` or `--vary params.max_iter --values 100,300,1000` (complex values as `re:im`) writes a labelled contact sheet PNG and a JSON with each tile's recipe. Video: `FW zoom <recipe> --to-width W [--from-width W0] [--to-centre re,im]` (exponential width, eased centre), `FW morph <recipe> --path "re,im;re,im"` (julia c by default, `--vary` for another param), `FW loop <recipe> --circle re,im,r [--phase]` (closed path, last frame wraps to the first). All take `--size WxH --fps N --duration S`, write exact frames in `<out>_frames/`, an H.264 mp4 (yuv420p, CRF 18) and `<out>.json` with `animation` (keyframes, fps, duration_s). AI styling is off by default; `--ai` adds a ComfyUI Z-Image img2img copy (`<out>_ai.*`, marked `interpreted`) and always keeps the exact video ([references/13-route-details.md](../../references/13-route-details.md)). Every video gets a flash check; `FW flashcheck <video or frame dir>` runs it alone and exits 4 when flashes of 10% luminance (or saturated red) happen more than 3 times a second together over more than 25% of a 10-degree field; the verdict line names the failed rule and its area (the whole-frame swings/s is for reference only, so "1 swings/s" does not mean a pass or a fail). Report a failure, never ship it ([references/09](../../references/09-audio-visuals.md)).

## Step 2c: IFS, attractors, terrain, interpolation

`FW ifs sierpinski|fern|unequal-tiles -o out.png` (chaos game, p by |det|, first 20 points dropped, framed by a ball that provably holds the attractor). `FW attractor-search --hits 5 -o best.png` (Sprott quadratic maps ranked by D2 1.1-1.5 and small L, a book rule; Lyapunov in bits). `FW terrain -o t.png [--method midpoint] [--H 0.8]` (spectral by default; midpoint creases measured) writes a PNG and `.npy`. `FW fif --points "0,0;1,1;2,0" --d 0.5,-0.5 -o f.png [--numbers y.txt]` draws a fractal interpolation curve through the points.

## Step 2d: flames, L-systems, attractors

`FW flame [sierpinski|swirl-sierpinski|recipe.json] -o f.png [--seed N --tries 24]` (chaos game over xforms, 12 Draves-Reckase variations, final xform, colour blending, log-density with gamma and vibrancy, supersample 2, density estimation; no preset = seeded random flames scored on coverage, best kept). `FW lsystem koch|koch-snowflake|dragon|hilbert|sierpinski-arrowhead|plant-a|plant-b|plant-d|plant-e|plant-f|plant-stochastic -o p.png [--n N --seed N]` writes PNG, SVG and recipe. `FW attractor clifford|dejong|icon|icon-3|icon-halloween|icon-clam|icon-streamers|icon-flower|lorenz|chen|lu|multiscroll -o a.png [--params a,b,c,d] [--search]` (icons from Symmetry in Chaos Table A.1; multiscroll params are Yalcin's a, Mx, Nx) (density shading; search ranks random Clifford or de Jong sets by Sprott's rule). Every command writes a recipe JSON that redraws it.

## Step 2f: neighbours (not all fractal)

`FW rd coral|mitosis|default [--f F --k K --steps N --seed N]` (Gray-Scott). `FW ca 90|30|B3/S23 [--steps N]` (elementary rule or Life-like). `FW tiling square|triangle|hex|penrose [--n N]`. `FW kleinian apollonian|grandma [--ta T --tb T]` (Apollonian gasket, or a two-generator limit set from Grandma's recipe drawn by the book's depth-first word search; `--method random` for inverse iteration). Each writes a PNG and recipe. Say plainly that reaction-diffusion and tilings are not fractals; `FW measure box` on a tiling says "not fractal" ([references/12-neighbours.md](../../references/12-neighbours.md)).

## Step 2e: 3D

`FW 3d render mandelbulb|mandelbox|quatjulia|menger|hybrid [--view whole|close] [--remedy ao|shadow|fog|trap|dof|aa|camera|all|none] -o x.png` (sphere-traced DE in headless Edge; writes the recipe with the camera made explicit). Default look since 0.8.0: path traced at 256 samples (sky + sun, about 0.5-2 s) with a composed camera (40 mm, low angle, subject on the left third); `--pt 0` gives the fast shadow + ambient occlusion look, which suits boxy Menger-like forms better; a recipe file keeps its own setting. `--remedy` adds to the shadow/ao look, `--remedy none` clears it first. Leave fog and dof off unless asked: fog washed the subject out in the look gate and dof blurs close views. `FW 3d recipe ...` prints the recipe; `FW 3d gate -o DIR` renders the remedy matrix and sheets. Browser route only, no NumPy fallback. A normal route since the 3D look gate (2026-11-14). `--pt N [--bounces 2] [--seed 1]` sets the samples (same seed, same pixels; 512 px at 256 spp in 0.5-1.8 s); see references/07-3d.md. Printable mesh: `FW 3d mesh <formula|recipe> [--size-mm 60] [--res 200] [--engine auto|skimage|numpy] [--wall-mm 0.9] -o x.stl` samples the same DE in NumPy and writes one watertight solid as binary STL in mm (sidecar JSON: triangles, shells, volume, time; exit 3 if not watertight). Menger defaults to level 3 for printing. `--wall-mm X` meshes the offset surface DE = t (t = X/2 at print scale) so thin parts thicken toward X mm; 0.9 cleared the Mandelbulb FDM thin-wall warning (2.7% -> 0.1% under 0.9 mm). Multi-colour: `-o x.3mf` (or `--colors N`, default 4, max 8; `--palette "#hex,..."`) also writes a 3MF coloured by the orbit trap (equal-surface bins, one filament each; Bambu Studio and PrusaSlicer read the per-triangle filament tags). Then `pw.py check x.stl --target print-fdm` (polywright-print; it reads the 3MF too).

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
