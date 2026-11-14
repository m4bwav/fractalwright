# 03 Deep zoom: precision, perturbation, glitches, renderers

Accessed 2026-11-14. Status markers: **[V]** = checked against the cited page this session;
**[K]** = from long-standing primary sources listed under Sources but not re-fetched this session
(re-verify before quoting in user-facing docs). Zoom depth is given as magnification "1eN",
meaning the view width is about 4/10^N of the full set.

## 1. Where plain precision runs out

The pixel spacing must stay well above the number's resolution at the coordinate's size
(|c| ~ 1-2). With m mantissa bits, the coordinate step is about 2^-m. You need a few spare bits
for iteration error, so the practical limit is roughly 10^-(m*0.301 - 2 or 3).

| Number type | Mantissa bits | Exponent range | Plain-iteration zoom limit | Perturbation delta limit |
|---|---|---|---|---|
| float16 | 11 | 1e-5..6e4 | ~1e2 | useless |
| float32 (WebGL/GLSL default, `highp`) | 24 | ~1e-38 (denormals ~1e-45) | ~1e4-1e5 | ~1e-38: deltas underflow past about 1e35 zoom |
| float64 (NumPy, desktop GLSL `double`, no WebGL) | 53 | ~1e-308 | ~1e13-1e15 | ~1e300 zoom |
| double-float (2 x float32, WebGL emulation) | ~48 | float32 range | ~1e12-1e13 | same exponent wall as float32 |
| double-double (2 x float64) | ~106 | float64 range | ~1e28-1e30 | — |
| quad-double (4 x float64) | ~212 | float64 range | ~1e60 | — |
| long double x87 (80-bit) | 64 | ~1e-4932 | ~1e17 | ~1e4900 zoom (KF uses it) |
| floatexp (float/double mantissa + separate int exponent) | 24 or 53 | effectively unbounded | — | unbounded; deltas only |
| MPFR/GMP (gmpy2, mpmath) | any | any | any (cost grows with digits) | used for reference orbit |

Rules of thumb (K.I. Martin, Heiland-Allen; [K]): reference orbit precision in bits is about
log2(zoom) + 32-64 guard bits, and pixel deltas need only a hardware float **as long as the
exponent does not underflow**. That is why float32 perturbation stops near 1e35-1e38, float64
near 1e300, and floatexp ("extended double") goes on forever. FractalShark uses a custom
"2x32 + exponent" type on CUDA [V].

## 2. Techniques

### 2.1 Arbitrary-precision brute force (reference only)
```
for each pixel: c = mpc(center) + mpc(offset); z = 0
  for n < maxiter: z = z*z + c; if |z|^2 > R^2: break
```
Cost: pixels x iterations x M(digits), M = multiply cost. At 1e100 zoom with mpmath, a 1080p
frame is days. Use only as the **slow ground-truth render** for small crops (e.g. 64x64) in tests.
gmpy2 (MPFR, LGPL) is roughly 10-50x faster than pure-Python mpmath; mpmath (BSD) is the
zero-native-dependency fallback and uses gmpy2 automatically if installed [K].

### 2.2 Perturbation (K.I. Martin, SuperFractalThing, 2013)
Compute one reference orbit Z_n at high precision, round each to hardware floats, then iterate
each pixel's small difference dz with hardware floats:
```
Z[0]=0; for n: Z[n+1] = Z[n]^2 + C          # mpmath/gmpy2, stored as float64 (or floatexp)
dc = pixel - C  (hardware float / floatexp)
dz = 0
for n: dz = 2*Z[n]*dz + dz*dz + dc
       z = Z[n+1] + dz ; if |z|^2 > R^2: escape at n
```
Cost: one reference orbit O(maxiter x M(digits)) + pixels x iterations x O(1) hardware ops.
This is what makes 1e1000 zooms practical. The pixel loop is a plain float loop that fits a
GLSL fragment shader or a NumPy vectorised loop.

### 2.3 Rebasing (Zhuoran, 2021)
Replaces most glitch detection. When |z| < |dz| (the pixel's full orbit gets closer to 0 than
its offset), or when the reference orbit ends, restart the pixel against the **same reference
from iteration 0**:
```
if |Z[m] + dz|^2 < |dz|^2 or m == refLen-1:
    dz = Z[m] + dz ; m = 0
```
Cost: a compare per iteration. Effect: one reference suffices for almost all images; glitches
from "reference escaped early" also go away. Source: Zhuoran's fractalforums.org thread
"Another solution to perturbation glitches" and Heiland-Allen's write-up [K].

