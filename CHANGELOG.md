# Changelog: fractalwright

Every change to [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md) and its companions, newest first, each with the reason. Reasons cite findings in [RESEARCH.md](RESEARCH.md) (`R-`), lessons in [LEARNINGS.md](LEARNINGS.md) (`L-`), and test runs in [TESTS.md](TESTS.md) (`T-`). State in `evergreen.json`. Protocol: MAINTENANCE.md.

Entry shape: `### C-YYYYMMDD-n · date · one-line summary`, then `because:` (IDs or "user request"), `files:` (file and section), and a sentence on what changed. Cite section headings, not line numbers.

### C-20261114-2 · 2026-11-14 · fw.py first batch: doctor, explain, render, measure, palette
- because: user request (continue prompt Step D), T-20261114-2
- files: scripts/fw.py, tests/test_fw.py, skills/fractalwright/SKILL.md
- NumPy float64 render of five escape-time families with smooth colouring and recipes saved next to each PNG; box-counting dimension; Mandelbrot area by pixel count.

### C-20261114-1 · 2026-11-14 · Created as an evergreen unit
- because: user request
- files: skills/fractalwright/SKILL.md, RESEARCH.md, LEARNINGS.md, evergreen.json (skills: also TESTS.md and evals/evals.json)
- Initial version. Tier `moderate`, interval 30d. See R-20261114-1 for the research basis; the first test run, for a skill, is logged in TESTS.md.
