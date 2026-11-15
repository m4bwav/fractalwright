# HANDOFF: fractalwright

Status: v0.9.0 released and installed 2026-11-15 (session 8: 0.8.0 path traced 3D by default per Mark, 0.9.0 mesh --wall-mm; wiki at 0.8.0). Steps A-F done. Not finished: Next items below, the two books.

Continue prompt: [plans/fractalwright-continue-prompt.md](plans/fractalwright-continue-prompt.md)

## What exists

- Public repo https://github.com/m4bwav/fractalwright, release https://github.com/m4bwav/fractalwright/releases/tag/v0.2.2, installed fractalwright@mark-local (entry in Ai/.claude-plugin/marketplace.json). Wiki 12 pages at 0.2.2 (https://github.com/m4bwav/fractalwright/wiki).
- fw.py commands: doctor, explain (incl. logistic cobweb/bifurcation, coastline), identify, measure, render (+ --deep perturbation to 1e-30 in fw_deep.py; --route browser via Playwright+Edge), palette, sheet, zoom, morph, loop, flashcheck, serve (explorer + /audio, loopback only), export, audio (fw_audio.py, uses musicwright mw.py envelopes >= 0.1.34, NumPy fallback), flame, lsystem, attractor (fw_gen.py), ifs, attractor-search, fif (fw_extra.py), 3d recipe|render|gate (fw_3d.py, browser only; default shadow+ao+camera), rd/ca/tiling/kleinian (fw_neighbours.py). Tests 119/119 (~110 s).
- ComfyUI hosts come from FW_COMFY_HOSTS (default loopback 8188,8199); add the Mac with FW_COMFY_HOSTS=127.0.0.1:8199,192.168.86.100:8188 (setx was refused by the permission classifier; Mark may set it).
- Evals: evals/evals.json, T-20261114-10: 13/13 after description fix; baseline 2/2 vs 0/2. Worth lite UNPROVEN (needs heavy A/B), leaning KEEP.
- Beat everscout `fractal-art`; harvest.json listed by `evergreen.py harvest targets`.

## Decisions (Mark, askwright set fractalwright-scope-2026-11-14, closed)

Name fractalwright; public; ALL neighbours in (reaction-diffusion, cellular automata, tilings, Kleinian); AI styling OFF by default since set fractalwright-ai-look-2026-11-14 (exact preferred; --ai opts in); Playwright+Edge first accelerator. Small rulings: MIT, no third-party presets, own shaders, fractal verdict needs two decades, band envelopes live in musicwright.

## Waits on Mark

- No open askwright sets (pathtrace set answered "path traced by default" and closed 2026-11-15).
- Books: Mark chose both (set fractalwright-next-2026-11-14, closed): Indra's Pearls and Peitgen, Chaos and Fractals. He buys them; distill when on disk.
- FW_COMFY_HOSTS set with setx to 127.0.0.1:8199,192.168.86.100:8188 (Mark's pick).

## Next (Mark's rank: gpudeep, path tracing, mesh, paper checks)

1. Done 2026-11-14 (v0.5.1, PR #22): worth trims + fixed evals, A/B 6/6 vs 0/6 at x1.23 (log). Flashcheck FAIL-at-1-swing/s fixed in v0.6.0: the area rule summed out-of-step cell swings (moving bands); now only cells flashing together count, and the verdict line names the failed rule and its area. Re-run 2026-11-15: 3/3 pass, 4-5 turns, no retries (notes/2026-11-15-zoom-ab-rerun.md).
2. Done 2026-11-14: wiki updated to 0.5.1 (wiki commit ce162a2; GPU deep route, explorer POST /orbit, rd --size N, 3d --pt; outputs check 35/35, live 12/12).
3. Done 2026-11-15: wiki at 0.8.0 (commit 0291dc3). Left: add 0.9.0 --wall-mm to the wiki Neighbours-and-3D page.
7. Done in v0.5.0 (PR #23): double-float GPU deep deltas (default; 0.09-1.02% mismatches) and GPU deep in the serve explorer (POST /orbit). Progressive preview done in 0.11.0 (coarse preview from the last orbit, stale requests aborted).
4. Path-traced 3D: done in 0.4.0 (`3d render --pt N`, references/07-3d.md "Path tracer"; sheet and judge in Ai/fractalwright-renders/pathtrace-2026-11-14).
5. Done in v0.6.0: `fw.py 3d mesh` (scripts/fw_mesh.py), watertight single-solid STL in mm; Mandelbulb 422k tris 11 s, Menger L3 816k tris 3 s, both pass `pw.py check --target print-fdm` (bulb warns 2.7% under 0.9 mm). `--wall-mm` done in 0.9.0 (offset DE = t; bulb 60 mm thin area 2.68% -> 0.11%, pw check pass). Orbit-trap colour 3MF done in 0.10.0 (`-o x.3mf --colors N`). Left: open one in Bambu Studio by hand to confirm the filament mapping.
6. Done 2026-11-14 (v0.7.0, PR papers): icons match Symmetry in Chaos Table A.1 (transcription; 4 sets added), chen/lu/multiscroll (Yalcin) added from the papers, kleinian grandma draws by DFS word search (default; --method random), series approximation opt-in `render --deep --series` (1.0-1.7x), explorer rotation control + stop palettes in the hash. Sources and measurements in references/03, 05 (4b, 4c), 12. Left: Grandma's recipe formulas and the DFS details vs Indra's Pearls when the book is on disk; icon table vs the printed book.