### 2.4 Glitch detection (Pauldelbrot criterion, 2014)
Before rebasing, renderers detected pixels whose dz lost precision:
```
if |Z[n] + dz|^2 < tol * |Z[n]|^2:  mark glitched   # tol ~ 1e-6 (KF default 1e-3..1e-6 range)
```
Glitched pixels form flat "blobs" of uniform colour. They are re-rendered with a new reference
placed inside the blob (usually the blob's centre or the pixel with the lowest iteration), and
repeated until no glitches remain. Cost: compare per iteration + extra reference orbits.
Still useful **as a test**, even with rebasing on.

### 2.5 Series approximation (SA, Martin 2013)
Skip the first N iterations for all pixels at once by expressing dz_n as a polynomial in dc:
```
dz_n ~= A_n dc + B_n dc^2 + C_n dc^3 + ...
A_{n+1} = 2 Z_n A_n + 1 ; B_{n+1} = 2 Z_n B_n + A_n^2 ; C_{n+1} = 2 Z_n C_n + 2 A_n B_n ...
stop at N when higher terms exceed tolerance for the image's corner pixels
```
Cost: O(N x terms^2) once per frame. Can skip millions of iterations near minibrots. Failure
mode: skipping too far gives wrong images without blob signs; the stop test is heuristic.
Largely superseded by BLA.

### 2.6 Bilinear approximation (BLA, Zhuoran 2021; Heiland-Allen's write-up)
Per-iteration linear maps dz -> A dz + B dc, valid while |dz| is under a radius r_n. Merge
adjacent steps into a binary tree so a pixel can jump 2^k iterations at once:
```
single step n: A = 2 Z_n, B = 1, r = eps * |Z_n| (roughly)
merge (x then y): A = Ay*Ax, B = Ay*Bx + By, r = min(rx, max(0, (ry - |Bx|*|dc_max|) / |Ax|))
per pixel: at iteration m, find the largest tree node starting at m with |dz| < r; apply; else
           do one ordinary perturbation step; rebase as 2.3
```
Cost: O(refLen) memory and build time per frame; per-pixel cost drops from O(iterations) to
roughly O(log iterations) inside long periodic stretches. Works with rebasing, unlike SA.
KF 2.15+, Fraktaler 3, Imagina and FractalShark (ported from FractalZoomer) use it [V for FS].

### 2.7 Reference orbit selection
- Image centre: the default; fine with rebasing.
- Nucleus of the nearest minibrot (period found by "ball period" / Newton): the orbit is
  periodic, so it never escapes and only one period need be stored. Imagina syncs approximation
  steps with minibrot periods [V via Wikibooks summary].
- Glitch-blob centres: extra references for the old (non-rebasing) method.

### 2.8 Floatexp / extended range
Store (mantissa float, int exponent) and renormalise after each op. 3-10x slower than native
floats, so renderers switch: float32 -> float64 -> long double -> floatexp as zoom passes
each type's exponent wall [K, KF manual]. In GLSL: vec2(mantissa, exponent) or a float + int.

### 2.9 Double-double / double-float in shaders
Dekker/Knuth two-sum and two-product, with FMA if available:
```
two_sum(a,b): s=a+b; v=s-a; e=(a-(s-v))+(b-v); return (s,e)
two_prod(a,b): p=a*b; e=fma(a,b,-p)    # no fma in WebGL1/2: Dekker split, 6 extra muls
```
Pitfall: GPU drivers may fuse or reorder and break the error terms; known WebGL ports
add `* uOne` style tricks to stop the optimiser [K]. Gives ~1e12 zoom in WebGL without
perturbation. Perturbation in float32 plus a CPU reference reaches ~1e30+ and is simpler.

## 3. Glitch tests usable as a proof bar

1. **Reference crop test.** Render a 64x64 crop of the deep frame with 2.1 (mpmath/gmpy2,
   precision = log2(zoom)+64 bits). Compare iteration counts per pixel to the fast render.
   Pass: >= 99.9% of pixels within +/-1 iteration (smooth-coloured value within 1%), and no
   connected group of >= 4 mismatched pixels.
2. **Blob test.** Flat-colour connected regions not present in a reference render: label
   regions of identical iteration count with size > 0.5% of image and no matching region in a
   2x-downsampled reference. Pass: zero.
3. **Pauldelbrot counter.** Run the 2.4 check in instrumented mode with rebasing off; record
   glitched-pixel count. With rebasing on, count of pixels that reached maxiter while the
   reference says they escape must be 0.
4. **Shift test.** Render the same frame with the reference moved to a different pixel (or a
   minibrot nucleus). Images must agree within test 1 tolerance; disagreement means a
   reference-dependent glitch.
5. **Zoom-video continuity.** Mean absolute difference between consecutive frames, after
   rescaling, must not spike more than 3x the median (catches precision-switch seams between
   float32/float64/floatexp segments).

Known test locations: use coordinates from the KF / Fraktaler 3 example sets and FractalShark's
built-in views (deepest ~1e650452) [V]; fix a handful (1e10, 1e50, 1e300, 1e1000) in the
plugin's test suite once licences of the coordinate files are checked (coordinates are facts,
low risk).

