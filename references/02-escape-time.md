# 02 Escape-time families and colouring

Research note for fractalwright. Accessed 2026-11-14. Every claim carries a source; the numbered list at the end holds the full URLs.
Effort note: this pass was quick. Only the Mandelbrot area figure was re-checked live this session [S1][S2]. The rest is cited from well-known primary pages and should be spot-checked before any test is pinned to it (see Open questions).

## Shared escape-time loop

```
z = z0(pixel); c = c0(pixel); n = 0
while n < max_iter and |z|^2 <= R^2:
    z = f(z, c); n += 1
escaped = n < max_iter
```

- For quadratic maps, once |z| > 2 the orbit is guaranteed to diverge, so R = 2 is the minimum correct bailout [S3]. Smooth colouring needs a large R (2^8 or more; IQ uses 256 or more) so that the log-log correction is accurate [S4][S5].
- Interior checks save a lot of time on Mandelbrot views: the main cardioid test q = (x-1/4)^2 + y^2, q(q + (x-1/4)) <= y^2/4, and the period-2 bulb test (x+1)^2 + y^2 <= 1/16 [S3]. Periodicity checking (Brent-style cycle detection on z) is a second option [S3].
- Float32 (WebGL) runs out of precision at about scale 1e-5 to 1e-6 per pixel. Float64 (NumPy, and WebGPU only through emulation) lasts to about 1e-13 to 1e-14. Deeper zooms need perturbation theory with series approximation, as in Kalles Fraktaler [S6][S7].

## Families

### Mandelbrot
- Formula: z_{n+1} = z_n^2 + c, z_0 = 0, c = pixel [S3].
- Parameters: max_iter, bailout. Bailout 2, or a larger one for smooth colouring.
- Look: a cardioid plus a period-2 disc, bulbs studded along the boundary, filaments, and minibrots. Symmetric about the real axis [S3].
- Default view: centre (-0.75, 0), width 3.5 (x from -2.5 to 1) [S3]. Seahorse valley is about (-0.745, 0.1) at width 0.01 or less [S3].
- Identify tell: cardioid with a circle to its left, mirror symmetry about the horizontal axis, and the spike on the negative real axis ending at -2.
- Known numbers: area ≈ 1.5065918849 ± 2.8e-9 by pixel counting (Förstemann 2012) [S1][S2]. Hausdorff dimension of the boundary = 2 (Shishikura) [S3]. The set lies inside the disc |c| <= 2, and its real-axis extent is [-2, 0.25] [S3].

### Julia (filled Julia sets)
- Formula: z_{n+1} = z_n^2 + c with c fixed and z_0 = pixel [S8].
- Parameters: c (complex), max_iter, bailout = max(2, |c|) [S8].
- Look: connected if c is in M, Cantor dust if not (Fatou-Julia dichotomy). 180-degree rotational symmetry [S8].
- Default view: centre (0, 0), width 3.2 to 4. Presets: c = -0.8+0.156i, c = -0.4+0.6i, c = 0.285+0.01i, c = -0.7269+0.1889i (all listed on the Wikipedia Julia page) [S8]. Douady rabbit c ≈ -0.1226+0.7449i; dendrite c = i; San Marco c = -0.75 [S8].
- Identify tell: point symmetry through the centre with no cardioid. The shape repeats along its own boundary.

### Multibrot
- Formula: z ← z^d + c with real d (integers usually) [S9].
- Parameters: d, max_iter, bailout. Smooth colouring divides by log d, not log 2 [S4].
- Look: (d-1)-fold rotational symmetry with d-1 lobes; d=3 has two lobes [S9]. Negative d gives "multicorn-like" inverted shapes [S9].
- Default view: centre (0, 0), width 3 for d >= 3.
- Tell: (d-1)-fold symmetric main body, still with Mandelbrot-like bulbs and filaments.

### Burning Ship
- Formula: z ← (|Re z| + i|Im z|)^2 + c, z_0 = 0 [S10]. Original paper: Michelitsch and Rössler 1992 [S10].
- Conventionally drawn with the imaginary axis flipped so the "ship" sits upright [S10].
- Default view: whole set centre (-0.5, -0.5) width 3.5. The ship itself is near (-1.762, -0.028) at width about 0.08 (imaginary axis flipped) [S10].
- Tell: hard, angular, flame-like spires along the negative real axis. Not symmetric about the real axis.

### Tricorn / Mandelbar
- Formula: z ← conj(z)^2 + c [S11]. It is anti-holomorphic, so the ordinary DE derivation differs; the derivative chain uses conjugates [S11].
- Look: three-fold symmetric "tricorn" with discontinuous-looking hyperbolic components and wiggly boundaries along the real-axis component edges [S11].
- Default view: centre (-0.3, 0), width 4.
- Tell: three-cornered body with 3-fold symmetry, bulbs that look "smeared", and no cardioid.

