# 11. Tools and prior art

Accessed 2026-11-14. Purpose: make sure fractalwright duplicates nothing that already exists, knows every licence it touches, and picks a render core that works headless on Windows. GitHub facts (licence SPDX id, last push, stars) come from `gh api repos/<owner>/<repo>` on 2026-11-14. Rows marked **(unverified)** come from secondary sources or memory and need a primary check before the plugin relies on them.

## 1. Agent skills, plugins, MCP servers and LLM tools

| Name | What it does | Licence | Activity | Relevance |
|---|---|---|---|---|
| wilsonchenghy/ShaderToy-MCP | Python MCP server: `get_shader_info`, `search_shader` against the Shadertoy API (needs `SHADERTOY_APP_KEY`) | MIT | last push 2025-05-07, 51 stars | Lookup only, no rendering. Do not rebuild a Shadertoy search; link to it. Fetched shaders keep their own licences (see 3). |
| ckorhonen/claude-skills `shadertoy` | SKILL.md for writing and debugging Shadertoy/GLSL fragment shaders, incl. domain folding, ray marching, SDFs | not checked (unverified) | listed on skills.sh, skillsmp | Overlaps the "write a GLSL fractal" knowledge. fractalwright should go beyond: measure, render headless, explain maths. |
| bfollington/terma `shadertoy` | GLSL/Shadertoy reference skill | not checked (unverified) | ~52 stars per directory | Same overlap; reference only. |
| MiniMax-AI/skills `shader-dev` | Ray marching, SDF, fluids, particles skill | MIT per directory (unverified) | active 2026 | Same overlap. |
| jjuidev/jss `shader` | SDF, noise, fBm fragment shaders for WebGL/three.js | unverified | - | Same overlap. |
| "Generative Art Algorithms" (mcpmarket) | Noise, flow fields, L-systems, fractal geometry, seeded randomness | unverified | - | Closest to fractal maths; thin. |
| omer-metin generative-art | Persona skill, p5.js/Processing/GLSL | unverified | - | Low. |
| tdimino rocaille-shader | Domain-warp shader to HTML or Shadertoy | unverified | - | Low. |
| "fractal" MCP servers (compspec/fractale-mcp, @fractal-mcp/mcp, Fracktal-MCP) | Unrelated (agent orchestration, memory) despite the name | various | - | None. Name collision only. |
| Mark's own: threewright, artwright, musicwright, pixelwright, polywright | three.js scenes; image measurement/judging; music; pixel art; 3D meshes | Mark's | active | **Delegate** to these (see Implications), do not rebuild. |

Finding: no agent skill or MCP server found that renders, measures (box-counting dimension, etc.), deep-zooms or animates fractals. The niche is open; the nearest neighbours are generic shader-writing skills.

## 2. Python packages and render-core options

| Package | What | Licence | Size / maintenance | Relevance |
|---|---|---|---|---|
| fractalshades (GBillotey) | Arbitrary-precision Mandelbrot deep zoom (perturbation, BLA), numba-based, GUI explorer | MIT | 1.2.1 (2025-05-11); win_amd64 wheels for CPython 3.9-3.13; sdist 17.2 MB; repo push 2026-08-30, 37 stars | Best existing Python deep-zoom engine. Optional backend for `fw.py deepzoom`; do not reimplement perturbation unless stdlib-only is required. No wheel for 3.14 yet (check). |
| numba | JIT for NumPy loops | BSD-2 (unverified) | large (llvmlite ~30-40 MB, unverified) | Pulled in by fractalshades; fine for an optional extra, too big for core. |
| moderngl | OpenGL 3.3+ binding; standalone (headless) context | MIT | 5.13.0 (2026-10-07); win wheels ~110 KB; repo push 2026-10-21, 2.3k stars | **Top GLSL candidate.** Tiny. Windows standalone context uses WGL via opengl32.dll; needs a GPU driver, no display server issue on Windows desktop. One user report of a hang with `standalone=True` under pygame. |
| glcontext | Context backends for moderngl (wgl, egl, x11, darwin) | MIT | push 2026-11-01 | EGL backend is Linux-only in practice; on Windows use wgl. |
| wgpu-py | WebGPU (wgpu-native) for Python; render to texture without a canvas | BSD-2-Clause | v0.33.0 (2026-11-06); `wgpu-0.33.0-py3-none-win_amd64.whl` = 3.46 MB; push 2026-11-10, 712 stars | **Second candidate.** Headless by design (render to texture, read back to numpy). Uses D3D12/Vulkan on Windows. WGSL not GLSL, so Shadertoy-style GLSL needs porting (wgpu-native accepts GLSL via naga for some stages; unverified). |
| rendercanvas (pygfx) | Canvas abstraction incl. offscreen for wgpu-py | BSD-2-Clause | push 2026-11-05 | Optional helper; not needed for pure offscreen. |
| vispy | Scientific visualisation on OpenGL | BSD-style (GitHub reports NOASSERTION) | push 2026-11-13, 3.6k stars | Overkill; skip. |
| taichi | GPU kernels in Python (CUDA/Vulkan/Metal/CPU) | Apache-2.0 | push 2026-10-05, 28k stars; wheels tens of MB (unverified); release cadence slowed | Fast escape-time kernels, but heavy and Python-version lagging. Not core. |
| pyglet / glfw | Windowing libs | BSD / zlib (unverified) | - | Only for an interactive desktop window; browser explorer covers that need. |
| pyvvisf | Pure-Python ISF renderer (PyOpenGL + json5) | unverified | PyPI | Could load ISF files; check maturity before using. |
| Playwright + Chromium | Headless browser screenshots of a WebGL/WebGPU page | Apache-2.0 (Playwright) | Chromium download ~150 MB+ (unverified) | WebGL works headless (SwiftShader fallback or GPU). WebGPU headless needs `--enable-unsafe-webgpu` and GPU flags; Chrome's guide documents Linux flags; reports of black canvas captures. Treat headless WebGPU on Windows as **unproven** until tested. |

