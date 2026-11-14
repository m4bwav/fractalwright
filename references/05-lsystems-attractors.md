# 05 - L-systems and strange attractors

Research notes for fractalwright. Accessed 2026-11-14 unless noted. Claims marked
**(unverified)** come from well-known sources I did not re-fetch this session; check them
before relying on them in tests.

## 1. L-system kinds

| Kind | What changes | Primary source |
|---|---|---|
| D0L (deterministic, context-free) | One production per letter, all letters rewritten in parallel each step | ABOP ch. 1.1-1.3 [S1] |
| Bracketed 0L | Adds `[` push and `]` pop of turtle state, so branches | ABOP 1.6, Fig. 1.24 [S1] |
| Stochastic 0L | Several productions per letter, each with probability pi(p); probabilities per predecessor sum to 1; chosen per occurrence | ABOP 1.7, p. 28, Fig. 1.27 [S1] |
| Context-sensitive (1L/2L) | Production `al < a > ar -> x` applies only when neighbours match; brackets skipped when matching context | ABOP 1.8, Figs. 1.31 (unverified fig. no.) [S1] |
| Parametric | Letters carry numeric params `A(l,w)`, productions have conditions `: l > 1` and arithmetic | ABOP 1.10 [S1] |

Edge-rewriting vs node-rewriting: ABOP Fig. 1.24 caption says (a)-(c) are edge-rewriting
(rules on `F`), (d)-(f) node-rewriting (rules on a non-drawing letter `X`, plus `F -> FF`) [S1].

## 2. Grammar spec for an `lsystem` command

Proposed file format (YAML/JSON, one preset per file or a list):

```yaml
name: abop-1.24a
axiom: F
rules:                       # D0L / bracketed
  F: "F[+F]F[-F]F"
# stochastic: a list of [weight, successor]
# rules: { F: [[0.33, "F[+F]F[-F]F"], [0.33, "F[+F]F"], [0.34, "F[-F]F"]] }
# context-sensitive: key "L<A>R", "*" = any; ignore: "+-F" letters skipped when matching
# parametric: rules: [{pred: "A(l)", cond: "l>1", succ: "F(l)[+A(l*0.7)]"}]
angle: 25.7                  # degrees, delta
iterations: 5
step: 1.0                    # F length; scale per depth optional
length_factor: 1.0           # for > and <
width: 1.0
width_factor: 0.7            # for ! (ABOP) / # !
seed: 1                      # stochastic determinism
heading: 90                  # initial turtle heading, 90 = up
source: "ABOP Fig. 1.24a"
```

Rewriting rules for the engine:
- Rewrite every letter in parallel; letters with no rule copy through (identity).
- Stochastic choice uses a seeded PRNG per occurrence, so `--seed` reproduces a plant.
- Guard string growth: estimate length per iteration and refuse above a cap (e.g. 10^7 symbols)
  unless `--force`. Peano at n=5 or Gosper at n=6 already reach millions.

### Turtle symbols (2D and 3D)

2D set as in Paul Bourke's L-system page [S2]; 3D set is ABOP 1.5 [S1] (unverified symbol wording).

| Symbol | Meaning |
|---|---|
| `F` (also `G`, configurable) | forward one step, draw |
| `f` | forward, no line |
| `+` / `-` | turn left / right by delta (ABOP: `+` left) |
| `&` / `^` | pitch down / up (3D, ABOP) |
| `\` / `/` | roll left / right (3D, ABOP) |
| `\|` | turn around 180 deg |
| `[` / `]` | push / pop state (position, heading, width, colour) |
| `!` / `#` | decrease / increase line width (Bourke) |
| `>` / `<` | multiply / divide length by length_factor (Bourke) |
| `@` | dot of current width (Bourke) |
| `{` / `}` | start / close and fill polygon (leaves) |
| `(` / `)` | decrease / increase angle by an increment (Bourke) |
| other letters | ignored by turtle (rewrite only) |

Note: Bourke uses `&` for "swap + and -" [S2]; ABOP uses `&` for pitch. Pick ABOP meanings
in 3D mode and document the 2D difference.

