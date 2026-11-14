# Tests: fractalwright

Test runs for [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md). Cases live in `evals/evals.json`. A failure that taught something is a lesson in [LEARNINGS.md](LEARNINGS.md); a fix it caused is logged in [CHANGELOG.md](CHANGELOG.md) with `because: T-...`; research it triggered is in [RESEARCH.md](RESEARCH.md); counts and the failing list are in `evergreen.json` under `tests`. Rules: MAINTENANCE.md (testing section) and the plugin's `protocol/TESTING.md`.

A test passes on evidence (a tool call in the trace, a file, a marker, a log line), never on the transcript's claim that something was done.

Entry shape: `### T-YYYYMMDD-n · date · harness · env · passed/total`, then one line per failing case (`id · kind · class · what the evidence showed`), then `led to:` (L-, C-, R- ids or none). Newest first. Budget 150 lines; archive older runs to `TESTS-ARCHIVE.md`.

## Runs

### T-20261114-2 · 2026-11-14 · unittest (tests/test_fw.py) · Windows, Python 3.14.6, numpy 2.5.2 · 8/8
- Proof bars with measured errors: Mandelbrot area +0.00018 at 1024 px, 10^4 iterations (bar 0.002); Sierpinski lattice 4e-16, chaos game +0.0087 at 1024 px (bar 0.02); Koch +0.0193 at 2048 px (bar 0.04); mirror symmetry exact; same recipe gives identical pixels for all five families and through a saved recipe; pure Python fallback within 1.0 mean diff of NumPy.
- Agent evals not written yet (Step F).
- led to: none

### T-20261114-1 · 2026-11-14 · not yet run · plugin · 0/0
- Suite scaffolded; no run recorded. Write the cases in `evals/evals.json` (at least two trigger prompts, two decoys, one action case with evidence, one outcome case), run the baseline without the skill, then run with it (`evergreen-test`).
- led to: none
