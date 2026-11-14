# HANDOFF: fractalwright

Status: v0.2.0 released and installed 2026-11-14 (session 3). Steps A-F done; 3D passed Mark's look gate and ships as a normal route. Not finished: items left under Next, Peitgen and Indra's Pearls books, Mark's verdict on the AI video look.

Continue prompt: [plans/fractalwright-continue-prompt.md](plans/fractalwright-continue-prompt.md)

## What exists

- Public repo https://github.com/m4bwav/fractalwright, release https://github.com/m4bwav/fractalwright/releases/tag/v0.2.0, installed fractalwright@mark-local (entry in Ai/.claude-plugin/marketplace.json). Wiki 7 pages (written before 0.1.0: does not yet cover the new commands).
- fw.py commands: doctor, explain (incl. logistic cobweb/bifurcation, coastline), identify, measure, render (+ --deep perturbation to 1e-30 in fw_deep.py; --route browser via Playwright+Edge), palette, sheet, zoom, morph, loop, flashcheck, serve (explorer + /audio, loopback only), export, audio (fw_audio.py, uses musicwright mw.py envelopes >= 0.1.34, NumPy fallback), flame, lsystem, attractor (fw_gen.py), ifs, attractor-search, fif (fw_extra.py), 3d recipe|render|gate (fw_3d.py, browser only; default shadow+ao+camera), rd/ca/tiling/kleinian (fw_neighbours.py). Tests 114/114 (~95 s).
- ComfyUI hosts come from FW_COMFY_HOSTS (default loopback 8188,8199); add the Mac with FW_COMFY_HOSTS=127.0.0.1:8199,192.168.86.100:8188 (setx was refused by the permission classifier; Mark may set it).
- Evals: evals/evals.json, T-20261114-10: 13/13 after description fix; baseline 2/2 vs 0/2. Worth lite UNPROVEN (needs heavy A/B), leaning KEEP.
- Beat everscout `fractal-art`; harvest.json listed by `evergreen.py harvest targets`.

## Decisions (Mark, askwright set fractalwright-scope-2026-11-14, closed)

Name fractalwright; public; ALL neighbours in (reaction-diffusion, cellular automata, tilings, Kleinian); AI styling ON by default for video (stills exact; exact frames kept; --no-ai); Playwright+Edge first accelerator. Small rulings: MIT, no third-party presets, own shaders, fractal verdict needs two decades, band envelopes live in musicwright.

## Waits on Mark

- Books: Peitgen, Chaos and Fractals: New Frontiers (#4); Indra's Pearls (#7) now matters for Kleinian sets.
- Installed musicwright is 0.1.33: the shared clone Ai/musicwright has another session's uncommitted ai-docs/HANDOFF.md, so it was not pulled to 0.1.34.

## Next (in order)

1. Done 2026-11-14 (3dship, v0.2.0): 3D default remedies, normal route, Mandelbox scale 2.0, hybrid at p*2.5, quatjulia DE test (T-20261114-14). Left: path tracing, meshing for print.
2. AI styling pass for video: done 2026-11-14 (fw_ai.py, img2img per frame). Next: --ai-prompt/--ai-denoise flags, Wan VACE v2v route, Mark's look verdict.
3. Neighbours done 2026-11-14 (rd, ca, tiling, kleinian). Left: check Grandma's recipe against Indra's Pearls, DFS word enumeration, RD colour palettes and video.
4. Gaps: GPU perturbation in the browser, series approximation; page rotation and stop palettes; symmetric-icon params checked against Field and Golubitsky; multi-scroll attractor from a primary paper. Done 2026-11-14 (gaps PR): Julia deep zoom, WCAG flash-area rule, JS limiter browser test, Lorenz D2 range; floatexp past 1e-290 ruled out for now (log).
5. Wiki done for 0.2.0 (11 pages, PR #15). Left: evergreen-worth heavy run; RD palettes/video; next release.
6. Waits on Mark: look of the AI-styled zoom D:/ComfyUI/output/video/fractalwright_aipass/smoke_ai.mp4 vs smoke.mp4 (put on an askwright page next session if still unasked).