## 3. Preset table

All angles in degrees. n = suggested iterations.

| Preset | Axiom | Rules | Angle | n | Source |
|---|---|---|---|---|---|
| abop-1.24a | F | F->F[+F]F[-F]F | 25.7 | 5 | ABOP Fig 1.24a [S1] |
| abop-1.24b | F | F->F[+F]F[-F][F] | 20 | 5 | ABOP Fig 1.24b [S1] |
| abop-1.24c | F | F->FF-[-F+F+F]+[+F-F-F] | 22.5 | 4 | ABOP Fig 1.24c [S1] |
| abop-1.24d | X | X->F[+X]F[-X]+X; F->FF | 20 | 7 | ABOP Fig 1.24d [S1] |
| abop-1.24e | X | X->F[+X][-X]FX; F->FF | 25.7 | 7 | ABOP Fig 1.24e [S1] |
| abop-1.24f | X | X->F-[[X]+X]+F[+FX]-X; F->FF | 22.5 | 5 | ABOP Fig 1.24f [S1] |
| abop-1.27 stochastic | F | F->(.33)F[+F]F[-F]F (.33)F[+F]F (.34)F[-F]F | (not stated on p.28) ~25 | 5 | ABOP p.28 / Fig 1.27 [S1] |
| hilbert | X | X->-YF+XFX+FY-; Y->+XF-YFY-FX+ | 90 | 5-7 | Bourke [S2] |
| peano | X | X->XFYFX+F+YFXFY-F-XFYFX; Y->YFXFY-F-XFYFX+F+YFXFY | 90 | 3-4 | Bourke [S2] |
| dragon | FX | X->X+YF+; Y->-FX-Y | 90 | 10-14 | Bourke [S2] |
| gosper-hex | XF | X->X+YF++YF-FX--FXFX-YF+; Y->-FX+YFYF++YF+FX--FX-Y | 60 | 4 | Bourke [S2] |
| gosper-quad | -YF | (long; copy from [S2]) | 90 | 2-3 | Bourke [S2] |
| sierpinski-arrowhead | YF | X->YF+XF+Y; Y->XF-YF-X | 60 | 6-8 | Bourke [S2] |
| bush-saupe | VZFFF | V->[+++W][---W]YV; W->+X[-W]Z; X->-W[+X]Z; Y->YZ; Z->[-FFF][+FFF]F | 20 | 10 | Bourke "Bushes D" [S2] |
| sticks | X | F->FF; X->F[+X]F[-X]+X | 20 | 7 | Bourke [S2] |
| weed | F | F->FF-[XY]+[XY]; X->+FY; Y->-FX | 22.5 | 5 | Bourke [S2] |
| koch-quadric (unverified) | F-F-F-F | F->F-F+F+FF-F-F+F | 90 | 3 | ABOP Fig 1.7 (unverified) [S1] |

Here the turtle draws on `F` only. `X`/`Y` letters are rewrite-only, which is why Hilbert and Dragon need `F` in the successors.
Bourke also lists two long algae systems (angle 12) and a leaf with length factor 1.36 [S2].

## 4. Strange attractors: equations and known-good parameters

### Continuous (ODE, integrate with RK4, dt ~0.005-0.01)

| Name | Equations | Classic parameters | Source |
|---|---|---|---|
| Lorenz | x'=s(y-x); y'=x(r-z)-y; z'=xy-bz | s=10, r=28, b=8/3 | https://paulbourke.net/fractals/lorenz/ (accessed 2026-11-14) |
| Rossler | x'=-y-z; y'=x+ay; z'=b+z(x-c) | a=0.2, b=0.2, c=5.7 | https://paulbourke.net/fractals/rossler/ (accessed 2026-11-14) |
| Thomas | x'=sin y - bx; y'=sin z - by; z'=sin x - bz | b~0.208186 (onset of chaos); below it the attractor grows through crises | https://en.wikipedia.org/wiki/Thomas%27_cyclically_symmetric_attractor (accessed 2026-11-14) |
| Aizawa | x'=(z-b)x-dy; y'=dx+(z-b)y; z'=c+az-z^3/3-(x^2+y^2)(1+ez)+fzx^3 | a=.95 b=.7 c=.6 d=3.5 e=.25 f=.1 | https://jcponce.github.io/strange-attractors and https://mathworld.wolfram.com/LangfordSystem.html (search, accessed 2026-11-14; a 5-parameter variant without e exists) |

