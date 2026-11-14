# GitHub wiki (2026-11-14)

- Wiki: https://github.com/m4bwav/fractalwright/wiki . Working copy: `Ai/fractalwright.wiki` (sibling clone, branch master).
- Pages: Home, Getting-Started, Commands, Recipe-Format, Works-With, FAQ, Development, _Sidebar, _Footer.
- First page saved through the web UI (Chrome tool) to create the .wiki.git; pages pushed over the placeholder (fast-forward).
- Verification: no registry package (unreleased), so examples ran against `main` at b510ab7 on Windows, Python 3.14.6, NumPy 2.5.2. Commands run and output: [2026-11-14-wiki-verify.out.txt](2026-11-14-wiki-verify.out.txt) (ffmpeg path masked). `wikiwright check` 0 errors; `outputs` 8 checked, 0 missing, 1 skipped (Recipe-Format JSON reflowed); `live` 7 pages, 0 failures.
- Facts the README lacks: the carpet preset reads D 1.81 vs 1.8928 on non-3^j boxes; Mandelbrot area 1.5071 at 512 px (error 0.0005); recipe view coordinates are strings.
- Update at release: rerun the commands in the out file, diff, and bump the footer version (_Footer.md names 0.1.0 unreleased); Commands.md names Python/NumPy versions.

## Update for 0.2.0 (2026-11-14)

- Wiki commit 38d9853. Pages added: Video-and-Audio, Explorer, Generative, Neighbours-and-3D; Commands, Home, Getting-Started, FAQ, Recipe-Format, Development, Works-With, sidebar and footer updated.
- Verified against main at 3736ae3: [2026-11-14-wiki-verify-0.2.0.sh](2026-11-14-wiki-verify-0.2.0.sh) run from an empty folder with FW_COMFY_HOSTS="" (no GPU), output [2026-11-14-wiki-verify-0.2.0.out.txt](2026-11-14-wiki-verify-0.2.0.out.txt) (ffmpeg and musicwright paths masked). 35 commands, all exit 0. pytest 111 passed in 96 s. check 0 errors; outputs 29 checked, 0 missing, 6 skipped (excerpts, timing, local path); live 11 pages, 0 failures. everwrite tells.py not installed, prose check not run.
- Found: `fw.py --version` printed 0.1.0 on main; doctor still says moderngl is "not wired yet" and its ffmpeg line omits audio.
- Next release: rerun the .sh, `wikiwright diffout` against the saved out, bump _Footer.md.
