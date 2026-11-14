# fractalwright: the fractal plugin continue prompt

Work from `D:\m4bwa\Claude\Projects\Ai\fractalwright`. The name is a working name; changing it is a small ruling, decide and flag it in the log.

## Goal

Build an evergreen plugin that can research, understand and generate fractals. Mark's words: "a fractal plugin that can research, understand, and generate images, videos, interactive fractals, and audio spectrum fractals (like in winamp)", and later "I wonder if its possible to build 3d fractals unless they would all look ugly".

Five outputs, one knowledge base:

- **Understand**: name the family of a fractal from a picture or a formula, explain how it is made, measure it (box-counting dimension, symmetry, escape statistics) and say what would change its look.
- **Images**: exact renders from code, at any size, with the recipe saved next to the file so the same picture can be made again.
- **Videos**: zooms, parameter morphs, flame animations and loops, encoded for the place they will be shown.
- **Interactive**: a single page a person can pan, zoom and tweak in a browser, served from this machine on the loopback address only.
- **Audio spectrum fractals**: visuals driven by a song's spectrum and beats, in the line of Winamp's AVS and MilkDrop, both live in the browser and rendered offline to a video that stays in sync.
- **3D fractals**: only what passes the look gate below.

The work ends when all five outputs pass their evals, the plugin is released and installed, its beat and harvest targets exist, and every book Mark has supplied is distilled. Then HANDOFF.md says `Status: finished`.

## 1. Load state

1. Read `ai-docs/HANDOFF.md`, the end of `ai-docs/log.md`, and `ai-docs/notes/books.md`. Compare HANDOFF.md's age with run logs and commits, and trust the newer evidence.
2. If HANDOFF.md says the build has not started, also read, before designing anything:
   - the `evergreen-new` skill and one sibling's layout (`Ai/sfxwright` or `Ai/musicwright`) for the house shape: hub SKILL.md, one stdlib-first script, references loaded on demand, LEARNINGS, evals with a baseline, `harvest.json`, README banner, SECURITY.md, wiki;
   - the "Fractal plugin" entry in `Ai/plugin-backlog/new-plugins.md`;
   - the plugins this one calls and must not duplicate: comfyui-gen (GPU hosts, video models), threewright (threewright-shaders, threewright-video, threewright-web), musicwright (`mw.py` audio measures), cinewright-finish (encode and delivery), artwright-judge (blind pair ranking), polywright and polywright-print (meshes), askwright (decision pages), everscout (beats), readwright (books).
3. Standing rules are not repeated here. Their sources: `C:/Users/m4bwa/.claude/CLAUDE.md` (pull requests, merging, releases, attribution, worktrees, file links, wrap-up), the chainwright SKILL.md, and the memory index (package size budget, local servers over Artifacts, estimates in agent time, small rulings, tests always allowed, the model download floor, Krea 2 provenance, kill by PID only, queue on a busy GPU, README banner).

## 2. Read answers

For any askwright set HANDOFF.md names, run `ask.py read`, act on answered questions and close them. "Not sure" and unanswered questions stay open; never fill them with the guess.

## 3. Order of work

This is one chain. The session that runs this prompt is the master: it hands each batch (a research topic, a book, a render test, a build step in its own worktree) to a subagent, keeps only the short report and the file pointers, and hands on to a fresh session only when its own context runs low. Take the next item HANDOFF.md names, then the next step below. Update HANDOFF.md at each milestone.

### Step A. Research, written to `references/` and `kb/` with a source on every claim

One subagent per topic, in parallel:

1. **History and people**: Julia and Fatou, Mandelbrot, Barnsley, Lindenmayer, the Fractint Stone Soup group, Electric Sheep, the Mandelbulb and Mandelbox finds on Fractal Forums, the demoscene.
2. **Escape-time families**: Mandelbrot, Julia, Multibrot, Burning Ship, Tricorn, Newton and Nova, Lyapunov, Buddhabrot. Colouring: smooth iteration count, histogram, orbit traps, distance estimate, stripe average, palettes.
3. **Deep zoom**: where float and double run out, arbitrary precision, perturbation, series and bilinear approximation, glitch detection, what the current renderers do.
4. **Iterated function systems and flames**: chaos game, Barnsley's collage theorem, the flame algorithm, its variations, tone mapping and density estimation; flam3, Apophysis, JWildfire, Chaotica, Fractorium.
5. **L-systems and strange attractors**: plants, space-filling curves, Lorenz, Clifford, de Jong, symmetric icons.
6. **Noise and natural fractals**: fBm, multifractals, terrain, clouds; where this hands over to threewright and polywright.
7. **3D**: quaternion Julia, Mandelbulb, Mandelbox, kaleidoscopic IFS, hybrids; distance estimators and sphere tracing; lighting, ambient occlusion, soft shadows, fog, depth of field, colour from orbit traps; Mandelbulber, Mandelbulb3D, Fragmentarium; meshing for print.
8. **Measuring**: box-counting and correlation dimension, lacunarity, what the numbers can and cannot say about a picture.
9. **Audio visuals**: Winamp AVS, Geiss, MilkDrop and its preset language, projectM, Butterchurn; FFT windows and band maps, onset and beat detection, smoothing; which mappings read as "the music" and which look random; the Web Audio analyser; the photosensitivity flash limit.
10. **Fractals and AI models**: fractal renders as input or control for image and video models, style LoRAs, what a model can add that the maths cannot, and the licence class of each model.
11. **Tools and prior art**: existing fractal skills, plugins and MCP servers (do not duplicate one), Shadertoy, ISF, licences of every tool and preset pack the plugin might read or call.

