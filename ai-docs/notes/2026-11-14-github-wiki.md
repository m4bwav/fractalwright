# GitHub wiki (2026-11-14)

- Wiki: https://github.com/m4bwav/fractalwright/wiki . Working copy: `Ai/fractalwright.wiki` (sibling clone, branch master).
- Pages: Home, Getting-Started, Commands, Recipe-Format, Works-With, FAQ, Development, _Sidebar, _Footer.
- First page saved through the web UI (Chrome tool) to create the .wiki.git; pages pushed over the placeholder (fast-forward).
- Verification: no registry package (unreleased), so examples ran against `main` at b510ab7 on Windows, Python 3.14.6, NumPy 2.5.2. Commands run and output: [2026-11-14-wiki-verify.out.txt](2026-11-14-wiki-verify.out.txt) (ffmpeg path masked). `wikiwright check` 0 errors; `outputs` 8 checked, 0 missing, 1 skipped (Recipe-Format JSON reflowed); `live` 7 pages, 0 failures.
- Facts the README lacks: the carpet preset reads D 1.81 vs 1.8928 on non-3^j boxes; Mandelbrot area 1.5071 at 512 px (error 0.0005); recipe view coordinates are strings.
- Update at release: rerun the commands in the out file, diff, and bump the footer version (_Footer.md names 0.1.0 unreleased); Commands.md names Python/NumPy versions.
