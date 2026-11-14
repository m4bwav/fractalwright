# HANDOFF: fractalwright

Status: v0.1.0 released and installed 2026-11-14 (session 2). Steps A-D done, F done (evals 13/13), E waits on Mark's 3D verdict. Not finished: neighbours Mark put in scope, Peitgen book.

Continue prompt: [plans/fractalwright-continue-prompt.md](plans/fractalwright-continue-prompt.md)

## What exists

- Public repo https://github.com/m4bwav/fractalwright, release https://github.com/m4bwav/fractalwright/releases/tag/v0.1.0, installed fractalwright@mark-local (entry in Ai/.claude-plugin/marketplace.json). Wiki 7 pages (written before 0.1.0: does not yet cover the new commands).
- fw.py commands: doctor, explain (incl. logistic cobweb/bifurcation, coastline), identify, measure, render (+ --deep perturbation to 1e-30 in fw_deep.py; --route browser via Playwright+Edge), palette, sheet, zoom, morph, loop, flashcheck, serve (explorer + /audio, loopback only), export, audio (fw_audio.py, uses musicwright mw.py envelopes >= 0.1.34, NumPy fallback), flame, lsystem, attractor (fw_gen.py), ifs, attractor-search, fif (fw_extra.py), 3d recipe|render|gate (fw_3d.py, browser only). Tests 89/89 (~75 s).
- ComfyUI hosts come from FW_COMFY_HOSTS (default loopback 8188,8199); add the Mac with FW_COMFY_HOSTS=127.0.0.1:8199,192.168.86.100:8188 (setx was refused by the permission classifier; Mark may set it).
- Evals: evals/evals.json, T-20261114-10: 13/13 after description fix; baseline 2/2 vs 0/2. Worth lite UNPROVEN (needs heavy A/B), leaning KEEP.
- Beat everscout `fractal-art`; harvest.json listed by `evergreen.py harvest targets`.

## Decisions (Mark, askwright set fractalwright-scope-2026-11-14, closed)

Name fractalwright; public; ALL neighbours in (reaction-diffusion, cellular automata, tilings, Kleinian); AI styling ON by default for video (stills exact; exact frames kept; --no-ai); Playwright+Edge first accelerator. Small rulings: MIT, no third-party presets, own shaders, fractal verdict needs two decades, band envelopes live in musicwright.

## Waits on Mark

- 3D gate: `python D:/m4bwa/Claude/Projects/Ai/askwright/skills/askwright/scripts/ask.py serve D:/m4bwa/Claude/Projects/Ai/fractalwright/ask/fractalwright-3d-gate-2026-11-14` (not served yet). Judge: shadow 6-0, AO 5-0-1, camera 5-0-1, all 4-0-2, fog 0-4-2. Guess: ship normal with shadow+AO+camera default. Notes: ai-docs/notes/2026-11-14-3d-gate.md.
- Books: Peitgen, Chaos and Fractals: New Frontiers (#4); Indra's Pearls (#7) now matters for Kleinian sets.
- Installed musicwright is 0.1.33: the shared clone Ai/musicwright has another session's uncommitted ai-docs/HANDOFF.md, so it was not pulled to 0.1.34.

## Next (in order)

1. Read the 3D gate answers; apply (default remedies, ship status in SKILL.md; fix Mandelbox framing and hybrid scale; numeric DE test for quaternion Julia).
2. AI styling pass for video: done 2026-11-14 (fw_ai.py, img2img per frame). Next: --ai-prompt/--ai-denoise flags, Wan VACE v2v route, Mark's look verdict.
3. Neighbours done 2026-11-14 (rd, ca, tiling, kleinian). Left: check Grandma's recipe against Indra's Pearls, DFS word enumeration, RD colour palettes and video.
4. Gaps: GPU perturbation in the browser, series approximation; page rotation and stop palettes; symmetric-icon params checked against Field and Golubitsky; multi-scroll attractor from a primary paper. Done 2026-11-14 (gaps PR): Julia deep zoom, WCAG flash-area rule, JS limiter browser test, Lorenz D2 range; floatexp past 1e-290 ruled out for now (log).
5. Wiki update for 0.1.0 commands (wikiwright); evergreen-worth heavy run; next release.
