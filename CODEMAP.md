# CODEMAP

- `skills/fractalwright/SKILL.md`: hub skill (workflow; loads `references/` on demand).
- `scripts/fw.py`: CLI. `load_recipe`/`normalise` (recipe schema, presets), `escape_numpy` (five families), `render_array` (NumPy core), `render_rows_py` (pure Python fallback), `write_png` (stdlib PNG), `box_dimension` (batch 1, kept for its tests), `mandelbrot_area`; measure v2 block: `box_analysis` (sizes, offsets, local slopes, verdict, thresholds as constants), `remove_specks`, `lacunarity`, `similarity_dimension`; self-affine block: `spectral_slope`, `semivariogram_h`, `katz_dimension`, `radial_psd`, `profile_analysis`, `heightmap_analysis`, `synth_fbm1d` (Davies-Harte), `synth_fbm2d`; `kronecker_mask` and `KRONECKER`; identify block: `julia_connected`, `mirror_scores`, `identify`; `cmd_*` per command.
- `tests/test_fw.py`: proof bars (determinism, symmetry, dimensions, area; batch 2: box verdicts and decoys, specks, Kronecker, lacunarity, Moran, fBm profile and surface, Katz, identify). Measured errors in TESTS.md.
- `references/01-11`: research by topic. `bench/bench.py`: Step C render-core benchmark.
- `ai-docs/`: HANDOFF, log, plans (design.md = render core and recipe schema; continue prompt), notes.
- Root evergreen unit: `evergreen.json`, RESEARCH, CHANGELOG, LEARNINGS, TESTS, MAINTENANCE, `evals/`, `harvest.json`.
