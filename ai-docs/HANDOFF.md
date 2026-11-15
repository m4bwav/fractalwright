# HANDOFF: fractalwright

Status: v0.3.0 (GPU deep zoom on the browser route to 1e-60, rd --size N fix) released and installed 2026-11-14 (session 6). Steps A-F done; 3D passed Mark's look gate and ships as a normal route. Not finished: items left under Next, Peitgen and Indra's Pearls books.

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

- Books: Mark chose both (set fractalwright-next-2026-11-14, closed): Indra's Pearls and Peitgen, Chaos and Fractals. He buys them; distill when on disk.
- FW_COMFY_HOSTS set with setx to 127.0.0.1:8199,192.168.86.100:8188 (Mark's pick).

## Next (Mark's rank: gpudeep, path tracing, mesh, paper checks)

1. Worth heavy run done: KEEP with trims (ai-docs/notes/2026-11-14-worth-heavy.md). Do on a branch: fix evals/evals.json (fill {out}, tools + max_turns on value cases, evals/check_zoom.py checker, harder case for coastline); SKILL.md trims (drop per-use evergreen.json read + doctor run, add "render the preset as given; tune only when asked", move GPU/AI/audio detail to references/); re-run the fixed A/B.
2. Wiki to 0.3.0 (GPU deep route, rd --size N).
3. GPU deep follow-ups: double-float deltas (float32 gives 3.5-19% escape-count mismatches vs CPU, no blobs); GPU deep in the serve explorer.
4. Path-traced 3D.
5. 3D fractal to printable mesh (polywright-print).
6. Parameter checks against papers: symmetric icons vs Field and Golubitsky, multi-scroll attractor, Grandma's recipe vs Indra's Pearls (when book arrives), DFS word enumeration, series approximation, page rotation and stop palettes.
