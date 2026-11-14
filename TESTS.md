# Tests: fractalwright

Test runs for [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md). Cases live in `evals/evals.json`. A failure that taught something is a lesson in [LEARNINGS.md](LEARNINGS.md); a fix it caused is logged in [CHANGELOG.md](CHANGELOG.md) with `because: T-...`; research it triggered is in [RESEARCH.md](RESEARCH.md); counts and the failing list are in `evergreen.json` under `tests`. Rules: MAINTENANCE.md (testing section) and the plugin's `protocol/TESTING.md`.

A test passes on evidence (a tool call in the trace, a file, a marker, a log line), never on the transcript's claim that something was done.

Entry shape: `### T-YYYYMMDD-n · date · harness · env · passed/total`, then one line per failing case (`id · kind · class · what the evidence showed`), then `led to:` (L-, C-, R- ids or none). Newest first. Budget 150 lines; archive older runs to `TESTS-ARCHIVE.md`.

## Runs

### T-20261114-7 · 2026-11-14 · unittest (tests/) · Windows, Python 3.14.6, numpy 2.5.2 · 63/63 (after rebase on batch 4a; 12 new in test_extra.py)
- Logistic: 1, 2, 4, 8 branches at r 2.8, 3.2, 3.5, 3.56; Lyapunov r = 4 0.9999995 bits (bar 0.01), r 3.2 negative. Henon (1.4, 0.3): L 0.6036 bits (bar 0.603 +- 0.02), D2 1.201 and 1.195 on two subsets (bar 1.21 +- 0.05). Search: 5 hits in 177 tries, 1.1 s.
- IFS: unequal tiles 8x8 histogram cv 0.014 with |det| p, 1.049 with equal p (bars 0.05, 0.5). Ball cover: max distance / R 1.0 Sierpinski, 0.973 fern, 0.995 worst of 20 random 3-map IFS (bar 1). Start 50 units away: 8 of 50 points outside without discard, 0 with 20.
- Terrain crease ratio (n/8 lines): diamond-square 1.188, 1.177, 1.174; spectral 1.000, 0.983, 0.990 (bars > 1.10 and 1 +- 0.04).
- FIF: d = 0 equals the line join (error 0); passes through all points (1e-12); semivariogram D vs 1 + log(sum|d|)/log 4: 1.524/1.5, 1.604/1.632, 1.374/1.339, 1.745/1.743 (bar 0.05).
- Mariani-Silver (not shipped): 800x600, max_iter 200-5000, full Mandelbrot and a rotated view differ by 0-10 pixels (slow-escaping pixels inside rectangles whose border never escaped); seahorse, two Julias and multibrot-3 identical. Speed x2.4-3.0 on interior-heavy views, x0.25-0.77 on views with little interior.
- Multi-scroll sine-Chua (not shipped): recalled parameters (alpha 10.814, beta 14, a 1.3, b 0.11) diverged at c = 1 and 3 and gave one broad lobe at c = 2.

### T-20261114-6 · 2026-11-14 · unittest (tests/) · Windows, Python 3.14.6, numpy 2.5.2, Playwright + Edge headless (ANGLE D3D11, RTX 5060 Ti) · 51/51
- Browser route vs NumPy, 320x240 full views, 300 iterations, mean abs diff per channel: mandelbrot 0.144, julia 0.023, tricorn 0.052, multibrot-3 0.148 (bar 1.0); burning ship 2.726 (bar 3.0), because NumPy itself run in float32 differs from float64 by 2.628 on the same view (abs folds amplify rounding).
- Page: zoom 4x about a point and pan by script, hash read, Export over POST, NumPy render of the exported recipe vs the page canvas: 0.251 (bar 1.5). Hash -> recipe -> hash identical for 6 hashes, including a 33-digit centre and rotation.
- Routing: seahorse (width 1e-4) with `--route browser` at 96x64 goes to NumPy (the first rule, pixel under 1e-6 of the coordinate, let it through at 96 px; the width rule 1e-3 catches it). Server refuses 0.0.0.0, a LAN address, a hostname and ""; `fw.py serve --host 0.0.0.0` exits 2.
- led to: C-20261114-6