### Discrete maps (iterate, plot points)

| Name | Equations | Parameters | Source |
|---|---|---|---|
| Henon | x'=1-ax^2+y; y'=bx | a=1.4, b=0.3 | https://en.wikipedia.org/wiki/H%C3%A9non_map (accessed 2026-11-14) |
| Ikeda | t=0.4-6/(1+x^2+y^2); x'=1+u(x cos t - y sin t); y'=u(x sin t + y cos t) | u=0.9 (chaotic for u>=0.6) | https://en.wikipedia.org/wiki/Ikeda_map (accessed 2026-11-14) |
| Clifford | x'=sin(a y)+c cos(a x); y'=sin(b x)+d cos(b y) | (-1.4,1.6,1.0,0.7), (1.6,-0.6,-1.2,1.6), (1.7,1.7,0.6,1.2), (1.5,-1.8,1.6,0.9), (-1.7,1.3,-0.1,-1.2), (-1.7,1.8,-1.9,-0.4), (-1.8,-2.0,-0.5,-0.9) | Bourke [S3] |
| Peter de Jong | x'=sin(a y)-cos(b x); y'=sin(c x)-cos(d y) | (1.641,1.902,0.316,1.525), (0.970,-1.899,1.381,-1.506), (1.4,-2.3,2.4,-2.1), (2.01,-2.53,1.61,-0.33), (-2.7,-0.09,-0.86,-2.2), (-0.827,-1.637,1.659,-0.943), (-2.24,0.43,-0.65,-2.43), (-2,-2,-1.2,2), (-0.709,1.638,0.452,1.740) | Bourke [S4] |
| Symmetric icon | z'=(l + a z zbar + b Re(z^n) + i w) z + g zbar^(n-1) | n sets the degree; dihedral D_n when w=0, cyclic Z_n when w!=0; parameter list in Field & Golubitsky, *Symmetry in Chaos* (1992) | https://russellcottrell.com/fractalsEtc/iconGenerator.htm (formula) and https://webbox.lafayette.edu/~reiterc/misc_frac/revisit3_pp.pdf (symmetry), accessed 2026-11-14 |

## 5. Sprott's automatic search

From *Strange Attractors: Creating Patterns in Chaos* (1993, free online) [S5][S6]:
- General 2D quadratic map (Eq. 3B): x' = a1 + a2 x + a3 x^2 + a4 xy + a5 y + a6 y^2,
  y' = a7 + a8 x + a9 x^2 + a10 xy + a11 y + a12 y^2 [S6].
- Coefficients coded by letters A..Y = -1.2..+1.2 in steps of 0.1, so an attractor is a short
  string (first letter names the equation type) [S6]. 25^12 ~ 6x10^16 cases, about 1.6% chaotic [S6].
- Rejection tests during iteration [S6]:
  - unbounded: |x| or |y| exceeds 10^6 -> reject;
  - fixed point: successive iterates differ by < 10^-6 -> reject;
  - Lyapunov: track a neighbour, renormalise its separation to 10^-6 every step, average
    ln(d/d0); require largest exponent > 0;
  - accept as strange attractor if still bounded and LE > 0 after 11,000 iterations.
- Dimension: correlation dimension is displayed, not a hard filter; Sprott notes visually
  appealing 2D attractors tend to have dimension slightly above 1, and suggests rejecting
  dimensions well below 1 or near 2; Chapter 8 returns to aesthetics [S6].
- Sprott's 1993 paper "Automatic generation of strange attractors" (Computers & Graphics 17)
  reports a survey preference for D ~1.1-1.5 and small positive LE (unverified; not fetched).

