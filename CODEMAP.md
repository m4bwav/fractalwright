# CODEMAP

- `skills/fractalwright/SKILL.md`: hub skill (workflow; loads `references/` on demand).
- `scripts/fw.py`: CLI. `load_recipe`/`normalise` (recipe schema, presets), `escape_numpy` (five families), `render_array` (NumPy core), `render_rows_py` (pure Python fallback), `write_png` (stdlib PNG), `box_dimension`, `mandelbrot_area`, `cmd_*` per command.
- `tests/test_fw.py`: proof bars (determinism, symmetry, dimensions, area).
- `references/01-11`: research by topic. `bench/bench.py`: Step C render-core benchmark.
- `ai-docs/`: HANDOFF, log, plans (design.md = render core and recipe schema; continue prompt), notes.
- Root evergreen unit: `evergreen.json`, RESEARCH, CHANGELOG, LEARNINGS, TESTS, MAINTENANCE, `evals/`, `harvest.json`.
