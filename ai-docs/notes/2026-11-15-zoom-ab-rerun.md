# Zoom eval re-run, with skill (2026-11-15)

Why: in the v0.5.1 A/B, with-skill zoom runs 2-3 took 24-26 turns retrying after flashcheck printed FAIL. v0.6.0 fixed the verdict. This re-runs only `action-zoom-video` with the skill, 3 runs, sonnet, via evergreen:evergreen-tester agents (skill 0.9.0, installed and in the clone). Graded from the tester traces plus `python evals/check_zoom.py <run>/out`, re-run by the master session.

| Run | check_zoom | Turns (tool calls) | Flash verdict | Retried on flashcheck |
|---|---|---|---|---|
| 1 | PASS | 5 | pass, 11% together, 1 swing/s | no (one retry for a bad preset name `mandelbrot`; should be `mandelbrot-full`) |
| 2 | PASS | 4 | pass, 14% together | no |
| 3 | PASS | 5 | pass, 18% together | no |

- Pass: 3/3. Turns 4-5 (was 24-26 in runs 2-3 of v0.5.1). No run called flashcheck separately; `fw.py zoom` runs it and printed pass every time.
- Cost: about 85k subagent tokens and 27-33 s per run (~256k tokens total). The tester agents give no dollar figure; at sonnet rates this is well under the ~$0.24-0.73 per run of v0.5.1.
- Caveats: testers wrote no user-facing final answer (they report instead), so the "regex on the answer: flash" expectation was graded from the reported flash verdict. Run 1 shows `mandelbrot` is a natural guess for a preset name; an alias could save a turn.
- Conclusion: the v0.6.0 flashcheck fix removed the retry loop. Item 1 in HANDOFF Next is closed.
