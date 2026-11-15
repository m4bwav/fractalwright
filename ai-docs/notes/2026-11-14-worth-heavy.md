# fractalwright: heavy evergreen-worth run (2026-11-14)

Mark approved it. Harness: evergreen 1.1.1 `evergreen.py worth --heavy`, then a corrected `--ab`, using claude -p with sonnet and 3 runs per arm. Skill version 0.2.2 (installed fractalwright@mark-local). Raw output: session scratchpad (`worth/` and `ab2/`), which is temporary. Nothing was recorded to evergreen.json. If the master session agrees, record the ruling with `EG worth skills/fractalwright --set KEEP --why "..."`.

## Verdict: KEEP, with TRIM items (after hand-grading; the harness printed CUT and was wrong)

| Case | with | without | Notes |
|---|---|---|---|
| action-zoom-video (graded by hand) | 2/3 full pass, 3/3 mp4 + recipe | 0/3 | All 6 runs made a 320x240 h264 mp4 of 3.0 s. Only the with arm wrote `<out>.json` with an `animation` block, and only the with arm reported a flash check. With-arm run 3 hit max_turns (31) while tuning the look, so it gave no reply and no flash report. |
| outcome-coastline-d (regex grader) | 3/3 | 3/3 | The baseline now passes, so this case proves nothing. The stale baseline note in evals.json (D 1.36, FAIL) did not reproduce. |
| Total | 5/6 (83%) | 3/6 (50%) | |

- Cost: x1.82 (with about $0.24 to $0.73 a run, without about $0.19 to $0.40), turns x2.08, time x2.24.
- Static: listing ~198 tokens every session, body ~2,385 tokens per use, 90% specific sentences, 0 repeats. Mode 1 (0 uses in 60 days) is expected: the plugin is a day old.
- Probe (no skill, no tools): named 1 of 60 key anchors. The model does not know fw.py, recipes, presets or the flash check, and that is the reason the skill exists.
- Total cost: $3.38 for the first heavy run (invalid) plus about $4.1 for the corrected A/B. GPU: none (CPU NumPy renders).

Why KEEP and not CUT: the gain on the case the skill exists for (a reproducible recipe plus a flash check) is 67 points against 0. The printed CUT came from a grader that cannot judge `command` evidence. Why TRIM: the cost is above 1.5x, and most of the extra cost was turns spent on overhead and on gold-plating.

## Harness problems found (fix in evals/evals.json on a branch)

1. `action-zoom-video` uses a `{out}` placeholder that the `--ab` runner never fills. In the first run every with-arm run stopped and asked where `{out}` was, and every arm failed. The case lint did not flag it. Fix: prompt "the folder out/ in the current directory" and evidence `out/*.mp4`.
2. Neither value case has `tools` or `max_turns`. In the first run, Bash was refused headless and both arms ran out of turns at 13 turns. Fix: `"tools": ["Read","Write","Edit","Glob","Grep","Bash"], "max_turns": 30` (both added in the scratch copy for the corrected run).
3. `command` evidence is not graded by `worth --ab` (evergreen.py line 1374: "stays with the tester agent"), so the zoom case fails in both arms by construction. Add a stdlib checker, `evals/check_zoom.py <dir>`, that exits 0 only when there is an h264 320x240 3.0+-0.2 s mp4 and a .json with `animation`. Pair it with a `regex on the answer:` for "flash". Prove the checker on the kept run folders before the next paid run.
4. `outcome-coastline-d` passes without the skill. Replace it with a harder case, for example a fixture where a naive edge-pixel box count lands outside the band, or one that requires the "two decades or no verdict" rule.
5. Evergreen-side learning (for the evergreen LEARNINGS): the case lint missed both the unfilled `{out}` placeholder and the case with neither tools nor max_turns, and `--heavy` printed CUT from a case it could not grade at all.

## Recommended trims (expected savings)

- With-arm runs each spent 2 to 3 turns reading `evergreen.json` and running `fw.py doctor` before working (SKILL.md line 17). Move the freshness read to refreshes only, or make it `fw.py doctor --quiet` once per machine. This saves about 2 turns and about $0.03 to $0.05 a use.
- With-arm run 3 spent about 20 turns hand-editing max_iter, density and supersample and re-rendering, then hit max_turns. Add one line: "render the preset as given; tune the look only when asked", or ship a ready `seahorse` zoom recipe. This removes the tail runs, which cost up to $0.73 and 600 s.
- Move detail that only some uses need to `references/` and read it on demand: the browser/GPU perturbation paragraph (line 29), the AI styling detail (line 35) and the audio mapping detail (line 33). Expected cut: roughly 700 to 900 of the 2,385 body tokens. Re-run the fixed A/B afterwards and keep the cut only if the zoom pass rate holds.
- Leave the description unchanged (trigger evals 13/13).
