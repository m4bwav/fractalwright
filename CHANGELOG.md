# Changelog: fractalwright

Every change to [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md) and its companions, newest first, each with the reason. Reasons cite findings in [RESEARCH.md](RESEARCH.md) (`R-`), lessons in [LEARNINGS.md](LEARNINGS.md) (`L-`), and test runs in [TESTS.md](TESTS.md) (`T-`). State in `evergreen.json`. Protocol: MAINTENANCE.md.

Entry shape: `### C-YYYYMMDD-n · date · one-line summary`, then `because:` (IDs or "user request"), `files:` (file and section), and a sentence on what changed. Cite section headings, not line numbers.

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
