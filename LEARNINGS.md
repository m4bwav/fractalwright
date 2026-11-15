# Learnings: fractalwright

Procedural lessons for [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md). Research findings live in [RESEARCH.md](RESEARCH.md); every change is logged in [CHANGELOG.md](CHANGELOG.md); test runs in [TESTS.md](TESTS.md); state in `evergreen.json`. Format and write-time gate: MAINTENANCE.md (LEARNINGS-FORMAT). Retired entries go to LEARNINGS-ARCHIVE.md with a reason.

Write an entry the moment a real signal happens: a user correction, the same error twice, a discovered workaround, an environment fact, a stated preference, a failed test or a failure in use. Check existing entries first, by meaning (`evergreen.py search "<the lesson>" --kinds learnings` finds near-duplicates in every registered unit): add / update / retire / none. Trigger and Hypothesis are required. Promote after three confirmations; retire when harmful > helpful.

## Active

<!-- Example (delete once you have a real entry):
### L-001 · 2026-11-14 · One-line lesson in plain words
- Trigger: what happened, with dates or counts
- Hypothesis: why
- Rule: the shortest instruction that prevents the trigger
- Evidence: C-20261114-1, T-20261114-1, confirmed 2026-11-14
- Scope: skill | repo:<slug> | env:<name> | global
- Status: active · helpful 1 · harmful 0 · last_confirmed 2026-11-14
-->

### L-20261114-11 · 2026-11-14 · df-shader-needs-bit-fence
Trigger: double-float GPU deltas measured no better than float32. Hypothesis: ANGLE/D3D11 rewrites (s - a) to b and contracts products into fma unless each rounded value passes through uintBitsToFloat(floatBitsToUint(x) ^ u_zero); a `* u_one` uniform is not enough. Probe each df op against NumPy before measuring the fractal. Also: deltas under ~1e-30 lose the lo half to denormal flush.
- Scope: repo:fractalwright
- Status: active · helpful 1 · harmful 0 · last_confirmed 2026-11-14

### L-20261114-10 · 2026-11-14 · description-lagged-features
Trigger: trigger-visualizer routed to no skill; zoom and flame matched only by luck. Hypothesis: each new command (zoom, audio, flame) must add its user phrase to the description in the same change, or routing never sees it.
