# AGENTS.md

Rules for any AI agent working in this repository. `CLAUDE.md` imports this file; `.github/copilot-instructions.md` points here.

## What this is

fractalwright: one hub skill, `skills/fractalwright/`. `scripts/fw.py` is the CLI, `references/` the research (load one file when a step needs it), `ai-docs/` the plans, log and handoff (start with `ai-docs/HANDOFF.md` and `ai-docs/plans/fractalwright-continue-prompt.md`). Map: `CODEMAP.md`.

## Rules

- Scripts: Python 3.9+, standard library first. NumPy is the reference core; Pillow, moderngl and Playwright are optional and probed by `fw.py doctor`, never required. UTF-8, LF.
- Every render writes a recipe JSON next to the PNG that redraws it exactly. Centre, width and Julia `c` are decimal strings. A recipe field change bumps `fractalwright` in the recipe.
- Proof bars are numbers: tolerances in tests come from measured errors, written in the test comment and TESTS.md. Never loosen one without a new measurement.
- Every change gets a test. Run `python -m unittest discover -s tests`.
- Evergreen unit at the root: read `evergreen.json` before editing; log changes in CHANGELOG with the reason, lessons in LEARNINGS. Beat `fractal-art` and `harvest.json` feed refreshes.
- A release bumps `.claude-plugin/plugin.json`, `plugin.json`, `VERSION` in `fw.py`, `metadata.version` in SKILL.md and the CHANGELOG together.
- No private names, hostnames or paths in public files. Plain short sentences, no em dashes, relative links. No AI attribution anywhere.

## Commands

- Tests: `python -m unittest discover -s tests`
- Doctor: `python scripts/fw.py doctor`
- Render: `python scripts/fw.py render seahorse -o out.png --size 800x600`