### Render-core candidates (feeds the design decision)

| Option | Install size | Headless on Windows | GLSL reuse | Notes |
|---|---|---|---|---|
| A. stdlib + optional NumPy (CPU escape-time, write PNG via zlib) | 0 (NumPy ~15 MB if used) | Yes, always | No | Guaranteed floor; slow at 4K/video; fine for previews, measurement, tests. |
| B. moderngl standalone | ~0.1 MB + GPU driver | Yes via WGL (needs a real GPU driver; RDP/no-GPU VMs may lack GL 3.3) | Yes (GLSL 330 fragment shaders, Shadertoy-style with a small `mainImage` wrapper) | Recommended GPU core: tiny, GLSL matches the browser explorer's WebGL shaders 1:1. |
| C. wgpu-py offscreen | 3.46 MB | Yes (render to texture, no canvas) | No, WGSL (port needed) | Better future-proofing and compute shaders; second shader dialect to maintain. |
| D. fractalshades | wheel + numba/llvmlite (tens of MB) | Yes (CPU) | n/a | Deep zoom beyond float64 only. Optional extra. |
| E. Playwright headless Chromium | ~150 MB+ browser | WebGL yes; WebGPU unproven | Same page as explorer | Use only to screenshot/verify the browser explorer, not as the main renderer. |

Suggested shape: A as the stdlib floor, B as the optional GPU path, D as optional deep zoom, E only for testing the explorer. C stays a watch item.

## 3. Shader ecosystems

| Name | What | Licence | Status | Relevance |
|---|---|---|---|---|
| Shadertoy | Online GLSL gallery and API | Site default for shaders: CC BY-NC-SA 3.0 Unported unless the author states otherwise (per secondary sources quoting the terms page; shadertoy.com/terms returned 403 to WebFetch, so **unverified at primary source**) | active | Never vendor Shadertoy code into the plugin or into commercial output. NC forbids commercial use; SA forces the same licence on remixes. Only reuse shaders whose header states a permissive licence (some state CC0/MIT). Write our own shaders from the maths. |
| ISF (Interactive Shader Format) | JSON header + GLSL fragment shader with typed inputs, used by VDMX, Resolume and others | Spec repo mrRay/ISF_Spec: MIT; Vidvox/ISF-Files: MIT | spec push 2025-03, files push 2026-06 | Good **export** format for audio-reactive/VJ use: fw.py can emit `.fs` ISF files (inputs = zoom, centre, iterations, audio level). |
| glslViewer (Patricio Gonzalez Vivo) | Console GLSL sandbox, headless renders, sequences | BSD-3-Clause | push 2026-11-02, 5.4k stars | External optional tool; fw.py could hand a shader to it. Do not rebuild its CLI. Windows build availability unverified. |
| GLSL Sandbox (mrdoob) | Web shader editor and gallery | MIT (code); gallery shaders have no stated licence (unverified) | push 2026-08-25 | Inspiration only; gallery code is not cleared for reuse. |
| twigl | Compact web GLSL editor (geeker/golf modes) | unverified (repo not found at twigl/twigl.app) | - | Inspiration for a minimal explorer; no reuse planned. |

## 4. Desktop fractal programs and file formats

