# HANDOFF: fractalwright

Status: v0.2.2 (AI styling off by default, Mark 2026-11-14) released and installed 2026-11-14 (session 5). Steps A-F done; 3D passed Mark's look gate and ships as a normal route. Not finished: items left under Next, Peitgen and Indra's Pearls books.

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

- Open askwright set ask/fractalwright-next-2026-11-14 (books, Mac host, order of remaining items, heavy worth run). Run ask.py read first; act on its rank for item 4 order.

- Books: Peitgen, Chaos and Fractals: New Frontiers (#4); Indra's Pearls (#7) now matters for Kleinian sets.
- Installed musicwright is 0.1.33: the shared clone Ai/musicwright has another session's uncommitted ai-docs/HANDOFF.md, so it was not pulled to 0.1.34.

## Next (in order)

1. Done 2026-11-14 (3dship, v0.2.0): 3D default remedies, normal route, Mandelbox scale 2.0, hybrid at p*2.5, quatjulia DE test (T-20261114-14). Left: path tracing, meshing for print.
2. AI styling pass for video: done 2026-11-14 (fw_ai.py, img2img per frame). Flags --ai-prompt/--ai-denoise/--ai-seed done in 0.2.1. Mark chose exact and AI off by default (0.2.2); Wan VACE v2v dropped unless he asks.
3. Neighbours done 2026-11-14 (rd, ca, tiling, kleinian). Left: check Grandma's recipe against Indra's Pearls, DFS word enumeration, (RD palettes and video done in 0.2.1).
4. Gaps: GPU perturbation in the browser, series approximation; page rotation and stop palettes; symmetric-icon params checked against Field and Golubitsky; multi-scroll attractor from a primary paper. Done 2026-11-14 (gaps PR): Julia deep zoom, WCAG flash-area rule, JS limiter browser test, Lorenz D2 range; floatexp past 1e-290 ruled out for now (log).
5. Wiki done for 0.2.2 (12 pages, wiki commit 46ce592, 2026-11-14): rd palettes/video, opt-in AI flags, Versions page. Left: evergreen-worth heavy run.
6. Next up: fix `rd --size 64` crash (fw_neighbours.py _size wants WxH; give a clean usage error), then the gaps in item 4 in Mark's ranked order. (Wiki work for rd and the AI flags done 2026-11-14.)