## 4. What fits where

| Path | Plain limit | With perturbation | Reference orbit | Notes |
|---|---|---|---|---|
| WebGL2 fragment shader, float32 | ~1e5 | ~1e35 (float32 exponent); beyond with vec2 floatexp | computed in JS (BigInt fixed-point or a WASM MPFR) or in Python and shipped as a float texture | no `double`; rebasing is a few lines; BLA needs a tree texture, doable |
| WebGL2 double-float emulation | ~1e12 | not needed with perturbation | — | slow (~10x), fragile on drivers |
| WebGPU (WGSL) | f32 only (f64 not in core spec [K]) | same as WebGL; compute shaders make BLA lookup easier | as above | headless needs Chrome flags |
| Desktop headless GLSL (moderngl/EGL) | double via GL_ARB_gpu_shader_fp64 ~1e14 | ~1e300 with double deltas | Python | fp64 is slow on consumer GPUs (1/32-1/64 rate) |
| NumPy float64 vectorised | ~1e14 | ~1e300; unbounded with floatexp arrays (mantissa + int64 exp) | Python | per-iteration Python overhead: mask out escaped pixels; Numba (optional) gives 10-50x |
| Python mpmath / gmpy2 | any | — | yes: 1e1000 x 1e6 iterations is minutes with gmpy2, much longer with mpmath | the reference orbit is the only high-precision work |

## 5. Renderer survey

