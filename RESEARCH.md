# Research: fractalwright

Findings that back [skills/fractalwright/SKILL.md](skills/fractalwright/SKILL.md). Changes they caused are logged in [CHANGELOG.md](CHANGELOG.md); procedural lessons live in [LEARNINGS.md](LEARNINGS.md); test runs and their evidence in [TESTS.md](TESTS.md); schedule and state in `evergreen.json`. Protocol: MAINTENANCE.md.

Topic: Fractal rendering, deep zoom, colouring, measuring and audio-reactive visuals: tools, renderers and methods. Tier `moderate`. Last refresh 2026-11-14; next due 2026-12-14.

## Current understanding

- The creation pass ran as Step A of the build (2026-11-14): eleven reference files under [references/](references/) with dated sources. They are the research record; this file indexes them.
- Escape-time maths and smooth colouring are settled (references/02). Deep zoom past ~1e13 needs perturbation with series approximation or bilinear approximation (references/03); fw.py stops at float64.
- Render core measured in [ai-docs/plans/design.md](ai-docs/plans/design.md): NumPy float64 is the reference; headless Edge WebGL2 and moderngl are optional accelerators; float32 fails at width 1e-4.
- Known measuring values and their honest error bars: references/08. Proven in tests: Sierpinski, Koch, Mandelbrot area, mirror symmetry, Kronecker grids, decoys (spiral, random discs), lacunarity pair, fBm profile and surface H (TESTS.md).
- Moving: AI styling models (references/10), audio-visual tools and MilkDrop successors (references/09), renderer releases (references/11).

## Open questions

- Scope of neighbours (cellular automata, reaction-diffusion, tilings) waits on Mark (design.md section 6).

## Search plan

Four tracks; every refresh runs at least one query on each (scope each to the period since the last refresh; add the year). Protocol §4 explains the tracks and how tooling, practice and testing findings are judged.

Subject (the goal and the latest thinking on reaching it):

- `<query 1>`
- `<query 2>`
- Official forums of each tool, platform or vendor this unit depends on (announcements, deprecations, breaking changes and known bugs often land there before the docs): `<forum URL>` (announcements category: `<URL>`); a vendor Discourse, community site or the tool repository's GitHub Discussions. Search announcements first, then known issues, since the last check (`site:<forum host> <terms> <month>`, or Discourse `/latest.json`, a category `.rss`, `search.json?q=<terms> after:<date>`). Staff posts are primary sources; user posts are leads to confirm.

Tooling (skills, plugins, MCP servers, scripts, knowledge graphs built for this subject):

- `path:SKILL.md "<topic>"` on GitHub code search, sorted by recently updated; `npx skills find "<topic>"` and skills.sh for install counts
- `https://registry.modelcontextprotocol.io/v0/servers?search=<topic>`; fallback `"<topic>" mcp server site:glama.ai OR site:pulsemcp.com`
- `"<topic>" skill OR plugin OR "mcp server" <year> site:github.com`
- Most used: skills.sh weekly and 24-hour installs for `<topic>` (never all-time; exclude meta and installer skills); `anthropics/claude-plugins-official` and `claude-plugins-community` searched for `<topic>` (record the tier)
- Practitioner test on every candidate: commit in the last 90 days, issues answered, no bundled `*.test.*` or `conftest.py` from an unknown author, author has other work in the area, ships `evals/` or paired results; `path:SKILL.md "<topic>" evals OR benchmark`
- Provenance tiebreaker: which model and reasoning setting wrote each candidate (`evals.json` / frontmatter `model`, README or changelog credit, commit messages); prefer the latest frontier model at its highest reasoning setting, read over inferred
- Supersession sweep: `"<topic>" skill deprecated OR superseded OR archived <year>`; archive flag on every tool already listed here

Most discussed and the converged thinking (comment volume over points; what the most-used and most-discussed sources agree on becomes a claim in Current understanding):

- `hn.algolia.com/api/v1/search_by_date?query=<topic>` and `site:reddit.com/r/ClaudeAI OR r/ClaudeCode "<topic>" <month>`
- OpenAlex `works?search=<topic> agent&sort=cited_by_count:desc&filter=from_publication_date:<last check>`; the two most-cited through Semantic Scholar

Practice (how others use AI agents on this goal, and everything in between):

- `"how I use" OR "my workflow" "<topic>" "claude code" OR codex OR cursor <year>`
- `site:arxiv.org "<topic>" agent "case study" OR empirical OR telemetry <year>`
- `"<topic>" site:simonwillison.net OR site:latent.space OR site:anthropic.com/engineering <year>`; hn.algolia.com `"<topic>" agent` sorted by date

Testing (how work on this subject is verified, and how skills for it are tuned):

- `"<topic>" verify OR validate OR "smoke test" OR checker agent <year>` (what evidence shows the job was done)
- `path:SKILL.md "<topic>" test OR eval OR evals` on GitHub; `"<topic>" evals OR "eval suite" OR regression "agent skill" <year>`
- `site:arxiv.org "<topic>" agent evaluation OR benchmark <year>`; promptfoo, Inspect or DeepEval docs for assertion types that fit this subject

Best sources (primary first): <official docs / changelog / official forums of the tools used / standards body / key papers; for tooling: skills.sh, the MCP registry, the anthropics plugin catalogs; for testing: the subject's own test tools and the eval-framework docs>. Sources that proved noisy: <list, so they are skipped next time; SEO "top 10" listicles and scraped mega-directories are noise by default>.

## Findings log

Newest first. One entry per material finding; a quiet refresh gets one entry saying so. `Track` is subject, tooling, practice, or testing.

### R-20261114-3 · 2026-11-14 · Book rules for measure and identify
- Summary: seven books read into technique-harvest notes gave the measure/identify rules built in C-20261114-3. Falconer, *Fractal Geometry* (2nd ed.): speck removal, similarity dimension as an upper bound under overlap, never identify by D alone. Mandelbrot, *The Fractal Geometry of Nature*: lacunarity as a second number. Turcotte, *Fractals and Chaos in Geology and Geophysics*: profile and heightmap path (spectral slope, semivariogram, radial spectrum), no box counting on profiles. Rosenberg, *Fractal Dimensions of Networks*: fit range in decades, two-decade minimum, 15+ sizes over random offsets, local slopes and curvature, spiral and random-disc decoys. Feldman, *Chaos and Fractals*: coarse-box bias, Julia connectedness from the orbit of 0. Steeb, *The Nonlinear Workbook*: Kronecker grid family as exact inputs. Banerjee et al., *Fractal Patterns with MATLAB*: Katz dimension.
- Track: practice
- Sources: technique-harvest ai-docs/books/<slug>/notes.md for each book (chapters cited there)
- Magnitude: moderate (new commands, verdict rules)
- Measured, not taken on trust: radial beta = profile beta + 1 and D = 3 - H held on synthetic fBm (T-20261114-3). Not built (book rule, unverified): Rosenberg's 0.8-0.9 correction and N/10 point rule, sandbox estimator, Turcotte's log-normal skew flag.
- Applied: C-20261114-3

### R-20261114-1 · 2026-11-14 · Creation pass
- Summary: Step A research subagents wrote references/01-11 (history, escape-time, deep zoom, IFS and flames, L-systems and attractors, noise, 3D, measuring, audio visuals, AI models, tools and prior art), each with dated sources; the measured render core is ai-docs/plans/design.md. Cost not recorded per track (subagent runs).
- Track: subject
- Sources: references/*.md source lists (accessed 2026-11-14)
- Magnitude: n/a (initial)
- Applied: C-20261114-1