## 6. Rendering notes

- **Density histogram**: iterate 10^7-10^9 points (skip first ~1000 transient), bin into a
  2D (or 3D) count grid at render resolution x supersample. Map count c with
  `v = log(1+c)/log(1+cmax)`, then gamma (~1/2.2) and a palette; this is the flame-style log
  tone map (see Draves & Reckase "The Fractal Flame Algorithm", unverified here [S9]).
  Colour by iteration velocity or by the last map term for variety.
- **Line drawing**: ODE attractors look best as a polyline (thin, alpha-blended, accumulated
  additively), coloured by time or speed. L-systems: polyline segments, SVG export is natural.
- **3D attractors**: integrate in 3D, project with a camera (orbit for video), or splat
  points into a 3D density volume then raymarch/project; depth fade adds form. Video: rotate
  the camera, or animate a parameter slowly (Clifford/de Jong morph smoothly).
- **Parallelism**: map iteration is serial per orbit; run many orbits from random seeds in
  parallel (numpy vector of points, or GPU) and merge histograms. Points inside the basin
  converge to the same attractor, so this is valid after transient skip.
- L-system 3D: tube/cylinder meshes per segment (export OBJ/glTF for polywright), leaves from
  `{ }` polygons.

## 7. Implications for fractalwright

1. `lsystem` command: YAML preset files as in section 2, built-in presets from section 3,
   `--iterations --angle --seed --svg/--png`, a symbol cap, 2D first, 3D (`& ^ \ /`) second.
2. Stochastic and parametric support is cheap once the rewriter exists; context-sensitive
   needs bracket-aware neighbour search (do last).
3. `attractor` command: a registry of named systems (map or ODE) with default params from
   section 4, plus `--sprott CODE` that decodes Sprott letter strings.
4. `attractor search`: Sprott's tests (bound, fixed point, LE>0, 11k iterations) plus a
   correlation-dimension window (start 1.1-1.6, tunable) and save hits as presets with thumbnails.
5. One shared density-histogram renderer with log tone map, used by attractors and by IFS/flames.
6. Video: parameter interpolation between two good sets, with a check that every frame passes
   the LE test (otherwise the attractor collapses mid-clip).

## 8. Open questions

- Exact figure numbers and angle for ABOP context-sensitive and parametric examples
  (1.31, 1.33, 1.35+) were not read; pages 30-45 of [S1] need a pass.
- Symmetric icon parameter table: need the book or a secondary source with the listed sets.
- Dimension window for "pleasing": confirm from Sprott ch. 8 / 1993 paper.
- Should the GPU path (WebGL explorer) share code with the CLI renderer?

## Sources

- [S1] Prusinkiewicz & Lindenmayer, *The Algorithmic Beauty of Plants*, ch. 1 PDF:
  https://algorithmicbotany.org/papers/abop/abop-ch1.pdf (Fig. 1.24 p.25 and stochastic p.28 read directly). Whole book: https://algorithmicbotany.org/papers/#abop
- [S2] Paul Bourke, L-System User Notes: https://paulbourke.net/fractals/lsys/
- [S3] Paul Bourke, Clifford attractors: https://paulbourke.net/fractals/clifford/
- [S4] Paul Bourke, Peter de Jong attractors: https://paulbourke.net/fractals/peterdejong/
- [S5] J. C. Sprott, *Strange Attractors* book page: https://sprott.physics.wisc.edu/sa.htm
- [S6] Sprott book HTML: https://sprott.physics.wisc.edu/fractals/booktext/sabook.htm (first 100k chars read)
- [S7] Standard literature values for Lorenz, Rossler, Thomas, Aizawa, Henon, Ikeda; not
  re-fetched this session. Verify against e.g. https://paulbourke.net/fractals/ pages.
- [S8] Field & Golubitsky, *Symmetry in Chaos*, Oxford UP 1992 / SIAM 2009 (not fetched).
- [S9] Draves & Reckase, The Fractal Flame Algorithm: https://flam3.com/flame_draves.pdf (not fetched).
