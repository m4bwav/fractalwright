# Changelog: fractalwright

Every change to [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md) and its companions, newest first, each with the reason. Reasons cite findings in [RESEARCH.md](RESEARCH.md) (`R-`), lessons in [LEARNINGS.md](LEARNINGS.md) (`L-`), and test runs in [TESTS.md](TESTS.md) (`T-`). State in `evergreen.json`. Protocol: MAINTENANCE.md.

Entry shape: `### C-YYYYMMDD-n · date · one-line summary`, then `because:` (IDs or "user request"), `files:` (file and section), and a sentence on what changed. Cite section headings, not line numbers.

### C-20261114-12 · 2026-11-14 · neighbours: rd, ca, tiling, kleinian
- because: T-20261114-12, user request (Mark's scope answers: all neighbours in), references/12-neighbours.md
- files: scripts/fw_neighbours.py (new), scripts/fw.py (`main` registers it), tests/test_neighbours.py (new), references/12-neighbours.md (new), skills/fractalwright/SKILL.md (Step 2f), CODEMAP.md
- Gray-Scott with Karl Sims' presets, elementary and Life-like CA, regular and Penrose P3 tilings (measure says not fractal), Apollonian gasket and Grandma's recipe limit sets. Each writes a PNG and recipe.

### C-20261114-11 · 2026-11-14 · AI styling pass for video (replaces the pending stub)
- because: T-20261114-11, ai-docs/plans/design.md (Mark's ruling: AI styling on by default for video), references/10-ai-models.md
- files: scripts/fw_ai.py (new), scripts/fw.py (`write_video`, `--ai` help), scripts/fw_audio.py (AI block), tests/test_ai.py (new), tests/test_fw.py (old stub test removed), skills/fractalwright/SKILL.md (Video), CODEMAP.md
- Per-frame Z-Image Turbo img2img through ComfyUI at low denoise with a fixed seed, residual EMA for temporal consistency, second video and recipe marked interpreted. Exact frames kept; no host or a host error never fails the render.

### C-20261114-10 · 2026-11-14 · fw.py 3d: raymarched DE fractals, look gate (Step E)
- because: T-20261114-10, user request (Step E), references/07-3d.md sections 2-5, ai-docs/notes/2026-11-14-3d-gate.md
- files: scripts/fw_3d.py (new), scripts/page/fractal3d.frag (new), scripts/fw.py (`main` registers it; one doctor row), tests/test_3d.py (new), skills/fractalwright/SKILL.md (Step 2e), README.md, CODEMAP.md, ask/fractalwright-3d-gate-2026-11-14 (new)
- Own GLSL sphere tracer (Hart 1996) with Mandelbulb p8, Mandelbox, quaternion Julia, Menger, a box-fold/bulb hybrid; remedies ao, shadow, fog, trap, dof, aa, camera as switches. Browser route only, no NumPy fallback. Blind judge: shadow, AO and the composed camera beat the baseline; fog lost; status pending Mark's gate verdict.

### C-20261114-9 · 2026-11-14 · audio: song to fractal video, live audio page (Step D batch 4b)
- because: T-20261114-9, user request (Step D batch 4b), references/09 sections 3, 4, 5.3 and 8b
- files: scripts/fw_audio.py (new), scripts/page/audio.html (new), scripts/fw.py (`main` registers fw_audio), scripts/fw_serve.py (GET /audio), tests/test_audio.py (new), skills/fractalwright/SKILL.md (Step 2d), README.md, CODEMAP.md
- `fw.py audio <song>` takes per-frame envelopes from musicwright's `mw.py envelopes` (0.1.34; a NumPy fallback when musicwright is absent or older), maps bass to julia c radius and zoom pulse, mids to colour drift, chroma to hue, treble to palette density, beats to zoom kicks and loudness to zoom travel, with 20 ms attack and 250 ms release. Frames are stepped at n/fps, rendered by the browser shader or NumPy, passed through a flash limiter and gated by flashcheck; the song is muxed with ffmpeg and cut to the frame count. MP3 is refused unless `--allow-mp3`. `fw.py serve` also serves `/audio`: file or microphone through the Web Audio analyser, the same mappings and a JS flash limiter behind a photosensitivity warning.
### C-20261114-8 · 2026-11-14 · flame, lsystem, attractor (Step D batch 4c, fw_gen.py)
- because: T-20261114-8, user request (Step D batch 4c), design.md section 4 (all neighbours in)
- files: scripts/fw_gen.py (new), scripts/fw.py (`main` registers it), tests/test_gen.py (new), skills/fractalwright/SKILL.md (Step 2d), README.md, CODEMAP.md
- Flames reimplemented from the Draves and Reckase paper (no flam3 or Apophysis code, palettes are fw.py's own). Hilbert's B rule is `-AF+BFB+FA-`; a recalled `-FA+` ending broke the curve, caught by the visit-once test. Lorenz D2 needs the fit range 0.01-0.1 of the cloud (0.02-0.25 read 1.95). Icon parameter sets are recalled, checked bounded only. Multi-scroll attractor still left out: no primary-paper parameter set in hand.

### C-20261114-7 · 2026-11-14 · book items: logistic explain, attractor-search, ifs, terrain, fif (fw_extra.py)
- because: T-20261114-7, book verdicts in ai-docs/log.md (Feldman, Pickover ed., Mandelbrot FGoN, Steeb, Banerjee, Loy *Musimathics*)
- files: scripts/fw_extra.py (new), scripts/fw.py (`main` registers it), tests/test_extra.py (new), skills/fractalwright/SKILL.md (Steps 1, 2c), CODEMAP.md, references/01 (Richardson), 02 (Lyapunov units), 04 (|det| default, discard, ball cover), 05 (Sprott window, Henon checks, Euler and hyperchaos cautions), 06 (crease measurement, FIF and Weierstrass), 09 (section 8b audio design rules)
- Lyapunov exponents are now stated in bits (ln 2 nats = 1 bit at r = 4). New commands are checked against known answers; the Sprott preference window and the audio rules stay book rules, unverified. Tested and left out: Mariani-Silver fill (not pixel-identical), multi-scroll attractor (recalled parameters failed), grey-level IFS (cost); reasons in ai-docs/log.md.

### C-20261114-6 · 2026-11-14 · explorer: serve, export, render --route browser (Step D batch 4a)
- because: T-20261114-6, user request (Step D batch 4a), design.md section 2 (headless browser first accelerator)
- files: scripts/fw_serve.py (new), scripts/page/fractal.frag (new), scripts/page/explorer.html (new), scripts/fw.py (`serve`, `export`, `render --route`, `doctor` playwright row), tests/test_serve.py (new), skills/fractalwright/SKILL.md (Step 2a), README.md, CODEMAP.md
- A WebGL2 explorer served on 127.0.0.1 only, with the full view in the URL hash, Export (recipe JSON) and Render exact (server NumPy or perturbation PNG). The browser route renders through headless Edge with the page's own shader and falls back to NumPy for views float32 cannot hold. Recipe schema unchanged; exported recipes record `render.route: browser`.
### C-20261114-5 · 2026-11-14 · deep zoom by perturbation (fw_deep.py)
- because: T-20261114-5, user request (deep-zoom path)
- files: scripts/fw_deep.py (new), scripts/fw.py (`render` routing and `--deep`), tests/test_deep.py (new), references/03-deep-zoom.md (sections 2.3 and 4), CODEMAP.md
- Mandelbrot renders below width 1e-12 (or with `--deep`) use a Decimal reference orbit and float64 deltas with Zhuoran rebasing; mpmath is not needed. Proven to width 1e-30 against direct Decimal iteration. Widths under 1e-290 are refused (floatexp not built). Series and bilinear approximation not built.
### C-20261114-4 · 2026-11-14 · sheet, zoom, morph, loop, flashcheck (Step D batch 3)
- because: T-20261114-4, user request (continue prompt Step D batch 3), design.md section 6 (AI styling on by default for video)
- files: scripts/fw.py (video block, colouring.phase), tests/test_fw.py (Video), skills/fractalwright/SKILL.md (Step 2b), README.md, CODEMAP.md
- Contact sheets with a recipe per tile; keyframed zoom (exponential width, smoothstep centre), morph (piecewise linear param path), loop (closed path sampled at k/n, palette phase cycle); frames + H.264 mp4 (yuv420p, CRF 18) + animation recipe. `--ai/--no-ai` (default on) only probes ComfyUI (2 s timeout, FW_COMFY_HOSTS overrides) and records `ai_pass: pending-not-implemented`. `flashcheck` counts frame-mean relative-luminance swings of 10% per second (limit 3).

### C-20261114-3 · 2026-11-14 · measure v2 and identify v1 (book verdicts)
- because: R-20261114-3, T-20261114-3, user request (continue prompt Step D batch 2)
- files: scripts/fw.py (measure v2, self-affine, kronecker, identify blocks), tests/test_fw.py, skills/fractalwright/SKILL.md (Steps 1, 3, 4), references/08-measuring.md (sections 1, 2, 6, 7, 8, 10, 12), references/06-noise-natural.md (section 7)
- `measure box` now fits 16 geometric box sizes averaged over 8 seeded offsets, reports decades, local slopes and curvature, removes 1-2 px specks with a warning, and gives a verdict that refuses "fractal" under two decades or with a drifting local slope. New: `measure lacunarity|ifs|profile|katz|heightmap`, `identify`, the `kronecker` render family with three presets. Two unverified rows in references/06 section 7 are now checked by measurement.

### C-20261114-2 · 2026-11-14 · fw.py first batch: doctor, explain, render, measure, palette
- because: user request (continue prompt Step D), T-20261114-2
- files: scripts/fw.py, tests/test_fw.py, skills/fractalwright/SKILL.md
- NumPy float64 render of five escape-time families with smooth colouring and recipes saved next to each PNG; box-counting dimension; Mandelbrot area by pixel count.

### C-20261114-1 · 2026-11-14 · Created as an evergreen unit
- because: user request
- files: skills/fractalwright/SKILL.md, RESEARCH.md, LEARNINGS.md, evergreen.json (skills: also TESTS.md and evals/evals.json)
- Initial version. Tier `moderate`, interval 30d. See R-20261114-1 for the research basis; the first test run, for a skill, is logged in TESTS.md.

### C-20261114-10 · 2026-11-14 · description now lists video, audio visualizers, flames, IFS, L-systems, attractors, terrain and identify; evals.json written (5 triggers, 6 decoys, action zoom video, outcome coastline D on a Koch fixture) · because: T-20261114-10
