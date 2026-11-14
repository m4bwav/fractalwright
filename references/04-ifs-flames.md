# 04 - Iterated function systems and fractal flames

Research note for fractalwright. Accessed 2026-11-14 unless marked. Claims marked
(KNOWN) come from the researcher's background knowledge of the Draves and Reckase
paper and flam3. The paper PDF (https://flam3.com/flame_draves.pdf) was too large
for the fetch tool (over 10 MB), so check those claims against it before shipping.

## 1. IFS basics

An IFS is a finite set of contraction maps f_1..f_N on the plane. Its attractor A
is the unique non-empty compact set with A = f_1(A) U ... U f_N(A) (Hutchinson 1981).
(KNOWN)

### Deterministic IFS
Start from any compact set S_0, for example a square. Then S_{k+1} = U f_i(S_k).
The cost grows as N^k, so it suits a few iterations of polygon sets, or the
Sierpinski and Koch construction diagrams.

### Chaos game (random iteration)
```
p = random point
repeat ITER times:
    i = pick index with probability p_i
    p = f_i(p)
    if iter > 20: plot(p)        # skip the transient while p falls onto the attractor
```
Probabilities only change the density, not the attractor. For uniform density,
weight each map by |det| of its linear part. (KNOWN)

### Barnsley fern
Each map is f(x,y) = (a x + b y + e, c x + d y + f). Coefficients from
https://en.wikipedia.org/wiki/Barnsley_fern (Wikipedia names the last column g):

| map | a | b | c | d | e | f | p |
|---|---|---|---|---|---|---|---|
| f1 stem | 0 | 0 | 0 | 0.16 | 0 | 0 | 0.01 |
| f2 successive leaflets | 0.85 | 0.04 | -0.04 | 0.85 | 0 | 1.60 | 0.85 |
| f3 left leaflet | 0.20 | -0.26 | 0.23 | 0.22 | 0 | 1.60 | 0.07 |
| f4 right leaflet | -0.15 | 0.28 | 0.26 | 0.24 | 0 | 0.44 | 0.07 |

Range is about x in [-2.18, 2.66] and y in [0, 9.99]. (KNOWN; check before use)

### Collage theorem (Barnsley 1985)
If the union of the f_i(T) lies within Hausdorff distance eps of a target set T,
and every f_i has contraction factor at most s < 1, then
d_H(T, A) <= eps / (1 - s). Practical use: an "IFS from a silhouette" tool
covers the shape with shrunken affine copies of itself and scores the overlap.
(coefficients checked: https://en.wikipedia.org/wiki/Barnsley_fern , accessed 2026-11-14; source M. Barnsley, *Fractals Everywhere*, 1988)

### Classic sets as IFS (similarity dimension: N r^D = 1, so D = log N / log(1/r))
- Sierpinski triangle: 3 maps, f_i(p) = (p + v_i)/2. D = log 3 / log 2, about 1.585.
- Koch curve: 4 maps with ratio 1/3, two of them rotated by +60 and -60 degrees.
  D = log 4 / log 3, about 1.262.
- Sierpinski carpet: 8 maps with ratio 1/3, D = log 8 / log 3. Menger sponge
  (3-D): 20 maps, D = log 20 / log 3.
- Exact sources: Hutchinson, "Fractals and self-similarity", Indiana Univ. Math.
  J. 30 (1981); Mandelbrot, *The Fractal Geometry of Nature* (1982). The open-set
  condition makes the similarity dimension equal the Hausdorff dimension. (KNOWN)

## 2. The fractal flame algorithm (Draves and Reckase, 2003/2008)

Paper: S. Draves and E. Reckase, "The Fractal Flame Algorithm",
https://flam3.com/flame_draves.pdf. Summary of the formulas:
https://en.wikipedia.org/wiki/Fractal_flame.

### Transform ("xform")
F_j(x,y) = sum_k w_jk * V_k(a_j x + b_j y + c_j, d_j x + e_j y + f_j)
Each xform has an affine pre-transform, weighted variations, an optional affine
**post transform** P_j applied after the variation sum, a selection weight, and a
colour index c_j in [0,1]. Draves suggests weights that sum to 1. Apophysis does
not enforce this. (Wikipedia)

### Final transform
One optional extra xform F_final, applied to every point *for plotting only*.
It is not fed back into the iteration. It is used for camera-like warps such as
a spherical lens. (KNOWN; paper section 3)

### Chaos game with colour
```
(x,y) = random in [-1,1]^2 ; c = random in [0,1]
for i in 0..N:
    j = pick xform by weight (flam3 >= 2.8 can use a per-xform "chaos" / xaos matrix)
    (x,y) = post_j( sum_k w_jk V_k( affine_j(x,y) ) )
    c = (c + c_j) / 2               # paper; flam3 uses c = c*(1-s_j) + c_j*s_j, s_j = color_speed
    if i >= 20:
        (fx,fy), fc = final(x,y,c) if final else (x,y,c)
        px = camera(fx,fy)          # centre, scale, rotate, supersample factor
        if in bounds: hist[px].rgb += palette(fc); hist[px].count += 1
```
The Wikipedia version of the colour blend is (P.c + c_j)/2. The flam3
`color_speed` generalisation is (KNOWN). Bad points (NaN, inf, huge values) are
re-seeded at random, and flam3 counts them as "badvals". (KNOWN)

### Variations to ship first (paper numbering; r = sqrt(x^2+y^2), theta = atan2(x,y), phi = atan2(y,x))
| # | name | V(x,y) |
|---|---|---|
| 0 | linear | (x, y) |
| 1 | sinusoidal | (sin x, sin y) |
| 2 | spherical | (x, y) / r^2 |
| 3 | swirl | (x sin r^2 - y cos r^2, x cos r^2 + y sin r^2) |
| 4 | horseshoe | ((x-y)(x+y), 2xy) / r |
| 5 | polar | (theta/pi, r - 1) |
| 6 | handkerchief | r (sin(theta+r), cos(theta-r)) |
| 7 | heart | r (sin(theta r), -cos(theta r)) |
| 8 | disc | (theta/pi)(sin(pi r), cos(pi r)) |
| 9 | spiral | (1/r)(cos theta + sin r, sin theta - cos r) |
| 10 | hyperbolic | (sin theta / r, r cos theta) |
| 11 | diamond | (sin theta cos r, cos theta sin r) |
| 12 | ex | r(p0^3 + p1^3, p0^3 - p1^3), p0 = sin(theta+r), p1 = cos(theta-r) |
| 13 | julia | sqrt(r)(cos(theta/2 + Omega), sin(theta/2 + Omega)), Omega random in {0, pi} |
| 14 | bent | piecewise: x<0 gives 2x; y<0 gives y/2 |
| 16 | fisheye | (2/(r+1)) (y, x) |
| 18 | exponential | e^(x-1) (cos(pi y), sin(pi y)) |
| 27 | eyefish | (2/(r+1)) (x, y) |
| 28 | bubble | (4/(r^2+4)) (x, y) |
| 29 | cylinder | (sin x, y) |
| 32 | julian (param.) | power/dist Julia generalisation |
| 34 | blur | random point in the unit disc |
| 35 | gaussian_blur | Gaussian random offset |

Rows 0-13 checked against flam3 var0_linear..var13_julia (https://github.com/scottdraves/flam3/blob/master/variations.c, accessed 2026-11-14); flam3's precalc_atan is atan2(x, y), so theta follows the paper's convention.
The full paper list runs from 0 to 48 (KNOWN). flam3 3.1.1 has 99 variations,
and JWildfire has several hundred, mostly as plugins (KNOWN; count them in
flam3's `variations.c` / `flam3.h`). Ship 0 to 14, 16, 18, 27 to 29, 34 and
julian/juliascope first. These cover most classic sheep. Random variations
(julia, blur) need a per-thread RNG.

### Rendering: histogram, then tone map
1. **Supersampling**: the histogram is ss x ss times the output resolution, and
   each output pixel averages an ss x ss block. (Wikipedia; flam3 `supersample`)
2. **Log-density**: alpha = log(freq) / log(freq_max) in the paper/Wikipedia
   form. flam3 actually scales each cell by
   ls = k1 * log(1 + count*k2)/count, with k1 = contrast*brightness*PREFILTER_WHITE*268/256
   and k2 = oversample^2*nbatches/(contrast*area*WHITE_LEVEL*sample_density*sumfilt),
   so it maps colour sums rather than a ratio to a maximum. (Wikipedia; flam3 https://github.com/scottdraves/flam3/blob/master/rect.c, accessed 2026-11-14)
3. **Gamma**: final = color_avg * alpha^(1/gamma), gamma > 1. Gamma per channel
   looks better but costs more. (Wikipedia) flam3 has `gamma_threshold`, which
   makes the curve linear below a threshold to cut noise (`gam_lin_thresh` passed to flam3_calc_alpha; https://github.com/scottdraves/flam3/blob/master/rect.c, accessed 2026-11-14).
4. **Vibrancy** v in [0,1]: blend of alpha-based gamma (applied to all channels
   together, which keeps saturation) and per-channel gamma:
   out = v * (alpha^(1/gamma) * rgb/alpha) + (1-v) * (per-channel rgb^(1/gamma)).
   (flam3 https://github.com/scottdraves/flam3/blob/master/rect.c, accessed 2026-11-14: ls = vibrancy*256*alpha/tmp plus (1-vibrancy)*256*pow(rgb/PREFILTER_WHITE, 1/gamma)). `highlight_power` is passed to flam3_calc_newrgb, whose body was not read: unverified after check (function body not in rect.c).
5. **Density estimation filter**: an adaptive blur whose kernel width shrinks as
   the hit count grows, based on Suykens and Willems 2000. Sparse areas blur and
   dense areas stay sharp. In flam3 the width is
   w = estimator_radius / count^estimator_curve, clamped to estimator_minimum.
   (Wikipedia for the idea; flam3 parameter names KNOWN)
6. Spatial filter (Gaussian, `filter` radius) at the end, then background
   compositing. Motion blur for animation uses `temporal_samples`. (KNOWN)

Quality knob: `quality` = samples per output pixel (a sheet render is about
100 to 1000+). Total iterations = quality * width * height. (KNOWN)

## 3. .flame / .flam3 file format
XML. A `<flames>` root holds one or more `<flame>` elements. Attributes (KNOWN,
from flam3 output and Apophysis files):
```xml
<flame name="x" version="Apophysis 2.09" size="1920 1080" center="0 0" scale="240"
       rotate="0" oversample="1" filter="0.5" quality="50" background="0 0 0"
       brightness="4" gamma="4" gamma_threshold="0.01" vibrancy="1"
       estimator_radius="9" estimator_minimum="0" estimator_curve="0.4">
  <xform weight="0.5" color="0" color_speed="0.5" linear="1" julia="0.3"
         coefs="a d b e c f" post="1 0 0 1 0 0" chaos="1 1 0"/>
  <finalxform color="0" linear="1" coefs="1 0 0 1 0 0"/>
  <palette count="256" format="RGB">hex...</palette>   <!-- or <color index= rgb=> rows -->
</flame>
```
- `coefs` order is column-major (a d b e c f in Wikipedia lettering). Apophysis
  also flips the y axis. This is the usual source of import bugs. (KNOWN)
- Variation parameters are attributes named `<var>_<param>`, for example
  `julian_power`. (KNOWN)
- `flam3-convert` turns the old GIMP format into XML. The repo ships
  `flam3-palettes.xml`, the 701 standard palettes. (https://github.com/scottdraves/flam3)
- Chaotica uses its own `.chaos` format and imports .flame. JWildfire reads and
  writes .flame and adds its own attributes. Fractorium reads and writes .flame
  and adds its own extensions. (KNOWN; the Chaotica site does not document formats)

## 4. Tool survey
| tool | what | licence | formats |
|---|---|---|---|
| flam3 (Draves) | the original CLI renderer + genome tool (flam3-render, -animate, -genome) | GPL-3.0 (repo sidebar, COPYING); last changelog entry 3.1.1, 2015-05-17 | .flam3/.flame XML; PNG/JPG/PPM out. https://github.com/scottdraves/flam3 |
| Electric Sheep | distributed screensaver; each "sheep" is a flame genome evolved by votes and rendered by clients | client GPL (https://en.wikipedia.org/wiki/Electric_Sheep) | genomes as flam3 XML |
| Apophysis 2 / 7X | Windows flame editor (Delphi); 7X is the community fork with 3-D and plugins | Apophysis listed as GPL (https://Www.Wikipedia.org/wiki/Fractal-generating_software); 7X licence GPL-3.0 per `gh api repos/xyrus02/apophysis-7x` (accessed 2026-11-14); was **unconfirmed** | .flame, plugin DLLs |
| JWildfire | Java editor with hundreds of variations, scripting, animation and a GPU renderer (FACLRender, CUDA) | LGPL-2.1-or-later (checked: README of https://github.com/thargor6/JWildfire , accessed 2026-11-14) per https://www.linuxlinks.com/jwildfire-user-friendly-fractal-flame-editor (check the repo) | .flame, .jwfscript |
| Fractorium | Qt editor + Ember renderer, OpenCL GPU path | GPL-3.0 (https://www.linuxlinks.com/fractorium-qt-based-fractal-flame-editor/; mirror https://git.speice.io/mirror-github-bspeice/fractorium) | .flame (+ extensions) |
| Chaotica | commercial renderer and editor by Glare Technologies, fast and high quality; HD and Studio editions, a limited free version | proprietary (https://www.chaoticafractals.com/, https://Www.wikipedia.org/wiki/Chaotica_(software)) | .chaos; imports .flame |

### Redistributing sheep and presets
https://electricsheep.org/license/ (via search result summary): **algorithm-made
sheep are CC Attribution-NonCommercial** (with a lineage). **Human-designed
sheep are CC Attribution** (credit the designer). Commercial use or use without
attribution needs a bought licence. One third-party repo bundles genomes as
CC BY 2.5. The exact CC version was not confirmed. Conclusion: do **not** bundle
sheep genomes in a plugin that may be used commercially. Generate our own
presets, or bundle only CC BY human sheep with credit after checking each one.
The flam3 palettes file is part of a GPL repo, so the licence of that data is
unclear. Bundling it may pull GPL obligations into the plugin.

## 5. GPU rendering options
- **Point splatting (WebGL2)**: a transform-feedback or ping-pong texture keeps
  M parallel chaos-game walkers (about 1e5 to 1e6). Each step runs the
  xform in a shader. Points are drawn as GL_POINTS with additive blending
  into an RGBA32F (or half-float) accumulation target (EXT_color_buffer_float).
  A full-screen pass then does log-density, gamma and vibrancy. No atomics are
  needed. (KNOWN)
- **WebGPU compute**: each invocation runs K iterations for one walker and does
  atomicAdd into u32 storage buffers (count + fixed-point RGB). Atomics are
  integer-only, so scale colour to fixed point. Density estimation and tone
  mapping run as later compute passes. This works in a browser or headless
  (Chrome/Dawn, wgpu). (KNOWN)
- **CUDA/OpenCL natives**: Fractorium (OpenCL, Ember) and JWildfire's FACLRender
  show the same design: many walkers, a random xform per step, atomic
  histogram, then CPU or GPU filtering. (KNOWN)
- **Caveats**: walkers need a burn-in (about 20 iterations) and per-walker RNG
  (PCG/xorshift). float32 precision drifts at deep zooms. Branchy variation
  switches diverge on the GPU, so it can help to sort or specialise shaders per
  genome (generate WGSL/GLSL from the genome).
- **NumPy**: vectorise over walkers ((M,2) arrays, one xform per step chosen by
  a mask) and use np.add.at or bincount on flat indices. Feasible for stills at
  1e8 to 1e9 samples. Numba helps a lot. (KNOWN)

## 6. Implications for fractalwright
1. Use one genome model (our JSON) with .flame import and export. Getting the
   coefs order and y-flip right is the main compatibility task. Write tests that
   round-trip Apophysis files.
2. Ship about 25 core variations (listed in section 2) plus final and post
   transforms, the xaos matrix, color_speed and palettes.
3. The renderer has two stages: (a) a histogram from a NumPy/Numba walker or a
   WebGPU compute walker, then (b) a shared tone mapper (log-density, gamma,
   gamma_threshold, vibrancy, DE filter, supersample). Stage (b) can be the same
   code in Python and WGSL, so stills and the explorer match.
4. The interactive explorer uses WebGL2 splatting (wide support), with a WebGPU
   path when available. Progressive accumulation while idle gives a preview
   that refines.
5. Animation: interpolate genomes (affine coefficients by polar decomposition
   to avoid shear) and use temporal_samples motion blur. Electric Sheep style
   loops rotate the affine of each xform through 360 degrees. (KNOWN)
6. Classic IFS (fern, Sierpinski, Koch, carpet, Dragon) are just flames with
   only the linear variation. One engine covers both.
7. Presets: make our own with a random-genome generator plus a filter for
   coverage and entropy. Do not ship sheep genomes or the flam3 palettes until
   the licences are cleared.

## 7. Open questions
- Exact Apophysis 7X and JWildfire licences (read their repo LICENSE files).
- Is flam3-palettes.xml data GPL, and can we ship it?
- Exact current CC version and NC scope on electricsheep.org/license.
- Check the variation formulas and the vibrancy and k1/k2 equations against the
  PDF (download it locally and read it with readwright or pdftotext).
- Chaotica free version limits, and whether .chaos is documented.
- WebGPU atomics throughput vs. WebGL2 additive blend on Mark's GPU (benchmark).

## 8. Sources (accessed 2026-11-14)
- https://flam3.com/flame_draves.pdf (fetch failed, too large; cited for structure)
- https://en.wikipedia.org/wiki/Fractal_flame
- https://en.wikipedia.org/wiki/Barnsley_fern
- https://github.com/scottdraves/flam3
- https://electricsheep.org/license/
- https://en.wikipedia.org/wiki/Electric_Sheep
- https://www.chaoticafractals.com/
- https://Www.wikipedia.org/wiki/Chaotica_(software)
- https://Www.Wikipedia.org/wiki/Fractal-generating_software
- https://www.linuxlinks.com/jwildfire-user-friendly-fractal-flame-editor
- https://www.linuxlinks.com/fractorium-qt-based-fractal-flame-editor/
- https://git.speice.io/mirror-github-bspeice/fractorium