| Renderer | Author | Techniques | Platform | Licence |
|---|---|---|---|---|
| SuperFractalThing | K.I. Martin (2013) | origin of perturbation + SA | Java | released as open source by its author; licence text not re-checked [K] |
| Kalles Fraktaler 2 / 2+ | Karl Runmo (2012-2017), fork by Claude Heiland-Allen | perturbation, SA, Pauldelbrot glitches, later rebasing + BLA, floatexp, OpenCL | Windows (Wine) | AGPL-3.0-or-later (fork) [V, Wikipedia mirror] |
| Fraktaler 3 | Claude Heiland-Allen | perturbation, rebasing, BLA, multiple number types, EXR export compatible with KF2+ | Linux, Windows, Android, Web | AGPL-3.0 per mathr releases (unverified after check: code.mathr.co.uk returned 403) |
| Imagina | Zhuoran | rebasing + BLA (its inventor), period-synchronised approximation, successive refinement | Windows | AGPL-3.0 per `gh api repos/5E-324/Imagina` (accessed 2026-11-14; repo owner assumed to be Zhuoran) |
| Mandel Machine | Botond Kosa | perturbation, SA, Java/SIMD | Java | freeware, closed source [K] |
| FractalShark | Matt Renzelmann (mattsaccount364) | perturbation, BLA ported from FractalZoomer, GPU reference orbit with NTT multiply, MPIR/GMP | Windows/Linux, CUDA RTX 2xxx+ | GPL-3.0 [V] |
| FractalZoomer | hrkalona | perturbation, SA, BLA, many formulas | Java | GPL-3.0 (checked https://github.com/hrkalona/Fractal-Zoomer 2026-11-14) |
| GAPFixFractal | bernds | arbitrary precision on CUDA | CUDA | GPL-3.0-or-later [V] |
| Deep-zoom WebGL explorers (e.g. mandelbrot perturbation shaders on Shadertoy/GitHub) | various | float32 perturbation, sometimes floatexp + rebasing | browser | mixed (Shadertoy default CC BY-NC-SA 3.0); do not copy code without checking |

Licence implication: KF2+ and Fraktaler 3 are AGPL, FractalShark GPL. fractalwright must not
copy their code if it is to stay permissively licensed; reimplement from the published maths
(blog posts, forum threads, papers), which are ideas, not code.

## 6. Implications for fractalwright

Recommended path:
1. **Reference orbit in Python**, mpmath required-light (pure Python, BSD), gmpy2 optional for
   speed. Store orbit as float64 (or mantissa + exponent pairs past 1e300). Small install.
2. **Pixel loop: perturbation + rebasing**, implemented twice from one spec:
   NumPy float64 (CPU, always available) and WebGL2 float32 (browser explorer / headless video).
3. **BLA** as phase 2 for high-iteration locations; SA skipped (BLA supersedes it).
4. **Floatexp** as phase 3: NumPy (mantissa array + int exponent array) and GLSL vec2.
5. Glitch tests 1-4 in CI on 64x64 crops; test 5 for zoom videos.

Depth limits per path (target, after each phase):
| Path | Phase 1 (perturbation + rebasing) | Phase 3 (floatexp) |
|---|---|---|
| NumPy float64 | ~1e300 | unbounded (practical: reference-orbit cost, ~1e10000) |
| WebGL2 float32 | ~1e30-1e35 | unbounded, ~3-5x slower per iteration |
| Plain (no perturbation) | NumPy ~1e13, WebGL ~1e4 | — |

Zoom videos: render keyframes at doubling zoom (exponential map / "zoom out sequence" like
KF + zoomasm) and interpolate; one reference orbit per keyframe (or one orbit at the final
centre serves every frame, since all frames share a centre).

## 7. Open questions
- Imagina and Fraktaler 3 licences: fetch repo LICENSE files directly.
- BigInt fixed-point reference orbit in plain JS for a browser-only explorer: speed at 1e1000?
- Is f64 (`shader-f64`) a WebGPU extension anywhere usable by 2026? (believed absent from core)
- Numba as an optional extra: worth the ~100 MB? (Probably yes as opt-in.)
- Which non-Mandelbrot formulas (Burning Ship, Mandelbar, higher powers) need their own
  perturbation formulas (Burning Ship needs the "diffabs" trick) and BLA coefficients.
- Owner decision: does a permissive licence matter (rules out vendoring AGPL/GPL code)?

## Sources (accessed 2026-11-14)
- FractalShark README, licence and techniques: https://github.com/mattsaccount364/FractalShark [V]
- Kalles Fraktaler overview, AGPL fork, BLA in later versions: https://mrob.com/pub/muency/kallesfraktaler.html ; https://www.wikiwand.com/en/Kalles_Fraktaler [V]
- Fraktaler 3 summary: https://en.wikibooks.org/wiki/Fractals/fraktaler-3 [V]
- Fractal software list (Imagina notes): https://en.wikibooks.org/wiki/Fractals/software [V]
- GAPFixFractal licence: https://github.com/bernds/GAPFixFractal [V]
- K.I. Martin, "Superfractalthing Maths" (perturbation + SA): http://www.superfractalthing.co.nf/sft_maths.pdf [K]
- Claude Heiland-Allen blog (perturbation, rebasing, BLA, KF/Fraktaler 3 releases): https://mathr.co.uk/blog/ ; code: https://code.mathr.co.uk/ [K]
- Zhuoran, "Another solution to perturbation glitches" (rebasing, BLA): https://fractalforums.org/fractal-mathematics-and-new-theories/28/another-solution-to-perturbation-glitches/4360 [K]
- Pauldelbrot glitch criterion thread: https://www.fractalforums.com/announcements-and-news/pertubation-theory-glitches-improvement/ [K]
- Kalles Fraktaler 2+ manual (number types, thresholds): https://mathr.co.uk/kf/manual.html [K]
- Wikibooks perturbation page: https://en.wikibooks.org/wiki/Fractals/Iterations_in_the_complex_plane/perturbation_theory [K]
