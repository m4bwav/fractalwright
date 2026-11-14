# Tests: fractalwright

Test runs for [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md). Cases live in `evals/evals.json`. A failure that taught something is a lesson in [LEARNINGS.md](LEARNINGS.md); a fix it caused is logged in [CHANGELOG.md](CHANGELOG.md) with `because: T-...`; research it triggered is in [RESEARCH.md](RESEARCH.md); counts and the failing list are in `evergreen.json` under `tests`. Rules: MAINTENANCE.md (testing section) and the plugin's `protocol/TESTING.md`.

A test passes on evidence (a tool call in the trace, a file, a marker, a log line), never on the transcript's claim that something was done.

Entry shape: `### T-YYYYMMDD-n · date · harness · env · passed/total`, then one line per failing case (`id · kind · class · what the evidence showed`), then `led to:` (L-, C-, R- ids or none). Newest first. Budget 150 lines; archive older runs to `TESTS-ARCHIVE.md`.

## Runs

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