| Program | What | Licence | Maintenance | Formats fw.py could read/write |
|---|---|---|---|---|
| Ultra Fractal | Commercial 2D fractal editor with layers, formula database | Commercial (unverified) | active (unverified) | `.upr` parameter sets, `.ufm` formulas, `.ucl` colourings, `.ugr` gradients, `.uxf` transforms (unverified). Text formats; parse `.ugr` gradients and simple `.upr` = useful import. |
| Fractint / Xfractint | Classic DOS/Unix escape-time program | Freeware; source terms (FRACTSRC.DOC): not for commercial fractal programs, modified versions may not be distributed; Debian ships it in non-free | legacy | `.par` parameter files, `.frm` formulas, `.map` palettes (256 RGB lines). Reading formats is fine; **do not copy Fractint source**. |
| Iterated Dynamics / ManPWin | Fractint forks | inherit Fractint terms (unverified) | active forks | Same formats. |
| ChaosPro | Freeware Windows fractal program | Freeware, closed (unverified) | inactive (unverified) | Own formula language; low priority. |
| XaoS | Real-time zoomer | GPL-2.0 | push 2026-09-11, 628 stars | `.xpf` position files, `.xaf` animation files (unverified). Do not copy code (GPL). |
| Mandelbulber2 | 3D fractal ray marcher, OpenCL, animation, CLI | GPL-3.0 | push 2026-11-14, 1.1k stars | `.fract` text settings (`[main_parameters]` key-value), CSV keyframes; CLI `mandelbulber2 [options] settings_file` with `--override KEY=VALUE`, `--format`. Best 3D hand-off: write `.fract`, call its CLI if installed. |
| Mandelbulb3D | 3D fractal program (Delphi) | LGPL-2.1 (thargor6/mb3d) | push 2023-03 | `.m3p` parameters (unverified). Low priority. |
| JWildfire | Fractal flames, Java | No SPDX on GitHub; README states LGPL-2.1-or-later (checked https://github.com/thargor6/JWildfire 2026-11-14) | push 2026-08-30 | `.flame` XML (flam3 format). |
| Apophysis (7X) | Fractal flame editor | GPL-3.0 (checked https://github.com/xyrus02/apophysis-7x 2026-11-14) | legacy | `.flame` XML. |
| Chaotica | Commercial flame renderer | Commercial (unverified) | active (unverified) | Imports `.flame`; own `.chaos`. |
| flam3 (Scott Draves) | Reference flame renderer and XML format | GPL-3.0 (checked https://github.com/xyrus02/apophysis-7x 2026-11-14) | legacy | `.flame` XML is the common interchange; fw.py should read/write it. |
| Kalles Fraktaler 2+ | Perturbation deep-zoom Mandelbrot (Windows) | AGPL-3.0+ (fork by Claude Heiland-Allen, per Wikipedia) | active per mathr.co.uk (unverified) | `.kfr` text location files (Re, Im, Zoom, Iterations), `.kfb` iteration maps (int32 iterations + float32 smooth plane). `.kfr` import/export lets users move deep-zoom locations. |
| Fractal eXtreme | Commercial Windows explorer | Commercial (unverified) | quiet | Skip. |
| Fragmentarium / FragM | GPU GLSL fractal IDE | Fragmentarium: no SPDX on GitHub (originally LGPL/GPL, unverified); FragM: GPL-3.0 | FragM push 2025-11 | `.frag` GLSL with `#include` and slider annotations. Reading slider syntax is fine; do not vendor its `.frag` library (GPL). |

## Do not duplicate

1. Shadertoy search/fetch: ShaderToy-MCP exists (MIT).
2. Generic "write a GLSL shader" guidance: several shader skills exist; fractalwright only adds fractal-specific maths, measurement and rendering.
3. Arbitrary-precision perturbation deep zoom: use fractalshades (MIT) or point to Kalles Fraktaler; do not rewrite.
4. 3D fractal ray-marching engine with GUI: Mandelbulber2 does it; fractalwright writes `.fract` and calls it.
5. Fractal flame renderer: JWildfire/flam3/Chaotica exist; at most a small reference flame renderer for tests, plus `.flame` I/O.
6. Console shader runner: glslViewer.
7. three.js scenes, mesh export, image judging, music generation, pixel-art: threewright, polywright, artwright, musicwright, pixelwright.

## Implications for fractalwright

- Gap confirmed: nothing combines explaining, measuring (dimension, escape statistics), generating and animating fractals for an agent. That is the product.
- `fw.py` core stays stdlib (CPU escape-time, PNG via zlib, JSON recipes); `[gpu]` extra = moderngl (~0.1 MB); `[deep]` extra = fractalshades; browser explorer shares the same GLSL as moderngl.
- Write every shader from scratch and license the plugin's shaders permissively (MIT) so users can sell output. Record the licence and origin of any imported shader in its recipe.
- Importers worth building first (text, small): `.kfr`, `.map`, `.ugr`, `.flame`, `.fract` (write), ISF `.fs` (write). All are file formats, not code, so reading/writing them raises no licence issue.
- Audio-reactive: emit ISF for VJ tools; hand music to musicwright.
- 3D: hand meshes to polywright, scenes to threewright; heavy 3D renders to Mandelbulber2 if installed.
- Headless WebGPU is not a dependency anywhere until tested on this PC.

## Open questions

1. Primary text of shadertoy.com/terms (403 to WebFetch): confirm CC BY-NC-SA 3.0 default and API terms; try a browser.
2. moderngl `standalone=True` on this Windows PC (RTX 5060 Ti): quick test; also behaviour over RDP.
3. wgpu-py: GLSL input via naga in v0.33, and offscreen readback speed for video frames.
4. Playwright headless Chromium WebGPU on Windows: does `--enable-unsafe-webgpu --headless=new` give a non-black canvas?
5. fractalshades: Python 3.14 wheels, full dependency size (numba, gmpy2?).
6. Exact licences: JWildfire, Fragmentarium, Apophysis 7X, flam3, Ultra Fractal format docs, KF2+ current release.
7. Licences of the listed shader skills (for attribution if any idea is borrowed).

## Sources

- https://github.com/wilsonchenghy/ShaderToy-MCP ; https://glama.ai/mcp/servers/@wilsonchenghy/ShaderToy-MCP
- https://skills.sh/ckorhonen/claude-skills/shadertoy ; https://skills.cat/skills/bfollington/terma/shadertoy ; https://open-design.ai/ar/skills/shader-dev/ ; https://playbooks.com/skills/jjuidev/jss/shader ; https://mcpmarket.com/tools/skills/generative-art-algorithms ; https://skills.sh/omer-metin/skills-for-antigravity/generative-art ; https://openskillindex.com/skills/tdimino-claude-code-minoan-rocaille-shader
- https://github.com/compspec/fractale-mcp ; https://lobehub.com/mcp/gorygrey-fracktal-mcp
- https://pypi.org/project/fractalshades/ ; https://github.com/GBillotey/Fractalshades ; https://gbillotey.github.io/Fractalshades-doc/getting_started.html
- https://pypi.org/project/moderngl/ ; https://moderngl.readthedocs.io/en/stable/topics/context.html ; https://github.com/moderngl/glcontext
- https://github.com/pygfx/wgpu-py (release v0.33.0 assets) ; https://wgpu-py.readthedocs.io/en/stable/guide.html ; https://github.com/pygfx/rendercanvas
- https://github.com/vispy/vispy ; https://github.com/taichi-dev/taichi ; https://pypi.org/project/pyvvisf/
- https://developer.chrome.com/blog/supercharge-web-ai-testing?hl=en ; https://vgpu.labs.vercel.dev/guides/agent-browser-webgpu
- https://www.shadertoy.com/terms (403) ; https://godotshaders.com/shader/notebook-drawings/ ; https://magicmusicvisuals.com/forums/viewtopic.php?p=3529 ; https://creativecommons.org/licenses/by-nc-sa/3.0/
- https://github.com/mrRay/ISF_Spec ; https://github.com/Vidvox/ISF-Files ; https://docs.isf.video/
- https://github.com/patriciogonzalezvivo/glslViewer ; https://github.com/mrdoob/glsl-sandbox
- https://github.com/xaos-project/XaoS ; https://github.com/buddhi1980/mandelbulber2 ; https://manpages.org/mandelbulber2 ; https://www.fractalforums.com/releases-b233/mandelbulber-v2-2-09 ; https://flathub.org/apps/com.github.buddhi1980.mandelbulber2
- https://github.com/thargor6/mb3d ; https://github.com/thargor6/JWildfire ; https://github.com/3Dickulus/FragM ; https://github.com/Syntopia/Fragmentarium
- https://en.wikipedia.org/wiki/Kalles_Fraktaler ; https://en.wikibooks.org/wiki/Fractals/kf-extras ; https://mrob.com/pub/muency/kallesfraktaler.html
- https://en.wikipedia.org/wiki/Fractint ; https://metadata-backend.ftp-master.debian.org/changelogs/non-free/x/xfractint/stable_copyright ; https://launchpad.net/ubuntu/focal/+source/xfractint/+copyright
