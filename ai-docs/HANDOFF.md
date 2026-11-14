# HANDOFF: fractalwright

Status: Steps A, B, C done; Step D in progress (2 batches merged); public repo, no release yet. Updated 2026-11-14 end of session 1.

Continue prompt: [plans/fractalwright-continue-prompt.md](plans/fractalwright-continue-prompt.md)

## What exists

- Public repo https://github.com/m4bwav/fractalwright (main), wiki https://github.com/m4bwav/fractalwright/wiki (7 pages; notes in notes/2026-11-14-github-wiki.md). Banner and social preview rendered by fw.py (.github/images). MIT. No release: tag v0.1.0 only after evals/evals.json is written (still TODO prompts) and run with a baseline.
- Research: references/01-11 (history, escape-time, deep zoom, IFS/flames, L-systems/attractors, noise, 3D, measuring, audio visuals, AI models, tools/prior art). Two verification passes done; remaining unverified items are marked in place.
- Design: [plans/design.md](plans/design.md). Render core decided by measurement (bench/bench.py): NumPy float64 required; optional accelerators probed in order: headless browser (Playwright + system Edge, WebGL2), then moderngl float64. wgpu dropped. float32 GPU fails at 1e-4 views.
- Code: scripts/fw.py with doctor, explain, render (mandelbrot, julia, burning-ship, tricorn, multibrot, kronecker; recipe JSON saved beside each PNG), measure (box with verdicts and decades, area, lacunarity, ifs, profile, katz, heightmap), identify v1, palette. tests/test_fw.py: 30/30 (about 70 s).
- Beat: everscout `fractal-art` (Ai/indie-ai-scout/beats/fractal-art, 28 verified sources; fractalforums.org dead in a redirect loop on 2026-11-14, recheck later). harvest.json at root; `evergreen.py harvest targets` lists it.
- Sibling READMEs and wikis carry a fractalwright "Works with" line (10 PRs merged 2026-11-14). askwright's install is at 399/400 KB: its next README addition fails the size check.

## Books

- Read and noted (technique-harvest/ai-docs/books/<slug>/notes.md): Falconer, Mandelbrot FGoN (OCR scan), Pickover (OCR), Feldman, Steeb, Banerjee MATLAB, numerical fractal-fractional, Turcotte, Rosenberg, Musimathics 1-2. Closed: fractional calculus (skipped), Blender x2 (built into polywright 0.6.7), Microscope (ludowright 0.1.34), 3ds Max (skipped). sfxwright 0.1.26 / musicwright 0.1.33 got the Musimathics sfx/music items.
- fractalwright book items not yet built are listed in ai-docs/log.md "book verdicts" lines (2026-11-14). Built in batch 2: the measure/identify items. Still to build: Sprott preference ranking in attractor search, IFS |det| probabilities, Mariani-Silver (test-first, pixel-identical bar), Canright framing (test-first), Lyapunov units bits/nats fix in refs/02, beginner teaching order + cobweb/bifurcation in explain, Richardson coastline in explain, FFT terrain default (test-first vs midpoint creases), fractal interpolation family (test-first), grey-level IFS (test-first), multi-scroll attractor (test-first), audio items (critical-band edges, 200 ms loudness window, chroma->hue, no MP3, longer sub-bass frame, Shepard-Risset note).
- Close each book with `book_harvest.py done <slug> --verdict built` once its fractalwright items are built. Still wanted: Peitgen, Chaos and Fractals: New Frontiers of Science (#4).

## Decisions and small rulings (change freely)

- Name fractalwright; public since Mark's word on 2026-11-14.
- MIT; no third-party presets bundled; no GPL/AGPL code copied; own shaders; AI passes optional and off by default, outputs marked interpreted.
- Fractal verdict needs at least two decades of fit range.
- Per-frame band envelopes belong in musicwright mw.py, not here.

## Waits on Mark

- askwright set ask/fractalwright-scope-2026-11-14 (Q2 visibility now answered: public). Read: `python D:/m4bwa/Claude/Projects/Ai/askwright/skills/askwright/scripts/ask.py read D:/m4bwa/Claude/Projects/Ai/fractalwright/ask/fractalwright-scope-2026-11-14`. Guesses in force meanwhile (neighbours: reaction-diffusion in only; AI optional; browser accelerator first).
- Books: Peitgen #4 if he has it.

## Next (in order)

1. Read askwright answers and apply.
2. Step D batch 3: `sheet`, then `zoom`/`morph`/`loop` (ffmpeg; loop seam bar), deep-zoom perturbation path (refs/03).
3. Build the remaining fractalwright book items above, closing books as their items land.
4. Batch 4: `serve` + `export` (interactive page, loopback only), then `audio` + live audio page (add per-frame band envelopes to musicwright first), then `flame`, `lsystem`, attractors.
5. Step E 3D look gate; Step F evals (evergreen-test with baseline), worth check, release v0.1.0, install, existing-plugins.md.