### Newton (and Nova)
- Newton: z ← z - a·p(z)/p'(z) on a polynomial p, z_0 = pixel; colour by the root reached (basin), shade by iteration count [S12]. Classic p(z) = z^3 - 1, roots at the cube roots of unity [S12].
- Bailout is a convergence test, not escape: stop when |z_{n+1} - z_n| < eps (e.g. 1e-6) [S12].
- Nova: z ← z - a·p(z)/p'(z) + c, with c = pixel (Mandelbrot-like, z_0 = a critical point, e.g. 1 for z^3-1) or c fixed (Julia-like). Nova Mandelbrot sets contain miniature Mandelbrot copies [S13].
- Parameters: polynomial (roots or coefficients), relaxation a (complex; a ≠ 1 gives "relaxed Newton"), eps, max_iter.
- Default view: centre (0, 0), width 4, for z^3-1.
- Tell: n coloured basins meeting at fractal boundaries, where every boundary point touches all basins (Wada property) [S12]. Flat regions, no escape filaments.

### Lyapunov
- Logistic map x ← r x (1-x), with r switching between a and b according to a periodic sequence such as "AB" or "AABAB". The pixel is (a, b) [S14].
- Exponent λ = (1/N) Σ log|r_n (1 - 2 x_n)| after a warm-up [S14]. Units: with the natural log λ is in nats per iteration; divide by ln 2 for bits. Always print the unit (`fw.py` reports bits) [book rule: Feldman, *Chaos and Fractals*, ch. 10]. λ < 0 is stable (one colour ramp, often yellow) and λ > 0 is chaotic (black or blue) [S14].
- Parameters: sequence, x_0 = 0.5, warm-up iterations (e.g. 100 to 600), N (e.g. 1000 or more), clamp on λ.
- Default view: a, b in [2, 4]; "Zircon Zity" is sequence BBBBBBAAAAAA on a in [2.5, 3.4], b in [3.4, 4.0] [S14].
- Tell: smooth folded "swallow" shapes on a two-tone field. Not complex-plane.

### Buddhabrot, Anti-Buddhabrot, Nebulabrot
- Buddhabrot: sample random c; for orbits that escape, add every visited z to a density histogram [S15]. Melinda Green 1993 [S16].
- Anti-Buddhabrot: same, but plot the orbits that do not escape (the interior) [S15].
- Nebulabrot: three passes with different max_iter (e.g. 5000/500/50) mapped to R/G/B [S15].
- Cost: needs many samples (10^8 or more for a clean HD image) and is noisy. Importance sampling with Metropolis-Hastings (Alexander Boswell) cuts zoomed-render cost sharply [S17]. Rendering is a scatter, which fits atomics on GPU or histogram adds in NumPy.
- Default view: c sampled in [-2, 2]^2. Plot with the real axis vertical so the "Buddha" sits upright [S15].
- Tell: glowing, ghostly density cloud with no hard edges, seated-figure silhouette.

## Colouring methods

### Smooth (continuous) iteration count
- mu = n + 1 - log(log|z_n|)/log d. Use a large R; some write it as n - log2(log2|z|) + const [S4][S5].
- Cost: one log-log per escaped pixel.
- Artefacts: banding returns if R is small. Wrong for non-polynomial maps and for Newton, where the convergence version uses log of the distance to the root [S4][S12].

### Histogram colouring
- Build a histogram of n over the escaped pixels, take the CDF, colour = palette(CDF(n)) [S3].
- Cost: two passes plus a global reduction; awkward in a single-pass shader.
- Artefacts: frame-to-frame flicker in zoom videos, because the distribution shifts. It can be combined with smooth mu by interpolating the CDF [S3].

### Orbit traps
- Track min over n of distance(z_n, trap), where the trap is a point, line, cross or circle. Colour from that minimum (and optionally from the index where it occurred) [S18][S19].
- Cost: one distance per iteration.
- Artefacts: discontinuities where the minimising index jumps. Aliasing on thin traps needs supersampling [S18].

### Distance estimate (exterior)
- Iterate dz ← 2·z·dz + 1 (dz_0 = 0) alongside z. d = |z|·log|z| / |dz| (some sources halve this, giving 0.5·|z|·log|z|/|dz|) [S20][S21].
- Use it to shade the boundary at a fixed pixel width (thin filaments stay visible) or as a soft edge [S20].
- Cost: one extra complex multiply-add per iteration.
- Artefacts: dz overflows in float32 for deep or long orbits; normalise or use log space [S20].