### Step B. Beat and harvest targets

- Create an everscout beat for fractal and audio-visual art with everscout-beat: verified sources (subreddits, Fractal Forums, Shadertoy, feeds, GitHub), entities, a question bank and a literature list. Findings land in LEARNINGS for review, never straight in the skill.
- Add `harvest.json` to the plugin so the technique harvest (`Ai/technique-harvest`, `evergreen.py harvest targets --json`) picks it up.

### Step C. Design note, then decisions

Write `ai-docs/plans/design.md`. It must settle, by measurement and not by taste:

- **The render core.** Pure Python is too slow for this work. Test the candidates against each other on speed, install size and how many of the five outputs one code path serves: NumPy on the CPU, GLSL run headless, a WebGL or WebGPU page driven by a headless browser (the same shader then serves stills, video frames, the interactive page and the audio page), and the ComfyUI hosts for AI passes only. Keep the install small; a heavy dependency is optional and probed, never required.
- **The recipe file**: one JSON per render with formula, parameters, view, palette, size, seed and tool version, enough to redraw it.
- **Scope edges**: which neighbours are in (cellular automata, reaction-diffusion, tilings) and which are pointers to other plugins.

Open choices go on an askwright page (name, public or private repo, which neighbours are in, how much AI styling he wants); carry on with the guesses meanwhile.

### Step D. Build `fw.py` and the pages, each command proven before the next

- `doctor`, `explain` (family, formula, how it is made), `identify` (picture in, family and likely parameters out), `measure`.
- `render` (stills from a recipe or a named preset), `palette`, `sheet` (contact sheet of variations for a pick).
- `zoom`, `morph`, `loop` (video: keyframes in, frames and an encoded file out, through ffmpeg).
- `serve` (the interactive explorer, one HTML file, share link carries the view), `export` (the current view to a recipe).
- `audio` (song in, synced video out; frame-stepped, never real-time capture) and the live audio page (file or microphone).
- `flame` and `lsystem` once the escape-time path is solid.

Proof bars, numbers and not opinions:

- Known values: the Mandelbrot set's area near 1.5066, the Sierpinski triangle's dimension log 3 / log 2, the Koch curve's log 4 / log 3, mirror symmetry across the real axis. `measure` must hit them within a stated tolerance.
- The same recipe gives the same pixels twice. A deep zoom shows no glitch blobs against a slow reference render of the same view.
- Loops: the seam frame pair differs no more than a neighbouring pair.
- Audio: a sine sweep lights the bands in order, silence gives a calm frame, a click track's beats land within one frame, and no output exceeds three flashes a second.
- Pictures a person will judge go through artwright-judge blind pairs first, then to Mark on an askwright page.

### Step E. The 3D look gate

3D fractals can be built; the route is a distance estimator marched by rays, and the research in A7 covers it. Mark's worry is that they come out ugly. Treat that as a hypothesis to test, not a reason to skip:

1. Render a baseline the lazy way (default formula, flat light, iteration colouring).
2. Render the same views with each remedy the research names, one at a time and then together: ambient occlusion, soft shadows, fog and depth cues, orbit-trap colour, depth of field, anti-aliasing, better formulas and hybrids, a composed camera.
3. Rank baseline against remedies in blind artwright-judge pairs, then put the best sheet on an askwright page for Mark.
4. Ship 3D as a normal route only if the judge prefers the remedies and Mark picks at least one render he would keep. Otherwise ship it marked experimental, or leave it out, and write down what failed. Meshing for print (through polywright-print) is a separate small test after the gate.

### Step F. Skill, evals, release

Hub skill (and siblings only if the catalogue lint says one description cannot carry it), eval suite with a no-skill baseline (evergreen-test), worth check (evergreen-worth), README with banner, SECURITY.md, wiki (wikiwright), then repository, release and install as the standing rules say. Add the plugin to `Ai/plugin-backlog/existing-plugins.md` when released and keep its `new-plugins.md` entry's status line current.

### Step G. Books

`ai-docs/notes/books.md` lists what Mark could supply, with a status per title. When one turns up on disk (`Ai/technique-harvest/scripts/book_harvest.py find`), a reader subagent distills it with readwright under `Ai/technique-harvest/ai-docs/books/BUILD-BRIEF.md`; only tested rules enter the skill. Free online titles are fetched and read without waiting.

## 4. Stop before anything that needs the owner

Put the question on an askwright page, record the set in HANDOFF.md, and carry on with other work. These wait on Mark:

- making the repository public, and the final name;
- installing or running downloaded third-party programs (Mandelbulber, JWildfire, projectM, Chaotica and the like); reading their docs and file formats is free;
- shipping or redistributing anyone's presets, palettes or shader code whose licence is not clearly open, Winamp and MilkDrop preset packs included;
- anything the "tests always allowed" grant excludes: disk space, security, legal questions, renders that tie up a GPU for hours;
- any unattended or scheduled run;
- publishing to a package registry or the Claude directory;
- buying books.

## 5. Stop early

If HANDOFF.md says `Status: finished`, or nothing can move without Mark, say what waits and stop. Waiting on a review of pictures never ends a session while research, tests, evals or books remain.

## 6. Hand over

Run the wrap-up (evergreen-wrapup, if installed; a failure is reported and never blocks), update `ai-docs/log.md` and `ai-docs/HANDOFF.md`, and only then print the start command: `Execute D:/m4bwa/Claude/Projects/Ai/fractalwright/ai-docs/plans/fractalwright-continue-prompt.md`, with the folder to start in (`D:/m4bwa/Claude/Projects/Ai`). State goes in HANDOFF.md, never in this file.