### T-20261114-5 · 2026-11-14 · unittest (tests/) · Windows, Python 3.14.6, numpy 2.5.2 · 43/43 (after rebase on batch 3)
- Deep zoom (fw_deep.py, perturbation with rebasing, Decimal reference orbit): width 1e-6 at 96x64, 2000 iterations, mean diff 0.405 vs plain NumPy (bar 1.0). Width 1e-20 and 1e-30 at 24x16, 3000 iterations: 384/384 pixels give the same iteration count as direct Decimal iteration (bar 99%, no wrong blob over 4 px); counts 1164-1978 and 2078-2815.
- Timings: perturbation 0.03 s (1e-20) and 0.04 s (1e-30) for 384 px; direct Decimal 0.44 s and 0.74 s. At 1e-6, 96x64: plain 0.03 s, perturbation 0.13 s.
- Rebasing counter: at both deep views the reference orbit escapes early (1358 and 2191 iterations), so every pixel rebases at least once (384 and 374 pixels, 3316 and 2339 rebases) and counts still match exactly.
### T-20261114-4 · 2026-11-14 · unittest (tests/test_fw.py) · Windows, Python 3.14.6, numpy 2.5.2, ffmpeg on PATH · 37/37
- Video at 160x90, max_iter 200, 12 frames at 12 fps. Same recipe twice: 12/12 frame hashes identical. Loop seam (julia c circle r 0.02 + palette phase): last-to-first mean abs diff 34.35 vs median neighbour diff 35.99, ratio 0.954 (bar 1.25). Zoom 3.5 -> 0.01 over 12 frames: width ratio spread 4.4e-16 (bar 1e-9). ffprobe: zoom, loop and morph mp4 each 12 frames at 12.0 fps.
- flashcheck on the test outputs: zoom 1, loop 2, morph 1 swings per second (limit 3), mp4 and frame folder both pass; a black/white strobe decoy fails. Sheet tile 2 pixel-identical to its sidecar recipe re-rendered. AI hook: a local stub server on /system_stats gives ai_pass pending-not-implemented; no host gives the exact video with a note. Suite runtime 57 s.
- led to: C-20261114-4

### T-20261114-3 · 2026-11-14 · unittest (tests/test_fw.py) · Windows, Python 3.14.6, numpy 2.5.2 · 30/30
- Box v2 (16 sizes, 8 seeded offsets): Koch 4096 px -0.0025 (bar 0.02), 2.23 decades, fractal-like; Koch 2048 px 1.93 decades, descriptor only; chaos Sierpinski 2048 px -0.0146 (bar 0.03). Local-slope spread: fractals 0.05-0.29 (Cantor dust 0.287 worst), decoys spiral 1.02, random discs 0.53, filled disc 0.35, so SLOPE_SPREAD_MAX = 0.30. A diagonal line reads 0.931 (spread 0.280), so INTEGER_BAND = 0.10.
- Specks: 3000 on Koch 2048 moved D to 1.176; the 1-2 px filter removed 2917 and returned 1.2589 (clean 1.2581, bar 0.005). A single-pixel filter left 131 and read 1.176: pairs matter.
- Kronecker: exact (under 1e-9) with boxes 3^j; general boxes -0.05 to -0.07 (carpet -0.061, Vicsek -0.053, dust -0.058; bar 0.08). Python fallback pixel-identical.
- Lacunarity pair (5^5 px, both log16/log5): box D 1.656 vs 1.681 (bar 0.05 apart); Lambda ratio at r 32-256 is 1.14, 1.14, 1.20, 1.32 (bars 1.10 and 1.25 at r 256).
- Profiles (Davies-Harte fBm 2^16, 10 seeds, H 0.3-0.8): max |H error| spectral 0.033 (bar 0.045), semivariogram 0.055 (bar 0.07). Katz exact on a Koch polyline; 1.028 on every fBm H.
- Surfaces (spectral synthesis 1024^2, 4 seeds): radial H max error 0.015 (bar 0.025); profile cuts 0.021 (bar 0.03); radial minus profile beta 0.96-1.01 (bar 0.06). Integer-k bin averages had read H 0.04-0.05 low; per-mode least squares fixed it. Differential cube counting read D 0.1-0.3 low (reported with a warning, not tested).
- Identify: Julia connectedness right on 5 c values; cardioid and period-2 bulb hints; full Mandelbrot view mirror up-down 1.0.
- led to: C-20261114-3

### T-20261114-2 · 2026-11-14 · unittest (tests/test_fw.py) · Windows, Python 3.14.6, numpy 2.5.2 · 8/8
- Proof bars with measured errors: Mandelbrot area +0.00018 at 1024 px, 10^4 iterations (bar 0.002); Sierpinski lattice 4e-16, chaos game +0.0087 at 1024 px (bar 0.02); Koch +0.0193 at 2048 px (bar 0.04); mirror symmetry exact; same recipe gives identical pixels for all five families and through a saved recipe; pure Python fallback within 1.0 mean diff of NumPy.
- Agent evals not written yet (Step F).
- led to: none

### T-20261114-1 · 2026-11-14 · not yet run · plugin · 0/0
- Suite scaffolded; no run recorded. Write the cases in `evals/evals.json` (at least two trigger prompts, two decoys, one action case with evidence, one outcome case), run the baseline without the skill, then run with it (`evergreen-test`).
- led to: none