### Distance estimate (interior)
- Needs the attracting cycle's period p and the cycle point z0; uses the derivatives d/dz and d/dc of the p-fold map [S21].
- Cost: high (needs period detection and Newton's method for z0). Most renderers skip it.

### Stripe average colouring
- Average of 0.5·sin(s·arg z_n) + 0.5 over the orbit, linearly interpolated with the smooth fractional part so that it varies continuously [S22] (Härkönen 2007 thesis [S22]; summary in [S23]).
- Parameter: stripe density s (e.g. 5 to 10). Skip the first few iterates.
- Artefacts: very large R is needed to avoid seams (≥ 1e3, ideally ≫).

### Triangle inequality average (TIA)
- t_n = (|z_n| - | |z_{n-1}|^2 - |c| |) / ( |z_{n-1}^2| + |c| - | |z_{n-1}|^2 - |c| | ), averaged and interpolated with the smooth fractional part [S23][S24]. Due to Kerry Mitchell, popularised through UltraFractal [S24].
- Artefacts: NaN when the denominator is zero (at c = 0); the first iterate must be skipped.

### Palettes and gradient design
- Cyclic palettes: colour = palette(fract(mu·density + offset)) so zooms keep their colour variety. IQ's cosine palette, a + b·cos(2π(c·t + d)), gives cyclic gradients from 12 numbers [S25].
- Perceptual uniformity: use perceptual colormaps (viridis and its kin, designed in CAM02-UCS) for "measured" output; colorcet provides cyclic perceptually uniform maps (e.g. CET-C*) [S26][S27]. Interpolating in OKLab avoids muddy midpoints [S28].
- Hue wheels: an RGB/HSB hue wheel puts cyan opposite red, not green as on the painter's RYB wheel, so complementary pairs picked by hue + 0.5 look wrong to painters; reshape hue first if a painter's palette is wanted. Ease palette parameters through a shaping function (smoothstep, pow) rather than a linear mix for softer bands [S29].
- Log scaling of mu (log(mu + 1)) helps deep zooms where n is large.

## Implications for fractalwright

Recipe JSON fields needed:
- `family`: mandelbrot | julia | multibrot | burning_ship | tricorn | newton | nova | lyapunov | buddhabrot
- `params`: `c` (julia/nova-julia), `power` d, `polynomial` roots, `relaxation` a, `sequence` (lyapunov), `flip_y` (burning ship), `samples`, `channels` [{max_iter, colour}] for nebulabrot, `anti` bool
- `view`: `center` [x, y] as decimal **strings** (deep zooms outrun JSON doubles), `scale` (width in plane units), `rotation`, `aspect`
- `iter`: `max_iter`, `bailout`, `eps` (Newton), `warmup` (Lyapunov)
- `colour`: `method` (smooth | histogram | trap | de | stripe | tia | basin | lyapunov), method params (`trap` shape and position, `stripe_density`, `de_width_px`), `palette` (named, cosine coefficients, or stops plus `space`: oklab|srgb), `cyclic`, `density`, `offset`, `interior_colour`
- `precision`: f32 | f64 | perturbation; `supersample`
- `seed` for Buddhabrot and other stochastic methods

Presets to ship: mandelbrot-full, seahorse-valley, julia-rabbit, julia-dendrite, julia-0.285, julia-classic (-0.8+0.156i), multibrot-3, burning-ship-hull, tricorn-full, newton-z3, nova-mandel, lyapunov-zircon-zity, buddhabrot-classic, nebulabrot.

Numeric tests:
- Mandelbrot area by pixel count at modest resolution should land near 1.50659 (reference 1.5065918849 ± 2.8e-9) [S1][S2]. Test with a tolerance, e.g. ±0.005 at 2048² and max_iter 10k, since convergence in resolution and iteration count is slow.
- Points: c = 0, -1, -2, 0.25 are in M; c = 0.26, 1, -2.01 are not [S3].
- Julia with c = 0: the unit disc, area π [S8].
- Newton z^3-1: z_0 = 2 converges to the root 1 [S12].
- Lyapunov at a = b = 3.2 (period-2 regime) gives λ < 0; a = b = 4 gives λ = ln 2 ≈ 0.693 nats = exactly 1 bit per iteration [S14]; `fw.py` logistic r = 4 measures 0.99999 bits.
- Smooth mu continuity: for adjacent pixels across an iteration-band boundary, |Δmu| stays small.

Design consequences:
- Histogram colouring and Buddhabrot both need global reductions or scatters. The "single fragment shader" route alone is not enough; a WebGPU compute or NumPy path is needed for them.
- f32 GLSL caps zoom near 1e-5. Deep zoom videos force either f64 (NumPy/CPU) or perturbation.
- `identify` can use the tells above plus cheap measures (symmetry axes, the colour count in basins, density-cloud vs hard-edge).

## Open questions
- Render core choice decides which colouring methods can run in the browser explorer (histogram, Buddhabrot) — owner call.
- Should presets pin reference images (golden-image tests) or only numeric tests? Golden images are fragile across GPUs.
- Burning Ship and Tricorn view coordinates were taken from secondary pages and memory; confirm them by rendering before shipping.
- The constant factor in the exterior DE (1 vs 0.5) varies by source; pick one and document it.
- Licence of borrowed palettes (colorcet is CC-BY; matplotlib maps are CC0) — record in credits.

## Sources (accessed 2026-11-14)
- [S1] Munafo, Pixel Counting: https://mrob.com/pub/muency/pixelcounting.html
- [S2] Munafo, Förstemann entry: https://www.mrob.com/pub/muency/forstemannthorsten.html (also Area History: https://mrob.com/pub/muency/areahistory.html)
- [S3] Wikipedia, Plotting algorithms for the Mandelbrot set: https://en.wikipedia.org/wiki/Plotting_algorithms_for_the_Mandelbrot_set ; Mandelbrot set: https://en.wikipedia.org/wiki/Mandelbrot_set
- [S4] Inigo Quilez, Smooth iteration count: https://iquilezles.org/articles/msetsmooth/
- [S5] Linas Vepstas, Renormalizing the Mandelbrot escape: https://linas.org/art-gallery/escape/escape.html
- [S6] Wikipedia, Plotting algorithms: Perturbation theory section (same URL as S3)
- [S7] Kalles Fraktaler 2+: https://mathr.co.uk/kf/kf.html
- [S8] Wikipedia, Julia set: https://en.wikipedia.org/wiki/Julia_set
- [S9] Wikipedia, Multibrot set: https://en.wikipedia.org/wiki/Multibrot_set
- [S10] Wikipedia, Burning Ship fractal: https://en.wikipedia.org/wiki/Burning_Ship_fractal
- [S11] Wikipedia, Tricorn: https://en.wikipedia.org/wiki/Tricorn_(mathematics)
- [S12] Wikipedia, Newton fractal: https://en.wikipedia.org/wiki/Newton_fractal
- [S13] Paul Derbyshire / Fractint docs on Nova; overview at https://en.wikipedia.org/wiki/Newton_fractal#Nova_fractal
- [S14] Wikipedia, Lyapunov fractal: https://en.wikipedia.org/wiki/Lyapunov_fractal
- [S15] Wikipedia, Buddhabrot: https://en.wikipedia.org/wiki/Buddhabrot
- [S16] Melinda Green, The Buddhabrot technique: https://superliminal.com/fractals/bbrot/
- [S17] Alexander Boswell, Metropolis-Hastings Buddhabrot: https://web.archive.org/web/2016*/http://www.steckles.com/buddha/
- [S18] Wikipedia, Orbit trap: https://en.wikipedia.org/wiki/Orbit_trap
- [S19] Inigo Quilez, Orbit traps: https://iquilezles.org/articles/ftrapsgeometric/
- [S20] Inigo Quilez, Distance to fractals: https://iquilezles.org/articles/distancefractals/
- [S21] Wikipedia, Plotting algorithms, Distance estimates section (same URL as S3)
- [S22] Jussi Härkönen, On smooth fractal coloring techniques (MSc thesis, Åbo Akademi, 2007): https://jussiharkonen.com/files/on_fractal_coloring_techniques%28lo-res%29.pdf
- [S23] Wikibooks, Fractals/Iterations in the complex plane/stripeAC and TIA: https://en.wikibooks.org/wiki/Fractals/Iterations_in_the_complex_plane/triangle_ineq
- [S24] Ultra Fractal docs, Triangle Inequality Average: https://www.ultrafractal.com/help/index.html?/help/coloring/standard/triangleinequalityaverage.html
- [S25] Inigo Quilez, Palettes: https://iquilezles.org/articles/palettes/
- [S26] matplotlib, Choosing colormaps: https://matplotlib.org/stable/users/explain/colors/colormaps.html
- [S27] Peter Kovesi, colorcet / Good Colour Maps: https://colorcet.com/
- [S28] Björn Ottosson, OKLab: https://bottosson.github.io/posts/oklab/
- [S29] Gonzalez Vivo and Lowe, The Book of Shaders, ch. 6 Colors (accessed 2026-11-19): https://thebookofshaders.com/06/
