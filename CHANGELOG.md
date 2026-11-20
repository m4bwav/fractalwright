# Changelog: fractalwright

Every change to [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md) and its companions, newest first, each with the reason. Reasons cite findings in [RESEARCH.md](RESEARCH.md) (`R-`), lessons in [LEARNINGS.md](LEARNINGS.md) (`L-`), and test runs in [TESTS.md](TESTS.md) (`T-`). State in `evergreen.json`. Protocol: MAINTENANCE.md.

### C-20261119-30 - 2026-11-19 - release 0.12.0: Book of Shaders rules
- because: C-20261119-29 and the harvest.json popular-repos query (PR #34)
- files: plugin.json files, scripts/fw.py (`VERSION`)
- Version 0.11.1 to 0.12.0.

### C-20261119-29 - 2026-11-19 - Book of Shaders: GPU Worley rules, hue wheel, explorer shader check
- because: book distillation (The Book of Shaders ch. 5, 6, 7, 12; checked against thebookofshaders.com chapter sources)
- files: references/06-noise-natural.md (GPU Worley paragraph, [S16]), references/02-escape-time.md (hue wheel and eased palettes, [S29]), tests/test_serve.py (`ShaderViewRules`)
- GPU Worley: one point per cell, 3x3 cell-local search, 2x2 seam risk, nearest point for region ids, constant loop bounds. Palettes: RGB hue wheel puts cyan opposite red (not the painter's RYB green); ease through a shaping function. New test: the explorer's .frag files have no unwrapped time in trig and no unscaled aspect; the check fires on a bad snippet.

### C-20261115-28 - 2026-11-15 - release 0.11.1: palette validation, bare family presets
- because: HANDOFF Next 0 (session 9 leftovers): `3d mesh --palette fire` was accepted silently as one colour; an eval run guessed preset `mandelbrot`
- files: scripts/fw_mesh.py (`parse_palette`), scripts/fw.py (`load_recipe` alias, `VERSION`), tests/test_3d.py (`test_palette_validation`), tests/test_fw.py (`test_bare_family_alias`), plugin.json files
- `--palette` now takes only comma-separated `#RRGGBB` (hash optional) and exits with a clear message otherwise. A bare family name (`mandelbrot`, `burning-ship`) loads its `<family>-full` preset.

### C-20261115-27 - 2026-11-15 - release 0.11.0: progressive preview in the deep explorer
- because: user request (HANDOFF Next 7 left: the explorer redrew only after each /orbit round trip)
- files: scripts/page/deep_df.frag (`u_km1`, `u_off`), scripts/page/explorer.html (`previewOffsets`, `deepRequest` with AbortController and a sequence number, `deepDraw` coarse draw), scripts/fw.py (`VERSION`), tests/test_serve.py (`test_page_progressive_preview`), references/03-deep-zoom.md (2.7), SKILL.md, README.md, plugin.json files
- While a new orbit is pending, the page redraws at once from the last exact orbit (pixel map o * k + D in old pixel units), one pixel per 4x4 block, then swaps in the exact frame; a newer move aborts the stale request. First pixel 24-42 ms -> 3-6 ms; full-res preview mismatch 0.19-0.23 levels mean (T-20261115-16). Chose orbit reuse over a scaled copy of the last frame: it shows new detail at the edges and after zooms, and the shader change is two uniforms.

### C-20261115-26 - 2026-11-15 - release 0.10.0: orbit-trap colour 3MF from `3d mesh`
- because: user request (HANDOFF Next 5: "Left: orbit-trap colour to 3MF")
- files: scripts/fw_mesh.py (`de_trap`, `face_colours`, `write_3mf`, `read_3mf`, `_paint`, `cmd_mesh`), scripts/fw_3d.py (`--colors`, `--palette`), scripts/fw.py (`VERSION`), tests/test_3d.py (`test_colour_3mf`), skills/fractalwright/SKILL.md, references/07-3d.md (Meshing), plugin.json files
- `fw.py 3d mesh <f> -o x.3mf [--colors N]` writes a 3MF (materials colorgroup + Bambu `paint_color`) coloured by the orbit trap in N equal-surface bins, plus the STL. Written with stdlib zip + XML rather than polywright `pw.py 3mf`, which packs whole meshes per object and has no per-triangle colour. Mandelbulb and Menger 3MFs pass `pw.py check --target print-fdm`.

### C-20261115-25 - 2026-11-15 - release 0.9.0: `3d mesh --wall-mm`
- because: user request (HANDOFF Next 5: Mandelbulb at 60 mm warned 2.7% of the surface under 0.9 mm)
- files: scripts/fw_mesh.py (`wall_iso`, `build`, `cmd_mesh`), scripts/fw_3d.py (`--wall-mm`), scripts/fw.py (`VERSION`), tests/test_3d.py (`test_wall_mm_offsets_surface`), skills/fractalwright/SKILL.md (3D mesh), references/07-3d.md (Meshing), README.md, plugin.json files
- `fw.py 3d mesh --wall-mm X` meshes the offset surface DE = X/2 at print scale (chosen over voxel dilation: smooth, same pipeline). Mandelbulb 60 mm, 0.9: print-fdm check pass, thin fraction 2.68% -> 0.11%, watertight, 1 shell.

### C-20261115-24 - 2026-11-15 - release 0.8.0: path traced 3D by default
- because: user request (askwright set fractalwright-pathtrace-2026-11-14: Mark chose "Path traced by default" over the low-confidence guess "keep")
- files: scripts/fw_3d.py (`DEFAULT_PT_SAMPLES`, `_apply_args`, `--pt` help), scripts/fw.py (`VERSION`), tests/test_3d.py, skills/fractalwright/SKILL.md (3D step), references/07-3d.md (Path tracer), README.md, plugin.json files
- `fw.py 3d render|recipe <formula>` now path traces at 256 samples unless `--pt 0`; recipe files keep their own setting, so old recipes redraw the same pixels. `3d gate` is unchanged (the remedy matrix stays on the shadow/ao look).

### C-20261114-23 - 2026-11-14 - release 0.7.0: parameter checks against papers
- because: user request (HANDOFF Next 6)
- files: scripts/fw_gen.py (`ATTRACTORS`, `flow_rhs`, `flow`, `yalcin_f1`), scripts/fw_neighbours.py (`limit_curve_dfs`, `_fix_attr`, `kleinian --method`), scripts/fw_deep.py (`series_skip`, `escape_perturb`), scripts/fw.py (`render --series`, `VERSION`), scripts/fw_serve.py (hash `ps`), scripts/page/explorer.html (rotation input and keys, stop palettes), tests, references/03, 05, 12, SKILL.md, README.md, plugin.json files
- Icon presets checked against Symmetry in Chaos Table A.1 (both matched; four added). New flows chen, lu (published a, b, c) and Yalcin multiscroll. Kleinian grandma draws by the Indra's Pearls depth-first word search by default. Series approximation added as opt-in `--series` (1.0-1.7x, counts within plain perturbation's own error). The explorer gains a rotation control and stop palettes in the share hash.

### C-20261114-22 - 2026-11-14 - release 0.6.0: flashcheck verdict fix, `3d mesh` printable STL
- because: user request (HANDOFF Next 1 and 5)
- files: scripts/fw.py (`flash_check`, `_sync_area`, `flash_line`, `cmd_flashcheck`, `_finish_video`, `VERSION`), scripts/fw_audio.py, scripts/fw_neighbours.py, scripts/fw_mesh.py (new), scripts/fw_3d.py (`mesh` action, `--res --size-mm --iter --engine`), tests/test_fw.py, tests/test_3d.py, references/07-3d.md (Meshing), skills/fractalwright/SKILL.md (Step 2b, 2e, metadata), README.md, plugin.json, .claude-plugin/plugin.json
- A default 320x240 3 s zoom printed "1 swings/s (limit 3) FAIL": the verdict came from the per-cell area rule (95% of cells flashed 6.5/s as bands drifted through 6 px cells, out of step), while the line printed the unrelated whole-frame count. The area rule now counts only cells whose swings coincide within a frame with a reference cell (WCAG: one flash over the area); the out-of-step figure stays as `async_flash_area`; `failed_rules` and a verdict line print the area that decided it. `fw.py 3d mesh` writes a watertight single-solid STL in mm from the NumPy DE (scikit-image marching cubes optional, NumPy marching tetrahedra otherwise).

Entry shape: `### C-YYYYMMDD-n · date · one-line summary`, then `because:` (IDs or "user request"), `files:` (file and section), and a sentence on what changed. Cite section headings, not line numbers.

### C-20261114-20 · 2026-11-14 · release 0.5.0: double-float GPU deep deltas, GPU deep in the explorer
- because: user request (HANDOFF Next 3), T-20261114-17, L-20261114-11
- files: scripts/page/deep_df.frag (new), scripts/page/deep.frag (RGBA orbit texture), scripts/fw_gpudeep.py (`frag_source`, `_df`, `uniforms` precision, `SWITCH_DF`, `GpuDeep(precision)`), scripts/fw_serve.py (`orbit_uniforms`, POST `/orbit`, `page_html`), scripts/page/explorer.html (GPU deep draw, exact decimal centre maths), scripts/fw.py (`--gpu-precision`, `VERSION`), tests/test_gpudeep.py, tests/test_serve.py, README.md, skills/fractalwright/SKILL.md (explorer paragraph, metadata), plugin.json, .claude-plugin/plugin.json
- Version 0.5.0 because 0.4.0 (path tracing) was released while this was built. The GPU perturbation shader now keeps the orbit and every delta as float-float pairs (two-sum, Veltkamp two-product, no fma), converting from pixel units at 1e-20 instead of 1e-30 because the GPU flushes the denormal lo halves. At 512 px escape-count mismatches against the CPU route drop from 3.5-18.7% to 0.09-1.02% for 0.24-0.30 s per call (float32 0.18-0.25 s); float32 stays behind `--gpu-precision float32`. `fw.py serve`: past float32 the page posts the view to the loopback `/orbit` endpoint and draws the server's Decimal orbit with the same shader; pan and zoom keep the centre as exact decimal strings.

### C-20261114-21 - 2026-11-14 - release 0.5.1: worth trims, fixed value evals
- because: user request, ai-docs/notes/2026-11-14-worth-heavy.md
- files: skills/fractalwright/SKILL.md (Step 0, explorer, audio and video paragraphs, metadata), references/13-route-details.md (new), evals/evals.json, evals/check_zoom.py (new), evals/fixtures/coastline-small.png (new), plugin.json, .claude-plugin/plugin.json, scripts/fw.py (`VERSION`)
- SKILL.md no longer reads evergreen.json or runs doctor on every use (doctor only on a failure, freshness on refresh), says "render the preset as given; tune the look only when asked", and moves browser/GPU perturbation, AI styling and audio mapping detail to references/13-route-details.md (body ~2,385 to ~2,195 tokens). Evals: the zoom case writes to out/ (no unfilled {out}), both value cases get tools and max_turns 30, evals/check_zoom.py grades the mp4 plus animation JSON, and outcome-coastline-small (96x96 Koch, 1.08 decades, verdict "descriptor only") replaces the coastline case the baseline passed. A/B sonnet, 3 runs per arm: with 6/6, without 0/6 (zoom hand-graded from transcripts), cost x1.23.

### C-20261114-19 · 2026-11-14 · release 0.4.0: path-traced 3D (`3d render --pt N`)
- because: user request (HANDOFF Next item 4)
- files: scripts/page/fractal3d.frag (`pathTrace`, `march`, `occluded`, `skyCol`, `cosineDir`, PCG RNG, `main`), scripts/fw_3d.py (`PT_DEFAULTS`, `normalise`, `uniforms`, page `drawPT`, `Browser3D.render_linear`, `to_srgb8`, `--pt/--bounces/--seed`), tests/test_3d.py, evals/pt_bench.py (new), references/07-3d.md (Path tracer), skills/fractalwright/SKILL.md (3D paragraph, metadata), plugin.json, .claude-plugin/plugin.json, scripts/fw.py (`VERSION`)
- `fw.py 3d render --pt N` path traces: diffuse, sky + sun, cosine-weighted bounces, seeded PCG RNG recorded in the recipe, N samples summed in a float framebuffer. Same seed gives identical pixels; noise falls as 1/sqrt(N) (RMSE*sqrt(N) 0.112-0.125); 512 px at 64/256 spp in 0.3-0.6 / 0.5-1.8 s.

### C-20261114-18 · 2026-11-14 · release 0.3.0: GPU perturbation deep zoom, rd --size N
- because: user request, T-20261114-16
- files: scripts/fw_gpudeep.py (new), scripts/page/deep.frag (new), scripts/fw.py (`cmd_render`, `cmd_zoom`, `write_video`, `_finish_video`, render/zoom `--route` help, `VERSION`), scripts/fw_neighbours.py (`_size`), tests/test_gpudeep.py (new), tests/test_neighbours.py, tests/test_serve.py, README.md, skills/fractalwright/SKILL.md (explorer paragraph, metadata), plugin.json, .claude-plugin/plugin.json
- `render --route browser` with `--deep`, a width under 1e-12, or a Mandelbrot/Julia view too deep for plain float32 now runs perturbation in a WebGL2 shader: Decimal reference orbit as an RG32F texture, float32 deltas held in pixel units until about 1e-30 (so dc never underflows), Zhuoran rebasing. Reaches width 1e-60; below that the CPU route runs. `zoom --route browser` renders every frame that way. About 250x faster than the CPU route at 512x512; escape counts differ on 3-19% of dense boundary pixels (float32 noise, a NumPy float32 copy differs from float64 by the same amount). `rd --size 64` now means 64x64; bad sizes give a usage message.

### C-20261114-17 · 2026-11-14 · release 0.2.2: AI styling off by default
- because: user request (askwright set fractalwright-ai-look-2026-11-14: exact zoom preferred, AI off by default)
- files: scripts/fw.py (`_video_args`, `VERSION`), scripts/fw_audio.py (`register`), scripts/fw_ai.py (`apply`), skills/fractalwright/SKILL.md (video paragraph, metadata), ai-docs/plans/design.md (section 6), plugin.json, .claude-plugin/plugin.json
- zoom, morph, loop and audio now render exact video only unless `--ai` is passed; `--no-ai` still works.

### C-20261114-16 · 2026-11-14 · release 0.2.1: AI pass flags, RD palettes and video
- because: user request, T-20261114-15
- files: scripts/fw_ai.py (`add_args`, `kw_from`), scripts/fw.py (`_video_args`, `_video_base`, `write_video`, `VERSION`), scripts/fw_audio.py (`register`, `cmd_audio`), scripts/fw_neighbours.py (`gray_scott` snaps, `Snaps`, `rd_rgb`, `_rd_video`, rd flags), tests/test_ai.py, tests/test_neighbours.py, plugin.json, .claude-plugin/plugin.json, skills/fractalwright/SKILL.md (metadata)
- zoom, morph, loop and audio take --ai-prompt, --ai-denoise (default 0.3, checked before rendering) and --ai-seed; they reach every img2img graph and the _ai.json recipe. `fw.py rd` takes --palette (any fw.py palette; default grey look unchanged) and --video OUT.mp4 with --frames and --fps: frames evenly spaced over --steps, one brightness scale for all frames, the zoom command's ffmpeg encode, flashcheck, recipe with an animation block.

### C-20261114-15 · 2026-11-14 · release 0.2.0
- because: user request
- files: plugin.json, .claude-plugin/plugin.json, skills/fractalwright/SKILL.md (metadata), scripts/fw.py (`VERSION`, doctor wording for moderngl and ffmpeg), README.md (Status)
- Since 0.1.0: AI styling pass for video (C-11), neighbours rd, ca, tiling and kleinian (C-12), Julia deep zoom and the WCAG 2.x flash area and red rules (C-13), and 3D as a normal route with shadow, ao and a composed camera by default (C-14). `fw.py --version` now prints 0.2.0; doctor no longer calls moderngl "not wired yet" and lists audio under ffmpeg.

### C-20261114-14 · 2026-11-14 · 3D ships as a normal route
- because: T-20261114-14, Mark's 3D gate answers (would keep all 9 renders shown), ai-docs/notes/2026-11-14-3d-gate.md
- files: scripts/fw_3d.py (`DEFAULT_REMEDIES`, Mandelbox scale and views, hybrid scale and views, `--remedy none`, gate baseline forced flat), scripts/page/fractal3d.frag (`DE`: hybrid at p*scale), tests/test_3d.py, skills/fractalwright/SKILL.md (Step 2e), README.md, CODEMAP.md
- Shadow, ao and the composed camera are on by default. Mandelbox moves from scale -1.5 to 2.0 (it read as a plain cube). Hybrid is evaluated at p*2.5 so it fits the bulb's frame. Recipes saved before this without a full remedies dict now render with the new defaults.

### C-20261114-13 · 2026-11-14 · gaps: Julia deep zoom, WCAG flash area rule, JS limiter test, Lorenz D2 fit
- because: T-20261114-13, HANDOFF Next item 4, W3C Understanding SC 2.3.1 (general flash and red flash thresholds, fetched 2026-11-14)
- files: scripts/fw_deep.py (Julia reference orbit and rebase against Z[0]), scripts/fw.py (`flash_check` area and red rules, `swing_walk`; render routes quadratic Julia to perturbation), scripts/fw_gen.py (`LORENZ_D2_FIT`, printed D2), scripts/fw_audio.py (docstring), tests
- flashcheck now fails only when cells flashing more than 3 times a second cover more than 25% of a 1/3 x 1/3 screen box (341x256 at 1024x768), so a small blinking region passes. Floatexp below 1e-290 left out (see ai-docs/log.md).

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
